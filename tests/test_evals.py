"""Pure-logic tests for the eval harness.

Nothing here starts a `claude` session. Scoring is the part that can be wrong
quietly -- a harness that counts a miss as a pass reports a number that reads
like evidence and is not -- so the arithmetic is tested and the subprocess is
left to the smoke run in CI-free manual use.
"""

from __future__ import annotations

import json
import os

import pytest
from conftest import _load


@pytest.fixture(scope="session")
def evals():
    return _load("run_evals", "run-evals.py")


def make(
    evals, query="q", should_trigger=True, fires=None, first_tool=None, error=None, skill="demo"
):
    """`fires` is one entry per run; a bare string is shorthand for a single run."""
    if isinstance(fires, str) or fires is None:
        fires = [fires]
    return evals.Case(
        query=query,
        should_trigger=should_trigger,
        skill=skill,
        fires=list(fires),
        first_tools=[first_tool] * len(fires),
        error=error,
    )


@pytest.mark.parametrize(
    "should_trigger, fires, expected",
    [
        (True, "demo", True),  # wanted it, got it
        (True, None, False),  # wanted it, silent -> miss
        (False, None, True),  # did not want it, silent
        (False, "demo", False),  # did not want it, fired -> false positive
    ],
)
def test_correctness_of_a_single_case(evals, should_trigger, fires, expected):
    assert make(evals, should_trigger=should_trigger, fires=fires).correct is expected


def test_an_errored_case_is_never_correct(evals):
    """A crashed run must not be scored as a pass. Absence of a trigger and
    failure to ask are different things, and only one is a result."""
    case = make(evals, should_trigger=False, fires=None, error="timed out")
    assert case.correct is False


def test_load_reads_both_arms(evals, tmp_path):
    skill = tmp_path / "demo"
    (skill / "evals").mkdir(parents=True)
    (skill / "evals" / "evals.json").write_text(
        json.dumps(
            {
                "skill": "demo",
                "tree": "claude",
                "should_trigger": ["a", "b"],
                "should_not_trigger": ["c"],
            }
        )
    )
    corpus = evals.load(skill)
    assert corpus.skill == "demo"
    assert [c.should_trigger for c in corpus.cases] == [True, True, False]


def test_report_passes_only_on_a_clean_sweep(evals, capsys):
    corpus = evals.Corpus(
        skill="demo",
        tree="claude",
        cases=[
            make(evals, should_trigger=True, fires="demo"),
            make(evals, should_trigger=False, fires=None),
        ],
    )
    assert evals.report(corpus) == 0
    assert "1/1 fired" in capsys.readouterr().out


def test_report_fails_on_a_false_fire(evals, capsys):
    """Precision failures must be loud: a skill firing on the wrong query costs
    every session, not just the one that asked."""
    corpus = evals.Corpus(
        skill="demo",
        tree="claude",
        cases=[make(evals, query="unrelated", should_trigger=False, fires="demo")],
    )
    assert evals.report(corpus) == 1
    assert "FALSE FIRE" in capsys.readouterr().out


def test_report_fails_on_a_miss(evals, capsys):
    corpus = evals.Corpus(
        skill="demo",
        tree="claude",
        cases=[make(evals, should_trigger=True, fires=None, first_tool="Bash")],
    )
    assert evals.report(corpus) == 1
    out = capsys.readouterr().out
    assert "MISSED" in out
    assert "Bash" in out  # what it reached for instead is the useful part


def test_a_different_skill_firing_counts_as_a_miss(evals):
    """Firing *something* is not firing the right thing."""
    case = make(evals, should_trigger=True, fires="some-other-skill")
    corpus = evals.Corpus(skill="demo", tree="claude", cases=[case])
    assert evals.report(corpus) == 1


def test_the_shipped_corpus_parses_and_is_balanced(evals):
    """The pilot corpus is real input to this harness; keep it loadable.

    Also asserts the near-miss arm exists. A corpus with no should_not_trigger
    cases can only ever report perfect precision, which is worse than no number.
    """
    from conftest import REPO

    corpus = evals.load(REPO / "claude/git-worktrees")
    assert corpus.skill == "git-worktrees"
    assert sum(1 for c in corpus.cases if not c.should_trigger) >= 5


# --------------------------------------------------------------------------
# Repeated runs. Added after two identical-config runs disagreed on 3 of 19
# cases, which made every single-run number in the pilot a sample rather than
# a result.
# --------------------------------------------------------------------------


def test_majority_decides_the_outcome(evals):
    assert make(evals, fires=["demo", "demo", None]).fired == "demo"
    assert make(evals, fires=["demo", None, None]).fired is None


def test_no_majority_means_no_result(evals):
    """Two different skills once each is not a win for either."""
    assert make(evals, fires=["a", "b"]).fired is None


def test_unstable_is_neither_pass_nor_fail(evals):
    assert make(evals, fires=["demo", None, "demo"]).unstable is True
    assert make(evals, fires=["demo", "demo", "demo"]).unstable is False
    assert make(evals, fires=[None, None, None]).unstable is False


def test_fire_rate_reports_the_raw_counts(evals):
    assert make(evals, fires=["demo", None, "demo"]).fire_rate == "2/3"


