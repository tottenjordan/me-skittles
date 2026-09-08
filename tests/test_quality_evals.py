"""Tests for the output-quality harness.

Nothing here starts a real session. The reader and the grader are the parts
that can be quietly wrong -- a reader that loses the output, or a grader that
answers yes to everything, both produce a tie that reads like a finding.
"""

from __future__ import annotations

import json
import os

import pytest
from conftest import _load


@pytest.fixture(scope="session")
def quality():
    return _load("run_quality_evals", "run-quality-evals.py")


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    """Stub `claude` on PATH replaying a canned transcript ending in a result."""

    def install(result_text="output", cost=0.5, turns=3, is_error=False):
        events = [
            {"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}},
            {
                "type": "result",
                "subtype": "error" if is_error else "success",
                "result": result_text,
                "total_cost_usd": cost,
                "num_turns": turns,
                "duration_ms": 1234,
                "is_error": is_error,
            },
        ]
        script = tmp_path / "claude"
        script.write_text(
            "#!/bin/sh\ncat <<'EOF'\n" + "\n".join(json.dumps(e) for e in events) + "\nEOF\n"
        )
        script.chmod(0o755)
        monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")

    return install


def test_captures_final_text_and_cost(quality, fake_claude, tmp_path):
    fake_claude(result_text="the plan", cost=0.42, turns=7)
    out = quality.run_once(tmp_path, tmp_path, "task")
    assert out.text == "the plan"
    assert out.cost_usd == 0.42
    assert out.turns == 7


def test_a_failed_run_is_recorded_not_scored(quality, fake_claude, tmp_path):
    """An errored run must not be graded; a missing answer is not a low score."""
    fake_claude(result_text="", cost=0.1, is_error=True)
    out = quality.run_once(tmp_path, tmp_path, "task")
    assert out.error is not None
