"""Pure-logic tests for the eval harness.

Nothing here starts a `claude` session. Scoring is the part that can be wrong
quietly -- a harness that counts a miss as a pass reports a number that reads
like evidence and is not -- so the arithmetic is tested and the subprocess is
left to the smoke run in CI-free manual use.
"""

from __future__ import annotations

import json

import pytest
from conftest import _load


@pytest.fixture(scope="session")
def evals():
    return _load("run_evals", "run-evals.py")


def make(evals, query="q", should_trigger=True, fired=None, first_tool=None, error=None):
    return evals.Case(
        query=query,
        should_trigger=should_trigger,
        fired=fired,
        first_tool=first_tool,
        error=error,
    )


@pytest.mark.parametrize(
    "should_trigger, fired, expected",
    [
        (True, "git-worktrees", True),  # wanted it, got it
        (True, None, False),  # wanted it, silent -> miss
        (False, None, True),  # did not want it, silent
        (False, "git-worktrees", False),  # did not want it, fired -> false positive
    ],
)
def test_correctness_of_a_single_case(evals, should_trigger, fired, expected):
    assert make(evals, should_trigger=should_trigger, fired=fired).correct is expected


def test_an_errored_case_is_never_correct(evals):
    """A crashed run must not be scored as a pass. Absence of a trigger and
    failure to ask are different things, and only one is a result."""
    case = make(evals, should_trigger=False, fired=None, error="timed out")
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
            make(evals, should_trigger=True, fired="demo"),
            make(evals, should_trigger=False, fired=None),
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
        cases=[make(evals, query="unrelated", should_trigger=False, fired="demo")],
    )
    assert evals.report(corpus) == 1
    assert "FALSE FIRE" in capsys.readouterr().out


def test_report_fails_on_a_miss(evals, capsys):
    corpus = evals.Corpus(
        skill="demo",
        tree="claude",
        cases=[make(evals, should_trigger=True, fired=None, first_tool="Bash")],
    )
    assert evals.report(corpus) == 1
    out = capsys.readouterr().out
    assert "MISSED" in out
    assert "Bash" in out  # what it reached for instead is the useful part


def test_a_different_skill_firing_counts_as_a_miss(evals):
    """Firing *something* is not firing the right thing."""
    case = make(evals, should_trigger=True, fired="some-other-skill")
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
