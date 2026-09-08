# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
# pyyaml is not used here directly. Group membership comes from repo_facts'
# load_groups, and that module parses YAML frontmatter, so importing it pulls
# pyyaml in. Reading groups.toml with a second parser would avoid the dependency
# and reintroduce exactly the split that scripts/parse-groups.awk exists to
# prevent, so the dependency is the cheaper of the two.
"""Measure whether a skill fires when it should, and stays quiet when it should not.

    uv run scripts/run-evals.py claude/git-worktrees
    uv run scripts/run-evals.py claude/git-worktrees --repeat 5 --json results.json
    uv run scripts/run-evals.py claude/git-worktrees --case 3 --repeat 1 --keep
    uv run scripts/run-evals.py claude/git-worktrees --isolated   # no siblings

Reads `<skill>/evals/evals.json` and runs every query through a real headless
Claude Code session, then reports a confusion matrix.

What this measures, and what it does not
----------------------------------------
Trigger accuracy only. Whether the skill *fires* is a different question from
whether its instructions are any good, they fail for different reasons, and
averaging them hides both. Output quality needs a with/without baseline and a
grader; that is deliberately not in this script.

A single run is not a measurement
---------------------------------
Two runs of this harness against an identical configuration disagreed on 3 of 19
cases. Triggering is a model decision, so one run is a sample. `--repeat`
defaults to 3 and the report separates *unstable* cases -- fired sometimes, not
others -- from passes and failures, because folding them into a score turns "we
do not know" into a number.

Measured so far, the two arms are not equally noisy: the should-not-trigger arm
was stable across runs while every flip landed in should-trigger. Precision
appears to be the more trustworthy figure; treat recall as approximate.

How a run is isolated
---------------------
Each case gets a throwaway CLAUDE_CONFIG_DIR holding the skill's whole
`groups.toml` group, because a group is the unit people install and therefore
the listing that really occurs. `--isolated` installs the skill alone, which
measures a configuration nobody runs and reliably reports a higher trigger rate.

Isolation from the machine is the point: without CLAUDE_CONFIG_DIR, whatever is
in ~/.claude/skills joins the listing and the result depends on whose laptop ran
it -- this repo's author has eleven personal skills installed, several
overlapping the trees under test.

Each case also gets a throwaway git repo as its working directory, because a
query like "set up a worktree" reads differently outside one.

`--permission-mode plan` keeps a run from touching anything real.

Why it scans a window of tool calls
-----------------------------------
The first version stopped at the model's first tool call, on the reasoning that
a skill matching a request matches it at the point of reading. That was wrong,
and measurably so: real sessions explore the repo with Bash before deciding, and
a case scored 0/3 under that rule fired as soon as the window widened. The rule
was not a minor accepted limit, it was systematically undercounting recall.

So the stream is now read until a Skill call appears, or `--max-tools` calls have
gone by (default 6), or the run ends. Cost rose from about 5 seconds a case to
about 33; a full pass over this group at --repeat 3 is several hours, which is
why the default repeat is modest and why runs are a deliberate act rather than
part of CI.

Still not measured: a skill invoked after more than `--max-tools` calls. That
limit is now a budget decision rather than a claim about behaviour.

"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS_FILE = "evals/evals.json"
ARMS_FILE = "evals/arms.json"

# Long enough for a first tool call on a slow model, short enough that a hung run
# does not stall a corpus. Reaching it is reported as a timeout, never as a miss:
# "no answer" and "the wrong answer" are different results.
CASE_TIMEOUT_S = 240


@dataclass
class Case:
    """One query, run `--repeat` times because a single run is not a measurement.

    Two runs of this harness against an identical configuration disagreed on 3 of
    19 cases. Triggering is a model decision, not a deterministic function, so a
    one-shot result is a sample that reads like a fact -- the pilot's headline
    "6/8 recall" was exactly that mistake. Every case therefore records each
    outcome, and `fired` is the majority.
    """

    query: str
    should_trigger: bool
    skill: str = ""  # the skill under test; a sibling firing is a different result
    fires: list[str | None] = field(default_factory=list)
    first_tools: list[str | None] = field(default_factory=list)
    tool_paths: list[list[str]] = field(default_factory=list)
    error: str | None = None

    @property
    def fired(self) -> str | None:
        """The majority outcome, or None if no single skill won a majority."""
        if not self.fires:
            return None
        names = [f for f in self.fires if f]
        for name in set(names):
            if names.count(name) * 2 > len(self.fires):
                return name
        return None

    @property
    def first_tool(self) -> str | None:
        return self.first_tools[0] if self.first_tools else None

    @property
    def fire_rate(self) -> str:
        """How often it fired, e.g. "2/3" -- the honest form of the result."""
        return f"{sum(1 for f in self.fires if f)}/{len(self.fires)}"

    @property
    def unstable(self) -> bool:
        """Fired sometimes and not others. Neither a pass nor a fail: noise."""
        fired = sum(1 for f in self.fires if f)
        return 0 < fired < len(self.fires)

    @property
    def stolen_by(self) -> str | None:
        """A sibling fired instead of the skill under test.

        On a should_not_trigger case that is usually the *right* answer, not a
        failure: the corpus asks whether this skill stays quiet, and a neighbour
        correctly handling the query is the group working as intended. Scoring it
        as a false fire punished `executing-plans` for
        `finishing-a-development-branch` answering a question that is literally
        one of its own trigger cases.
        """
        return self.fired if self.fired and self.fired != self.skill else None

    @property
    def correct(self) -> bool:
        if self.error is not None:
            return False
        return (self.fired == self.skill) == self.should_trigger


@dataclass
class Corpus:
    skill: str
    tree: str
    cases: list[Case] = field(default_factory=list)


def load(skill_path: Path) -> Corpus:
    data = json.loads((skill_path / EVALS_FILE).read_text(encoding="utf-8"))
    corpus = Corpus(skill=data["skill"], tree=data["tree"])
    for query in data.get("should_trigger", []):
        corpus.cases.append(Case(query=query, should_trigger=True, skill=corpus.skill))
    for query in data.get("should_not_trigger", []):
        corpus.cases.append(Case(query=query, should_trigger=False, skill=corpus.skill))
    return corpus


def group_siblings(tree: str, skill_name: str) -> list[str]:
    """Every skill installed alongside this one by `install.sh --group`.

    A group is the unit people install, so it is the listing the model really
    sees. Installing the skill alone measures something nobody experiences, and
    it cannot express the failure that matters most in a group of adjacent
    skills: with one skill present, "nothing fired" and "the wrong sibling
    fired" are the same observation.
    """
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        from repo_facts import load_groups
    finally:
        sys.path.pop(0)
    for entry in load_groups(REPO):
        if entry.get("tree") == tree and skill_name in (entry.get("skills") or []):
            return [s for s in entry["skills"] if isinstance(s, str)]
    return [skill_name]


DESCRIPTION_LINE = re.compile(r"^description:.*?(?=^[A-Za-z_-]+:|^---)", re.MULTILINE | re.DOTALL)


def swap_description(text: str, description: str) -> str:
    """Replace a SKILL.md's frontmatter description, leaving the body byte-identical.

    Only the description moves. Swapping anything else would put two variables in
    an experiment designed to isolate one.
    """
    replacement = "description: " + json.dumps(description) + "\n"
    swapped, count = DESCRIPTION_LINE.subn(lambda _m: replacement, text, count=1)
    if count != 1:
        raise ValueError("no frontmatter description to replace")
    return swapped


def sandbox(
    tree: str,
    skill_names: list[str],
    arm: str | None = None,
    under_test: str | None = None,
) -> tuple[Path, Path]:
    """A config dir holding exactly these skills, and a git repo to run in.

    With `arm`, the skill under test is copied and given that description instead
    of its own; every sibling stays a symlink. The copy is what keeps the
    experiment honest -- editing the repo's SKILL.md would move the group's
    budget_tokens and the README figures derived from it, adding two variables to
    a test designed to isolate one.
    """
    config = Path(tempfile.mkdtemp(prefix="evalcfg-"))
    (config / "skills").mkdir()
    target = under_test or (skill_names[0] if skill_names else None)
    for name in skill_names:
        src = REPO / tree / name
        # Plugin bundles have no top-level SKILL.md and are installed through the
        # marketplace, so symlinking one adds nothing to the listing.
        if not (src / "SKILL.md").is_file():
            continue
        if arm is not None and name == target:
            dst = config / "skills" / name
            shutil.copytree(src, dst, symlinks=True)
            skill_md = dst / "SKILL.md"
            skill_md.write_text(
                swap_description(skill_md.read_text(encoding="utf-8"), arm), encoding="utf-8"
            )
        else:
            (config / "skills" / name).symlink_to(src)

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


def find_skill_call(
    config: Path, workdir: Path, query: str, max_tools: int
) -> tuple[str | None, list[str]]:
    """Run one query; return the skill invoked, if any, and the tools tried first.

    Stops as soon as a Skill call appears, or after `max_tools` tool calls, or at
    the end of the run -- whichever comes first.
    """
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
    tools: list[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            # `message` is not always an object -- some events carry it as a
            # plain string. Reaching .get() on one killed a 20-minute run after
            # 14 cases, and intermittently, because the shape depends on what
            # the session happens to emit.
            message = event.get("message")
            if not isinstance(message, dict):
                message = {}
            content = message.get("content")
            for chunk in content if isinstance(content, list) else []:
                if not (isinstance(chunk, dict) and chunk.get("type") == "tool_use"):
                    continue
                name = chunk.get("name")
                tools.append(name)
                if name == "Skill":
                    payload = chunk.get("input") or {}
                    return payload.get("skill") or payload.get("name"), tools
                if len(tools) >= max_tools:
                    return None, tools
            if event.get("type") == "result":
                return None, tools
    finally:
        proc.kill()
        proc.wait(timeout=10)
    return None, tools


def run_case(
    case: Case,
    tree: str,
    install: list[str],
    keep: bool,
    repeat: int,
    max_tools: int,
    arm: str | None = None,
    under_test: str | None = None,
) -> None:
    for _ in range(repeat):
        config, workdir = sandbox(tree, install, arm=arm, under_test=under_test)
        try:
            invoked, tools = find_skill_call(config, workdir, case.query, max_tools)
            case.first_tools.append(tools[0] if tools else None)
            case.tool_paths.append(tools)
            case.fires.append(invoked)
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
    false_fires = [c for c in avoid if c.fired == corpus.skill]
    quiet = [c for c in avoid if c.fired != corpus.skill]
    handled_by_sibling = [c for c in avoid if c.stolen_by]

    unstable = [c for c in corpus.cases if c.unstable]
    repeats = max((len(c.fires) for c in corpus.cases), default=0)

    print(f"\n  {corpus.tree}/{corpus.skill}")
    print(f"  {'-' * 62}")
    print(f"  should trigger : {len(hits)}/{len(want)} fired")
    print(f"  should not     : {len(quiet)}/{len(avoid)} stayed quiet")

    for label, group in (("MISSED", misses), ("FALSE FIRE", false_fires)):
        for case in group:
            detail = case.error or f"first tool: {case.first_tool or 'none'}"
            if case.fired:
                detail = f"fired {case.fired}"
            print(f"    {label:<11} {case.query[:60]!r}  ({detail}, {case.fire_rate})")

    # Reported separately from pass/fail, and never silently folded into either.
    # A case that fires on some runs and not others has not been measured yet,
    # and averaging it into a score turns "we do not know" into a number.
    if handled_by_sibling:
        print(f"\n  {len(handled_by_sibling)} near-miss(es) a sibling answered, which is correct:")
        for case in handled_by_sibling:
            print(f"    {case.stolen_by:<32} {case.query[:44]!r}")
    if unstable:
        print(f"\n  {len(unstable)} unstable case(s) -- fired on some runs, not others:")
        for case in unstable:
            print(f"    {case.fire_rate}  {case.query[:60]!r}")
    if repeats == 1 and len(corpus.cases) > 1:
        print("\n  Single run per case. Measured disagreement between identical runs is")
        print("  roughly 1 case in 6, so treat this as one sample: use --repeat 3.")

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
    parser.add_argument(
        "--repeat",
        type=int,
        default=3,
        help="runs per case; 1 is a sample, not a measurement (default: 3)",
    )
    parser.add_argument(
        "--arm",
        help=f"description variant from {ARMS_FILE} to use instead of the skill's own",
    )
    parser.add_argument(
        "--max-tools",
        type=int,
        default=6,
        help="tool calls to scan for a Skill call before giving up (default: 6)",
    )
    parser.add_argument(
        "--isolated",
        action="store_true",
        help="install only this skill instead of its whole group (hides sibling confusion)",
    )
    args = parser.parse_args()

    skill_path = (REPO / args.skill).resolve()
    if not (skill_path / EVALS_FILE).is_file():
        print(f"No {EVALS_FILE} under {args.skill}", file=sys.stderr)
        return 2
    if not shutil.which("claude"):
        print("claude CLI not on PATH; this harness runs real sessions", file=sys.stderr)
        return 2

    corpus = load(skill_path)
    install = [corpus.skill] if args.isolated else group_siblings(corpus.tree, corpus.skill)
    arm_text = None
    if args.arm:
        arms_path = skill_path / ARMS_FILE
        if not arms_path.is_file():
            print(f"No {ARMS_FILE} under {args.skill}", file=sys.stderr)
            return 2
        arms = json.loads(arms_path.read_text(encoding="utf-8")).get("arms", {})
        if args.arm not in arms:
            print(f"No arm {args.arm!r}; have {', '.join(sorted(arms))}", file=sys.stderr)
            return 2
        arm_text = arms[args.arm]
        # Printed with the result so a number is never separated from the
        # condition that produced it.
        print(f"  arm: {args.arm} ({len(arm_text)} chars)")
    print(f"  installed in each sandbox: {', '.join(install)}")
    selected = corpus.cases if args.case is None else [corpus.cases[args.case]]
    for index, case in enumerate(selected):
        arrow = "should fire" if case.should_trigger else "should not"
        print(f"  [{index + 1}/{len(selected)}] {arrow}: {case.query[:58]}")
        run_case(
            case,
            corpus.tree,
            install,
            args.keep,
            args.repeat,
            args.max_tools,
            arm=arm_text,
            under_test=corpus.skill,
        )
        got = case.fired or case.first_tool or "no tool"
        flag = "  OK" if case.correct else "  <-- unexpected"
        if case.unstable:
            flag = "  <-- UNSTABLE"
        print(f"      -> {got} ({case.fire_rate}){flag}")

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
                            "fires": c.fires,
                            "fire_rate": c.fire_rate,
                            "unstable": c.unstable,
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
