"""Each check fires on the defect it exists for, and stays silent otherwise.

Seeded from the sandbox assertions that were written ad hoc while adding these
checks and then thrown away. Persisting them is the point: the verification was
already being done, it just never survived the session that did it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import messages

# --------------------------------------------------------------------------
# Baseline. If these fail, every other assertion below is meaningless.
# --------------------------------------------------------------------------

ALL_CHECKS = [
    "check_symlinks",
    "check_artifacts",
    "check_plugin_manifests",
    "check_groups",
    "check_group_budgets",
    "check_cross_tree_parity",
    "check_readme_catalogue",
    "check_stated_counts",
    "check_script_dependencies",
    "check_deprecated_models",
    "check_gemini_purity",
]


@pytest.mark.parametrize("check", ALL_CHECKS)
def test_clean_repo_has_no_errors(check, sandbox, findings):
    """An unmodified repo produces no errors. Warnings are allowed."""
    errors = [f for f in findings(check, sandbox) if f.level == "error"]
    assert not errors, f"{check} errored on a clean tree:\n{messages(errors)}"


def test_artifacts_check_needs_git_not_just_files(sandbox, findings):
    """Regression guard for the fixture itself.

    check_artifacts shells out to `git ls-files`. A sandbox without a git index
    reports every ignored __pycache__ as a committed artifact. That misfire cost
    real time; this asserts the fixture keeps preventing it.
    """
    assert not [f for f in findings("check_artifacts", sandbox) if f.level == "error"]


# --------------------------------------------------------------------------
# Cross-tree parity
# --------------------------------------------------------------------------


def test_one_tree_edit_is_an_error(sandbox, findings):
    target = sandbox / "gemini/executing-plans/SKILL.md"
    target.write_text(target.read_text() + "\nDrifted.\n")
    out = messages(findings("check_cross_tree_parity", sandbox))
    assert "not a declared divergence" in out
    # Naming both paths matters: the reader has to know what to compare against.
    assert "claude/executing-plans/SKILL.md" in out


def test_declared_divergence_is_allowed(sandbox, findings, validator):
    """A path in the allowlist may differ."""
    target = sandbox / "gemini/executing-plans/SKILL.md"
    target.write_text(target.read_text() + "\nDrifted.\n")
    validator.CROSS_TREE_DIVERGENCE["executing-plans/SKILL.md"] = "test"
    try:
        out = messages(findings("check_cross_tree_parity", sandbox))
    finally:
        del validator.CROSS_TREE_DIVERGENCE["executing-plans/SKILL.md"]
    assert "not a declared divergence" not in out


def test_converged_entry_warns_as_stale(sandbox, findings):
    """An exemption must not outlive the difference that justified it."""
    src = sandbox / "claude/git-worktrees/SKILL.md"
    (sandbox / "gemini/git-worktrees/SKILL.md").write_bytes(src.read_bytes())
    assert "the two trees now agree" in messages(findings("check_cross_tree_parity", sandbox))


def test_allowlisted_path_that_does_not_exist_warns(sandbox, findings, validator):
    validator.CROSS_TREE_DIVERGENCE["no-such-skill/nope.md"] = "typo"
    try:
        out = messages(findings("check_cross_tree_parity", sandbox))
    finally:
        del validator.CROSS_TREE_DIVERGENCE["no-such-skill/nope.md"]
    assert "not a file shared by both trees" in out


def test_file_in_one_tree_only_is_not_drift(sandbox, findings):
    """Porting decisions are not drift; only files present in both are compared."""
    (sandbox / "claude/executing-plans/EXTRA.md").write_text("claude-only\n")
    out = messages(findings("check_cross_tree_parity", sandbox))
    assert "EXTRA.md" not in out


# --------------------------------------------------------------------------
# Per-group context budgets
# --------------------------------------------------------------------------


def _set_budget(root: Path, old: str, new: str) -> None:
    path = root / "groups.toml"
    text = path.read_text()
    assert old in text, f"{old!r} not in groups.toml"
    path.write_text(text.replace(old, new, 1))


@pytest.mark.parametrize(
    "replacement, expected",
    [
        ("budget_tokens = 3000", "over its declared"),
        ('budget_tokens = "lots"', "must be a positive integer"),
        ("budget_tokens = -5", "must be a positive integer"),
        ("budget_tokens = 99999", "constrains nothing"),
    ],
)
def test_group_budget_violations(sandbox, findings, replacement, expected):
    _set_budget(sandbox, "budget_tokens = 3400", replacement)
    assert expected in messages(findings("check_group_budgets", sandbox))


def test_headroom_within_slack_is_not_flagged(sandbox, findings):
    """Headroom is the point; only an unbindable budget warns."""
    _set_budget(sandbox, "budget_tokens = 3400", "budget_tokens = 4000")
    assert "constrains nothing" not in messages(findings("check_group_budgets", sandbox))


def test_missing_budget_key_is_an_error(sandbox, findings):
    _set_budget(sandbox, "budget_tokens = 3400\n", "")
    assert "missing required key `budget_tokens`" in messages(findings("check_groups", sandbox))


# --------------------------------------------------------------------------
# Frontmatter outside the Agent Skills spec
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key, expected",
    [
        ("when_to_use", "packaging and upload reject it"),
        ("tools", "`tools` is the"),
    ],
)
def test_non_spec_frontmatter_key_warns(sandbox, validator, key, expected):
    path = sandbox / "claude/writing-plans/SKILL.md"
    path.write_text(path.read_text().replace("\ndescription:", f"\n{key}: x\ndescription:", 1))
    report = validator.Report()
    validator.check_skill(path, sandbox, report)
    assert expected in messages(report.findings)


def test_repo_sets_no_non_spec_keys_today(sandbox, validator, repo_facts):
    """The rule is a warning because nothing violates it. If that changes, the
    severity question in docs/notes/multi-harness-skills.md is worth reopening."""
    offenders = [
        f
        for f in repo_facts.find_skills(sandbox)
        if set(repo_facts.frontmatter_of(f)) & set(validator.DISCOURAGED_KEYS)
    ]
    assert not offenders, f"now {len(offenders)} skills use a discouraged key"


# --------------------------------------------------------------------------
# Catalogue and prose counts -- the drift class that shipped three times
# --------------------------------------------------------------------------


def test_wrong_stated_count_is_an_error(sandbox, findings, repo_facts):
    path = sandbox / "README.md"
    total = repo_facts.facts(sandbox)["skills_total"]
    text = path.read_text().replace(f"**{total} skills**", f"**{total + 1} skills**", 1)
    path.write_text(text)
    assert "skills" in messages(findings("check_stated_counts", sandbox)).lower()


def test_catalogue_row_under_the_wrong_section_is_an_error(sandbox, findings):
    """The incident this check was written for: ml-best-practices stayed listed
    under Google Cloud after it moved to the `data` group, so the table told
    readers to run a --group that would never install it."""
    path = sandbox / "README.md"
    text = path.read_text()
    assert "`notebook-guidance`" in text, "catalogue shape changed; update this test"
    path.write_text(
        text.replace("`notebook-guidance`", "`ml-best-practices`, `notebook-guidance`", 1)
    )
    # Through check_readme_catalogue, which locates the section and then calls
    # check_catalogue_membership(repo, section, report) with it.
    assert "ml-best-practices" in messages(findings("check_readme_catalogue", sandbox))


def test_decorated_headings_do_not_unhook_the_catalogue(sandbox, findings):
    """Emoji in a heading must not silently disable the catalogue checks.

    This is the near-miss that motivated the whole suite: the section was found
    by literal string match, so decorating it would have failed open.
    """
    path = sandbox / "README.md"
    path.write_text(path.read_text().replace("## 📚 Skill catalogue", "## Skill catalogue", 1))
    out = messages(findings("check_readme_catalogue", sandbox))
    assert "No `## Skill catalogue` section" not in out
