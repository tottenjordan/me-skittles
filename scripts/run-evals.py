# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Measure whether a skill fires when it should, and stays quiet when it should not.

    uv run scripts/run-evals.py claude/git-worktrees
    uv run scripts/run-evals.py claude/git-worktrees --json results.json
    uv run scripts/run-evals.py claude/git-worktrees --case 3 --keep

Reads `<skill>/evals/evals.json` and runs every query through a real headless
Claude Code session, then reports a confusion matrix.

What this measures, and what it does not
----------------------------------------
Trigger accuracy only. Whether the skill *fires* is a different question from
whether its instructions are any good, they fail for different reasons, and
averaging them hides both. Output quality needs a with/without baseline and a
grader; that is deliberately not in this script.

How a run is isolated
---------------------
Each case gets a throwaway CLAUDE_CONFIG_DIR containing exactly one skill, so
the listing the model sees is reproducible. Without that, whatever happens to be
in ~/.claude/skills joins the listing and the result depends on the machine --
this repo's own author has eleven personal skills installed, several of which
overlap the trees under test.

Each case also gets a throwaway git repo as its working directory, because a
query like "set up a worktree" reads differently outside one.

`--permission-mode plan` keeps a run from touching anything real.

Why it stops at the first tool call
-----------------------------------
Cost. Left alone, a triggered run keeps going and does the work: measured at
about $0.51 and 90 seconds for a single case, which makes a corpus unaffordable
and buys nothing, since the decision being measured has already happened.

So the stream is read until the model's first tool call and the process is then
killed. If that call is Skill with the expected name, the skill fired. Anything
else means the model chose to act without it.

The honest limit: this rules out a skill invoked *late*, after some other tool.
That is a real gap, and it is accepted deliberately -- a skill that matches a
request matches it at the point of reading, and treating a fifth-turn invocation
as a trigger success would flatter the description. If a case looks wrong, rerun
it with `--case N --keep` and read the transcript.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS_FILE = "evals/evals.json"

# Long enough for a first tool call on a slow model, short enough that a hung run
# does not stall a corpus. Reaching it is reported as a timeout, never as a miss:
# "no answer" and "the wrong answer" are different results.
CASE_TIMEOUT_S = 240


@dataclass
class Case:
    query: str
    should_trigger: bool
    fired: str | None = None  # skill name actually invoked, if any
    first_tool: str | None = None
    error: str | None = None

    @property
    def correct(self) -> bool:
        return self.error is None and (self.fired is not None) == self.should_trigger


@dataclass
class Corpus:
    skill: str
    tree: str
    cases: list[Case] = field(default_factory=list)


def load(skill_path: Path) -> Corpus:
    data = json.loads((skill_path / EVALS_FILE).read_text(encoding="utf-8"))
    corpus = Corpus(skill=data["skill"], tree=data["tree"])
    for query in data.get("should_trigger", []):
        corpus.cases.append(Case(query=query, should_trigger=True))
    for query in data.get("should_not_trigger", []):
        corpus.cases.append(Case(query=query, should_trigger=False))
    return corpus


def sandbox(skill_src: Path, skill_name: str) -> tuple[Path, Path]:
    """A config dir holding only this skill, and a git repo to run in."""
    config = Path(tempfile.mkdtemp(prefix="evalcfg-"))
    (config / "skills").mkdir()
    (config / "skills" / skill_name).symlink_to(skill_src)

    workdir = Path(tempfile.mkdtemp(prefix="evalwork-"))
    (workdir / "README.md").write_text("# scratch repo\n")
    for args in (
        ["init", "-q"],
        ["config", "user.email", "eval@example.invalid"],
        ["config", "user.name", "eval"],
        ["add", "-A"],
        ["commit", "-qm", "init"],
    ):
        subprocess.run(["git", *args], cwd=workdir, check=True, capture_output=True)
    return config, workdir


