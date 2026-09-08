# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
# pyyaml arrives via run-evals' import of repo_facts; see that script's header.
"""Measure whether a skill that fires actually improves the output.

    uv run scripts/run-quality-evals.py claude/git-worktrees
    uv run scripts/run-quality-evals.py claude/git-worktrees --repeat 2 --json out.json
    uv run scripts/run-quality-evals.py claude/git-worktrees --check-grader

A different question from scripts/run-evals.py, which asks only whether a skill
*loads*. A skill can fire reliably and contribute nothing.

The design
----------
Each task runs twice in fresh sessions: the skill's group installed, and the same
group minus the skill. `sandbox()` already takes an arbitrary skill list, so the
without arm is the group with one entry removed and needed no new code.

Each output is then graded **independently and unlabelled** against a checklist
drawn from the skill's own stated rules -- for git-worktrees, its Red flags
section supplies four binary behaviours directly. The grader sees one output at a
time and never learns which arm produced it, so it cannot reward the arm it
expects to be better.

A checklist rather than "which output is better": a preference judgement rewards
verbosity and yields no diagnosis, while per-item answers say *where* a skill
helps, which is what makes a null interpretable.

What it does not measure
------------------------
`--permission-mode plan` means runs state the procedure they would follow rather
than mutating the fixture. Safe and directly comparable, but it measures intent,
not executed work.

And the grader is a language model judging text. Treat its output as a regression
signal, not evidence -- which is why --check-grader exists and why its
self-consistency figure is reported next to every result.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
QUALITY_FILE = "evals/quality.json"

sys.path.insert(0, str(REPO / "scripts"))
from quality_fixtures import build as build_fixture


def _run_evals():
    """The trigger harness, loaded by path because its filename has a hyphen.

    Imported rather than copied: `sandbox()` and `group_siblings()` already do
    exactly what is needed here, and a second implementation of the sandbox is
    how two readers of one thing drift apart -- the lesson scripts/parse-groups.awk
    exists to encode.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_evals", REPO / "scripts" / "run-evals.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("run_evals", module)
    spec.loader.exec_module(module)
    return module


# Grading is a much easier task than the work being graded, so a cheaper model is
# defensible -- but only once --check-grader shows it is self-consistent and that
# it marks a planted negative false. Recorded in the results either way.
GRADER_MODEL = "claude-haiku-4-5-20251001"

GRADER_PROMPT = """You are grading one transcript against a checklist.

Answer each checklist item strictly about what the transcript SAYS OR DOES. Do not
reward intent, thoroughness, or length. If an item is not clearly evidenced, the
answer is false.

Return ONLY a JSON object of the form:
{{"items": [{{"n": 1, "met": true, "why": "one short sentence"}}, ...]}}

CHECKLIST:
{rubric}

TRANSCRIPT:
{output}
"""


@dataclass
class Output:
    text: str = ""
    cost_usd: float = 0.0
    turns: int = 0
    duration_ms: int = 0
    error: str | None = None


@dataclass
class TaskResult:
    task: str
    arm: str  # "with" or "without"
    output: Output
    grades: list[bool] = field(default_factory=list)


def run_once(config: Path, workdir: Path, task: str, timeout_s: int = 600) -> Output:
    """Run one task to completion and capture its final text and real cost."""
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(config)}
    try:
        proc = subprocess.run(
            [
                "claude",
                "-p",
                task,
                "--output-format",
                "stream-json",
                "--verbose",
                "--permission-mode",
                "plan",
            ],
            cwd=workdir,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return Output(error=f"timed out after {timeout_s}s")

    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "result":
            continue
        if event.get("is_error") or event.get("subtype") != "success":
            return Output(error=f"run failed: {event.get('subtype')}")
        return Output(
            text=str(event.get("result") or ""),
            cost_usd=float(event.get("total_cost_usd") or 0.0),
            turns=int(event.get("num_turns") or 0),
            duration_ms=int(event.get("duration_ms") or 0),
        )
    return Output(error="no result event")


def grade(output_text: str, rubric: list[str], model: str = GRADER_MODEL) -> list[bool] | None:
    """Grade one unlabelled output. Returns one bool per rubric item, or None."""
    numbered = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(rubric))
    prompt = GRADER_PROMPT.format(rubric=numbered, output=output_text)
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--model", model, "--output-format", "text"],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return None
    raw = proc.stdout.strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < 0:
        return None
    try:
        items = json.loads(raw[start : end + 1]).get("items") or []
    except json.JSONDecodeError:
        return None
    by_n = {int(i["n"]): bool(i["met"]) for i in items if "n" in i and "met" in i}
    if len(by_n) != len(rubric):
        return None
    return [by_n[n] for n in range(1, len(rubric) + 1)]


def load_quality(skill_path: Path) -> dict:
    return json.loads((skill_path / QUALITY_FILE).read_text(encoding="utf-8"))


def arms_for(tree: str, skill: str) -> dict[str, list[str]]:
    """The two installed sets. They differ by exactly one entry."""
    group = _run_evals().group_siblings(tree, skill)
    return {"with": group, "without": [s for s in group if s != skill]}


def make_sandbox(tree: str, skills: list[str]):
    """Reuse the trigger harness's config dir, but with the richer fixture."""
    import shutil
    import tempfile

    evals = _run_evals()
    config, throwaway = evals.sandbox(tree, skills)
    shutil.rmtree(throwaway, ignore_errors=True)  # its scratch repo is too bare
    workdir = Path(tempfile.mkdtemp(prefix="qualwork-"))
    build_fixture(workdir)
    return config, workdir


