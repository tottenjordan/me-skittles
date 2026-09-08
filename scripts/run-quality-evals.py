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


def grade_once(output_text: str, rubric: list[str], model: str = GRADER_MODEL) -> list[bool] | None:
    """One grading pass. Returns one bool per rubric item, or None if unparseable."""
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


def grade(
    output_text: str, rubric: list[str], model: str = GRADER_MODEL, repeat: int = 3
) -> list[bool] | None:
    """Grade an output `repeat` times and take the majority answer per item.

    A single grading is a sample, not a verdict. Measured on this rubric, the
    grader agreed with itself on all four items across five passes -- and then, on
    a different pair of passes, flipped one. Rare, real, and indistinguishable
    from a genuine difference if it lands in only one arm.

    Majority vote over an odd number of passes makes an isolated flip harmless,
    at a cost that barely registers because grading runs on a small model.
    """
    passes = [g for g in (grade_once(output_text, rubric, model) for _ in range(repeat)) if g]
    if not passes:
        return None
    return [sum(p[i] for p in passes) * 2 > len(passes) for i in range(len(rubric))]


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


def check_grader(spec: dict, model: str, passes: int = 5) -> int:
    """Prove the grader is usable before believing anything it says.

    Two failure modes, both of which look exactly like a null result: a grader
    that disagrees with itself, and a grader that says yes to everything.

    The planted samples live in the skill's own quality.json, not here. They were
    hardcoded once, written for git-worktrees, and the first other skill to use
    this gate failed it -- the grader correctly scored a worktree transcript 0/5
    against a rubric about uv and ruff. The check was asking the wrong question,
    and only looked like a grader problem.

    Stability is measured over `passes` gradings, not two. With a four-item
    rubric, two passes can only report 0/25/50/75/100 percent, so a single flip
    reads as a 25% failure rate -- which is how this gate passed once and failed
    the next run on the same grader and the same output.
    """
    rubric = spec["rubric"]
    check = spec.get("grader_check") or {}
    positive, negative = check.get("positive"), check.get("negative")
    if not positive or not negative:
        print("  FAIL: quality.json needs grader_check.positive and .negative")
        print("  (a transcript that meets this rubric, and one that plainly does not)")
        return 1

    print(f"  grader: {model}, stability over {passes} passes")
    runs = [g for g in (grade_once(positive, rubric, model) for _ in range(passes)) if g]
    if len(runs) < passes:
        print(f"  FAIL: {passes - len(runs)} grading(s) returned unparseable output")
        return 1

    shaky = []
    for i in range(len(rubric)):
        vals = [r[i] for r in runs]
        agreement = max(vals.count(True), vals.count(False)) / len(vals)
        if agreement < 1.0:
            shaky.append((i + 1, agreement))
    print(f"  self-consistency: {len(rubric) - len(shaky)}/{len(rubric)} items unanimous")
    for n, a in shaky:
        print(f"    item {n} agreed only {a:.0%} of the time")

    pos = grade(positive, rubric, model)
    neg = grade(negative, rubric, model)
    if pos is None or neg is None:
        print("  FAIL: majority grading returned nothing")
        return 1
    print(f"  planted positive: {sum(pos)}/{len(rubric)} met (expect most)")
    print(f"  planted negative: {sum(neg)}/{len(rubric)} met (expect ~0)")

    # One shaky item is tolerable *because* results use a majority vote; more
    # than that means the rubric is ambiguous, not the grader.
    ok = len(shaky) <= 1 and sum(pos) >= len(rubric) - 1 and sum(neg) <= 1
    print("  grader is usable" if ok else "  FAIL: grader unusable; do not run the pilot")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("skill", help="path to the skill, e.g. claude/git-worktrees")
    parser.add_argument("--repeat", type=int, default=2, help="runs per task per arm")
    parser.add_argument("--model", default=GRADER_MODEL, help="grading model")
    parser.add_argument(
        "--grade-repeat", type=int, default=3, help="gradings per output, majority wins"
    )
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
    if check_grader(spec, args.model) != 0:
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
                    r.grades = grade(out.text, rubric, args.model, args.grade_repeat) or []
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
