# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""A scratch repository with the conditions a quality rubric needs to discriminate.

`sandbox()` in run-evals.py builds a repo holding a README and one commit. That is
enough to ask *does the skill fire*; it is useless for asking *did it follow the
procedure*. A rubric item like "verified the worktree directory is gitignored"
cannot discriminate in a repo with no .gitignore worth checking, and "establish a
clean baseline" cannot discriminate with no tests to run.

So the fixture is built to *fail* the rubric on its own. Every condition here
exists to give one rubric item something to catch:

  .gitignore covers build artefacts but NOT .worktrees/  -> "verify it is ignored"
  a test suite with one failing test                     -> "establish a baseline"
                                                            "do not proceed past red"
  no obvious worktree location                           -> "do not assume a location"

If a future fixture accidentally satisfies the rubric, both arms score full marks
and the experiment reports a tie that means nothing. Task 1's verification step
exists for exactly that reason.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Deliberately does not mention .worktrees or worktrees. That omission is the
# thing the first rubric item is looking for.
GITIGNORE = "__pycache__/\n*.pyc\n.venv/\ndist/\n"

PASSING = '''"""Cart totals."""


def subtotal(items):
    return sum(price * qty for price, qty in items)


def apply_discount(total, percent):
    return total * (1 - percent / 100)
'''

FAILING_TEST = '''from cart import apply_discount, subtotal


def test_subtotal_adds_line_items():
    assert subtotal([(10.0, 2), (5.0, 1)]) == 25.0


def test_discount_never_returns_negative():
    # Fails today: apply_discount does not clamp. Left broken on purpose -- the
    # baseline rubric items need a red suite to have anything to detect.
    assert apply_discount(10.0, 150) >= 0
'''

AUTH = '''"""Session handling, the module the eval tasks ask about."""


def issue_token(user_id):
    return f"tok-{user_id}"


def verify(token):
    return token.startswith("tok-")
'''


def build(root: Path) -> Path:
    """Create the fixture at `root` and commit it. Returns `root`."""
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / ".gitignore").write_text(GITIGNORE)
    (root / "cart.py").write_text(PASSING)
    (root / "auth.py").write_text(AUTH)
    (root / "tests" / "test_cart.py").write_text(FAILING_TEST)
    (root / "README.md").write_text(
        "# shop\n\nRun the tests with `python -m pytest tests/ -q` from the repo root.\n"
    )
    for args in (
        ["init", "-q"],
        ["config", "user.email", "eval@example.invalid"],
        ["config", "user.name", "eval"],
        ["config", "gc.auto", "0"],
        ["add", "-A"],
        ["commit", "-qm", "initial"],
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    return root