def test_report_surfaces_unstable_cases_separately(evals, capsys):
    """An unstable case must be visible, not averaged into a score."""
    corpus = evals.Corpus(
        skill="demo",
        tree="claude",
        cases=[make(evals, should_trigger=True, fires=["demo", None, "demo"])],
    )
    evals.report(corpus)
    out = capsys.readouterr().out
    assert "unstable" in out.lower()
    assert "2/3" in out


def test_single_run_is_flagged_as_a_sample(evals, capsys):
    corpus = evals.Corpus(
        skill="demo",
        tree="claude",
        cases=[
            make(evals, should_trigger=True, fires="demo"),
            make(evals, should_trigger=False, fires=None),
        ],
    )
    evals.report(corpus)
    assert "--repeat 3" in capsys.readouterr().out


def test_group_siblings_returns_the_whole_workflow_group(evals):
    """The realistic listing, not the flattering one."""
    siblings = evals.group_siblings("claude", "git-worktrees")
    assert "git-worktrees" in siblings
    assert "writing-plans" in siblings  # an adjacent skill that can steal the trigger
    assert len(siblings) > 1


def test_group_siblings_falls_back_to_the_skill_alone(evals):
    assert evals.group_siblings("claude", "not-a-real-skill") == ["not-a-real-skill"]


# --------------------------------------------------------------------------
# The scan window. These lock in the fix for the harness's worst defect: it
# used to stop at the model's first tool call, which scored a skill as a miss
# whenever the session explored the repo before invoking it -- which is what
# real sessions do.
# --------------------------------------------------------------------------


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    """Put a stub `claude` on PATH that replays a canned stream-json transcript."""

    def install(tool_names):
        events = []
        for name in tool_names:
            payload = {"skill": "demo"} if name == "Skill" else {"command": "ls"}
            events.append(
                {"message": {"content": [{"type": "tool_use", "name": name, "input": payload}]}}
            )
        events.append({"type": "result", "subtype": "success"})
        script = tmp_path / "claude"
        body = "\n".join(json.dumps(e) for e in events)
        script.write_text("#!/bin/sh\ncat <<'EOF'\n" + body + "\nEOF\n")
        script.chmod(0o755)
        monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
        return script

    return install


def test_skill_found_as_the_very_first_tool(evals, fake_claude, tmp_path):
    fake_claude(["Skill"])
    fired, tools = evals.find_skill_call(tmp_path, tmp_path, "q", 6)
    assert fired == "demo"
    assert tools == ["Skill"]


def test_skill_found_after_exploration(evals, fake_claude, tmp_path):
    """The regression. Under the old first-tool rule this scored as a miss."""
    fake_claude(["Bash", "Read", "Glob", "Skill"])
    fired, tools = evals.find_skill_call(tmp_path, tmp_path, "q", 6)
    assert fired == "demo"
    assert len(tools) == 4


def test_window_closes_before_a_late_skill_call(evals, fake_claude, tmp_path):
    """max_tools is a budget, and the report must not pretend otherwise."""
    fake_claude(["Bash"] * 6 + ["Skill"])
    fired, tools = evals.find_skill_call(tmp_path, tmp_path, "q", 6)
    assert fired is None
    assert len(tools) == 6


def test_a_run_with_no_tools_at_all_is_a_miss(evals, fake_claude, tmp_path):
    fake_claude([])
    fired, tools = evals.find_skill_call(tmp_path, tmp_path, "q", 6)
    assert fired is None
    assert tools == []


def test_widening_the_window_can_change_the_verdict(evals, fake_claude, tmp_path):
    """The property that made the old rule wrong, stated as a test."""
    fake_claude(["Bash", "Bash", "Skill"])
    assert evals.find_skill_call(tmp_path, tmp_path, "q", 1)[0] is None
    assert evals.find_skill_call(tmp_path, tmp_path, "q", 6)[0] == "demo"


# --------------------------------------------------------------------------
# Sibling firing. Once the sandbox installs a whole group, "some skill fired"
# and "the skill under test fired" stop being the same question.
# --------------------------------------------------------------------------


def test_a_sibling_answering_a_near_miss_is_not_a_false_fire(evals, capsys):
    """The real case: executing-plans' near-miss arm contains a query that is
    finishing-a-development-branch's own trigger case. The sibling answering it
    is the group working, not a precision failure."""
    case = evals.Case(
        query="The feature is done and tests pass. Should I merge or open a PR?",
        should_trigger=False,
        skill="executing-plans",
        fires=["finishing-a-development-branch"],
        first_tools=["Skill"],
    )
    assert case.stolen_by == "finishing-a-development-branch"
    assert case.correct is True
    corpus = evals.Corpus(skill="executing-plans", tree="claude", cases=[case])
    assert evals.report(corpus) == 0
    assert "a sibling answered" in capsys.readouterr().out


def test_the_skill_itself_firing_on_a_near_miss_is_still_a_false_fire(evals):
    case = evals.Case(
        query="unrelated", should_trigger=False, skill="demo", fires=["demo"], first_tools=["Skill"]
    )
    assert case.stolen_by is None
    assert case.correct is False


def test_a_sibling_firing_on_a_should_trigger_case_is_still_a_miss(evals):
    """Recall is unforgiving in the other direction: the neighbour stealing a
    query this skill was supposed to win is exactly the failure worth catching."""
    case = evals.Case(
        query="q", should_trigger=True, skill="demo", fires=["other"], first_tools=["Skill"]
    )
    assert case.correct is False
    assert case.stolen_by == "other"