def check_grader(rubric: list[str], model: str) -> int:
    """Prove the grader is usable before believing anything it says.

    Two failure modes, both of which look exactly like a null result: a grader
    that disagrees with itself, and a grader that says yes to everything.
    """
    positive = (
        "I ran `git check-ignore .worktrees` and it was not ignored, so I added it to "
        ".gitignore and committed that first. I created the worktree at .worktrees/auth, "
        "then ran `python -m pytest tests/ -q` to get a baseline. One test fails "
        "(test_discount_never_returns_negative). I am stopping here to ask whether that "
        "failure is pre-existing before I touch anything. Where would you like the "
        "worktree to live -- .worktrees/ inside the repo, or a sibling directory?"
    )
    negative = "Sure. I ran `git worktree add ../auth -b auth`. Done, let me know what's next."

    print(f"  grader: {model}")
    first = grade(positive, rubric, model)
    second = grade(positive, rubric, model)
    planted = grade(negative, rubric, model)
    if first is None or second is None or planted is None:
        print("  FAIL: grader returned unparseable output")
        return 1

    flips = sum(1 for a, b in zip(first, second, strict=True) if a != b)
    rate = flips / len(rubric)
    print(
        f"  self-consistency: {len(rubric) - flips}/{len(rubric)} items agreed "
        f"across two gradings ({rate:.0%} flip rate)"
    )
    print(f"  planted positive: {sum(first)}/{len(rubric)} items met (expect most)")
    print(f"  planted negative: {sum(planted)}/{len(rubric)} items met (expect ~0)")

    ok = rate <= 0.10 and sum(first) >= len(rubric) - 1 and sum(planted) <= 1
    print("  grader is usable" if ok else "  FAIL: grader is not usable; do not run the pilot")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("skill", help="path to the skill, e.g. claude/git-worktrees")
    parser.add_argument("--repeat", type=int, default=2, help="runs per task per arm")
    parser.add_argument("--model", default=GRADER_MODEL, help="grading model")
    parser.add_argument("--json", type=Path, help="write full results, including raw outputs")
    parser.add_argument(
        "--check-grader",
        action="store_true",
        help="validate the grader and exit, without running any tasks",
    )
    args = parser.parse_args()

    skill_path = (REPO / args.skill).resolve()
    if not (skill_path / QUALITY_FILE).is_file():
        print(f"No {QUALITY_FILE} under {args.skill}", file=sys.stderr)
        return 2
    spec = load_quality(skill_path)
    rubric, tasks, skill, tree = spec["rubric"], spec["tasks"], spec["skill"], spec["tree"]

    # Always run first. A grader that flip-flops or says yes to everything
    # produces a tie, and a tie reads exactly like "the skill does not help".
    if check_grader(rubric, args.model) != 0:
        return 1
    if args.check_grader:
        return 0

    arms = arms_for(tree, skill)
    print(f"  with:    {len(arms['with'])} skills\n  without: {len(arms['without'])} skills")
    results: list[TaskResult] = []
    for task in tasks:
        for arm, install in arms.items():
            for _ in range(args.repeat):
                config, workdir = make_sandbox(tree, install)
                try:
                    out = run_once(config, workdir, task)
                finally:
                    import shutil

                    shutil.rmtree(config, ignore_errors=True)
                    shutil.rmtree(workdir, ignore_errors=True)
                r = TaskResult(task=task, arm=arm, output=out)
                if out.error is None:
                    r.grades = grade(out.text, rubric, args.model) or []
                results.append(r)
                mark = out.error or f"{sum(r.grades)}/{len(rubric)}"
                print(f"  [{arm:>7}] {mark}  {task[:52]}")
    return report(results, rubric, skill, args)


def report(results: list[TaskResult], rubric: list[str], skill: str, args) -> int:
    """Per rubric item, per arm. The total hides which item actually moved."""
    scored = [r for r in results if r.grades]
    cost = sum(r.output.cost_usd for r in results)
    print(f"\n  {skill}  ({len(scored)}/{len(results)} runs graded, ${cost:.2f} measured)")
    print("  " + "-" * 70)
    print(f"  {'rubric item':<52}{'with':>8}{'without':>10}")
    for i, item in enumerate(rubric):
        per = {arm: [r.grades[i] for r in scored if r.arm == arm] for arm in ("with", "without")}
        cells = {a: f"{sum(v)}/{len(v)}" if v else "-" for a, v in per.items()}
        print(f"  {item[:50]:<52}{cells['with']:>8}{cells['without']:>10}")

    tot = {
        arm: (
            sum(sum(r.grades) for r in scored if r.arm == arm),
            sum(len(r.grades) for r in scored if r.arm == arm),
        )
        for arm in ("with", "without")
    }
    w, wo = tot["with"], tot["without"]
    print("  " + "-" * 70)
    print(f"  {'TOTAL':<52}{f'{w[0]}/{w[1]}':>8}{f'{wo[0]}/{wo[1]}':>10}")

    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "skill": skill,
                    "grader": args.model,
                    "repeat": args.repeat,
                    "rubric": rubric,
                    "cost_usd": cost,
                    "results": [
                        {
                            "task": r.task,
                            "arm": r.arm,
                            "grades": r.grades,
                            "error": r.output.error,
                            "cost_usd": r.output.cost_usd,
                            "turns": r.output.turns,
                            # Raw text kept deliberately: a score nobody can audit is not evidence.
                            "output": r.output.text,
                        }
                        for r in results
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"  wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