def first_tool_call(config: Path, workdir: Path, query: str) -> tuple[str | None, dict | None]:
    """Run one query; return the first tool name and its input, killing the run there."""
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(config)}
    proc = subprocess.Popen(
        [
            "claude",
            "-p",
            query,
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "plan",
        ],
        cwd=workdir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            for chunk in (event.get("message") or {}).get("content") or []:
                if isinstance(chunk, dict) and chunk.get("type") == "tool_use":
                    return chunk.get("name"), chunk.get("input") or {}
            # A final result with no tool call at all is a legitimate outcome:
            # the model answered in prose without reaching for anything.
            if event.get("type") == "result":
                return None, None
    finally:
        proc.kill()
        proc.wait(timeout=10)
    return None, None


def run_case(case: Case, skill_src: Path, skill_name: str, keep: bool) -> None:
    config, workdir = sandbox(skill_src, skill_name)
    try:
        name, payload = first_tool_call(config, workdir, case.query)
        case.first_tool = name
        if name == "Skill":
            invoked = (payload or {}).get("skill") or (payload or {}).get("name")
            case.fired = invoked
    except subprocess.TimeoutExpired:
        case.error = f"timed out after {CASE_TIMEOUT_S}s"
    except (OSError, subprocess.SubprocessError) as exc:
        case.error = str(exc)
    finally:
        if keep:
            print(f"      kept: config={config} workdir={workdir}")
        else:
            shutil.rmtree(config, ignore_errors=True)
            shutil.rmtree(workdir, ignore_errors=True)


def report(corpus: Corpus) -> int:
    want = [c for c in corpus.cases if c.should_trigger]
    avoid = [c for c in corpus.cases if not c.should_trigger]
    hits = [c for c in want if c.fired == corpus.skill]
    misses = [c for c in want if c.fired != corpus.skill]
    false_fires = [c for c in avoid if c.fired is not None]
    quiet = [c for c in avoid if c.fired is None]

    print(f"\n  {corpus.tree}/{corpus.skill}")
    print(f"  {'-' * 62}")
    print(f"  should trigger : {len(hits)}/{len(want)} fired")
    print(f"  should not     : {len(quiet)}/{len(avoid)} stayed quiet")

    for label, group in (("MISSED", misses), ("FALSE FIRE", false_fires)):
        for case in group:
            detail = case.error or f"first tool: {case.first_tool or 'none'}"
            if case.fired:
                detail = f"fired {case.fired}"
            print(f"    {label:<11} {case.query[:60]!r}  ({detail})")

    errored = [c for c in corpus.cases if c.error]
    if errored:
        print(f"  {len(errored)} case(s) errored and are not counted as either")

    # Precision matters more than recall here. A skill that misses a query costs
    # the user one prompt; a skill that fires on the wrong query costs everyone
    # who did not want it, on every session, and is far harder to notice.
    return 1 if false_fires or misses else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("skill", help="path to the skill, e.g. claude/git-worktrees")
    parser.add_argument("--json", type=Path, help="write full results here")
    parser.add_argument("--case", type=int, help="run only this case index (0-based)")
    parser.add_argument("--keep", action="store_true", help="keep sandboxes for inspection")
    args = parser.parse_args()

    skill_path = (REPO / args.skill).resolve()
    if not (skill_path / EVALS_FILE).is_file():
        print(f"No {EVALS_FILE} under {args.skill}", file=sys.stderr)
        return 2
    if not shutil.which("claude"):
        print("claude CLI not on PATH; this harness runs real sessions", file=sys.stderr)
        return 2

    corpus = load(skill_path)
    selected = corpus.cases if args.case is None else [corpus.cases[args.case]]
    for index, case in enumerate(selected):
        arrow = "should fire" if case.should_trigger else "should not"
        print(f"  [{index + 1}/{len(selected)}] {arrow}: {case.query[:58]}")
        run_case(case, skill_path, corpus.skill, args.keep)
        got = case.fired or case.first_tool or "no tool"
        print(f"      -> {got}{'  OK' if case.correct else '  <-- unexpected'}")

    code = report(corpus if args.case is None else Corpus(corpus.skill, corpus.tree, selected))
    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "skill": corpus.skill,
                    "tree": corpus.tree,
                    "cases": [
                        {
                            "query": c.query,
                            "should_trigger": c.should_trigger,
                            "fired": c.fired,
                            "first_tool": c.first_tool,
                            "error": c.error,
                            "correct": c.correct,
                        }
                        for c in selected
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"  wrote {args.json}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
