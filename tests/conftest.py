"""Fixtures for exercising the repo's validators against throwaway copies.

The pattern these tests follow: copy the repo, break one specific thing, assert
the matching check reports it, and assert it stays quiet when nothing is broken.
Both halves matter. A check that never fires and a check that always fires are
equally useless, and the failure this repo actually hit was the first kind --
decorating the README's headings with emoji would have silently unhooked
`check_readme_catalogue`, which fails *open*: no section found, nothing checked,
build green.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"

# Copying the working tree means uncommitted edits are covered too, but it also
# means dragging these along unless they are excluded. .git is the big one: 11 MB
# of history that every sandbox would otherwise duplicate.
IGNORE = shutil.ignore_patterns(
    ".git", "__pycache__", "*.pyc", ".venv", "node_modules", ".pytest_cache"
)


def _load(name: str, filename: str) -> ModuleType:
    """Import a script by path. `validate-skills.py` is not a legal module name."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader, f"cannot load {filename}"
    module = importlib.util.module_from_spec(spec)
    # Registered before exec so the module's own `from repo_facts import ...`
    # resolves against this same instance rather than importing a second copy.
    sys.modules[name] = module
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(SCRIPTS))
    return module


@pytest.fixture(scope="session")
def validator() -> ModuleType:
    return _load("validate_skills", "validate-skills.py")


@pytest.fixture(scope="session")
def repo_facts() -> ModuleType:
    return _load("repo_facts", "repo_facts.py")


@pytest.fixture(scope="session")
def _pristine(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One clean copy per session, used as the template for per-test sandboxes."""
    root = tmp_path_factory.mktemp("pristine") / "repo"
    shutil.copytree(REPO, root, ignore=IGNORE)
    _git_index(root)
    return root


def _git_index(root: Path) -> None:
    """Give the sandbox a git index, and nothing more than an index.

    `check_artifacts` decides whether a path is a committed build artifact by
    asking `git ls-files`. Without a repository that call fails and every
    `__pycache__` is reported as committed -- two spurious errors that look like
    a real regression and cost time twice before this fixture existed.

    `init` rather than `clone`: init captures the working tree as it is now,
    including uncommitted edits, where a clone would silently test HEAD. The
    copied .gitignore still applies, so ignored paths stay untracked exactly as
    they do in the real repo.

    `add -N` rather than `add`, and no commit at all. Both matter, and the second
    is why CI failed the first time this landed:

    - `-N` records paths without their content, which is all `ls-files` reads.
      A plain `add` writes a blob per file: thousands of loose objects for every
      test to copy.
    - Committing makes git run `gc --auto` in the background. That repacked the
      loose objects *while* the per-test copytree was walking .git, so the copy
      raced a moving object store and died with "No such file or directory" on
      paths that existed moments earlier. It passed locally and failed in CI,
      which is exactly how a race announces itself. No commit, no gc, no race.

    gc.auto=0 belts the braces: nothing here should trigger maintenance, but a
    sandbox that repacks itself mid-copy is a miserable thing to debug twice.
    """

    def run(*args: str) -> None:
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

    run("init", "-q")
    run("config", "gc.auto", "0")
    run("add", "-N", "-A")


@pytest.fixture
def sandbox(_pristine: Path, tmp_path: Path, validator: ModuleType) -> Path:
    """A fresh, writable copy of the repo for one test to mutate."""
    root = tmp_path / "repo"
    shutil.copytree(_pristine, root, symlinks=True)
    # repo_facts_for is @cache'd on the repo path. Paths differ per test so a
    # stale hit is unlikely, but a test that mutates then re-reads would get the
    # pre-mutation facts, and that failure would be baffling. Cheap to prevent.
    validator.repo_facts_for.cache_clear()
    return root


@pytest.fixture
def findings(validator: ModuleType):
    """Run one check against a sandbox and return its findings.

    Individual checks rather than the whole validator: a test that asserts on
    the full run passes for the wrong reason as soon as an unrelated check
    starts reporting.
    """

    def run(check_name: str, root: Path) -> list:
        report = validator.Report()
        getattr(validator, check_name)(root, report)
        return report.findings

    return run


def messages(found: list) -> str:
    """All findings as one searchable blob."""
    return "\n".join(f"{f.level} {f.path} {f.message}" for f in found)
