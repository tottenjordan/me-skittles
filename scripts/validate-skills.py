#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Repo-wide structural validation for every SKILL.md in claude/ and gemini/.

Checks the invariants that make a skill loadable and keep the two trees honest:

- Frontmatter is present, closed, and parses as YAML
- `name` exists, is lowercase-kebab, and matches its directory
- `description` exists and is non-trivial (skills auto-trigger from it)
- No dangling symlinks anywhere in the repo
- No committed build artifacts (__pycache__, *.pyc)
- gemini/ contains no Claude-specific terminology (it is a port, not a copy)
- Plugin bundles use the manifest directory matching their tree
- SKILL.md stays under 500 lines (warns at 450) so progressive disclosure is preserved
- No retired model IDs outside of text that discusses their retirement
- groups.toml parses, has every required key, puts each skill directory in
  exactly one group for its tree, and means the same thing to tomllib as it
  does to the installer's awk parser (scripts/parse-groups.awk, run here)
- The README skill catalogue names no skill that does not exist, and files each
  skill under the section for the group that actually installs it
- Counts stated in prose in README.md, CLAUDE.md, GEMINI.md and ATTRIBUTION.md
  agree with scripts/repo_facts.py. Those four (see LIVE_DOCS), plus any plan
  that opted in with a `<!-- live-counts -->` line; docs/notes/ and the rest of
  docs/plans/ are point-in-time records and stay exempt (see PLAN_LIVE_MARKER)
- Descriptions stay under 500 chars — they are loaded every session (warning)
- Helper scripts declare their third-party dependencies (warning)
- No frontmatter keys the harness silently ignores (warning)
- Relative markdown links resolve (warning; template placeholders are skipped)
- Every skill appears in the README skill catalogue (warning)

Deliberately NOT checked here: required per-type sections and Hugo-shortcode
artifacts. Those are bundle-specific and owned by
claude/testing-handbook-skills/scripts/validate-skills.py, which enforces the
same 500-line limit for the skills it covers.

Usage:
    uv run scripts/validate-skills.py            # validate everything
    uv run scripts/validate-skills.py --tree gemini
    uv run scripts/validate-skills.py --json     # machine-readable, for CI
    uv run scripts/validate-skills.py -v
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

# `tomllib` is stdlib from 3.11, which the PEP 723 header above requires. ruff
# does not read that header, so under its default target version it sorts the
# import here rather than into the stdlib block above; keep it here so
# `uvx ruff check` stays clean without a config file.
import tomllib

# Same directory, so `uv run scripts/validate-skills.py` resolves it with no path
# setup. It is the single source of derived facts, and of the constants and
# helpers below that scripts/sync-docs.py also needs: keeping a second copy here
# is how two readers of one file drift apart, which is the whole reason
# check_groups_parser_agreement exists.
#
# pyyaml stays declared in the PEP 723 header above even though nothing here
# imports yaml any more — repo_facts does, so `uv run` still has to install it.
from repo_facts import (
    TOKEN_STEP,
    TREES,
    WARN_DESCRIPTION_LENGTH,
    estimate_tokens,
    facts,
    find_skills,
    installable_skills,
    parse_frontmatter,
    percent_of,
)

MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024   # hard API limit
MIN_DESCRIPTION_LENGTH = 20

# WARN_DESCRIPTION_LENGTH is imported from repo_facts: every skill's description
# is loaded on every session whether or not the skill fires, the README quotes
# how many skills exceed the limit, and the same number has to mean both things.
# 1024 above is the API ceiling; that one is the budget that keeps the total sane.

# Everything in SKILL.md loads up front, so detail that belongs in references/
# costs context on every single use. 500 is the repo's own documented standard --
# claude/writing-skills/anthropic-best-practices.md states it twice, including as
# a checklist item -- and is what the testing-handbook bundle validator enforces.
MAX_SKILL_LINES = 500
WARN_SKILL_LINES = 450
NAME_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")

# Stricter form, used only when deciding whether a backticked token in the
# README catalogue is a skill name. NAME_PATTERN also accepts leading, trailing
# and doubled hyphens, so a flag such as `--group` in a catalogue cell would be
# read as a skill and reported as a dangling entry. Frontmatter `name` keeps the
# looser pattern, which is the rule that field is actually held to.
#
# The length lookahead keeps this strictly narrower than NAME_PATTERN: it must
# only ever reject more tokens, never accept ones the old scan skipped.
CATALOGUE_NAME_PATTERN = re.compile(r"^(?=.{1,64}$)[a-z0-9]+(?:-[a-z0-9]+)*$")

LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
ARTIFACT_GLOBS = ("**/__pycache__", "**/*.pyc")

# Frontmatter keys outside the Agent Skills spec, which defines exactly six:
# name, description, license, compatibility, metadata, allowed-tools.
#
# The hazard is not that a harness ignores these -- Claude Code reads both, and
# documents `when_to_use` as "Appended to `description` in the skill listing".
# It is that "works in Claude Code" is not "portable": the spec's reference
# validator treats an unknown top-level key as a hard error, and so do
# package_skill.py, the Skills API and claude.ai upload, which fail with
# `Unexpected key(s) in SKILL.md frontmatter` rather than ignoring the field.
#
# Kept a warning, not an error, on purpose. Promoting it would force deleting
# real trigger surface from skills that work today to satisfy a packaging path
# this repo does not currently publish through. Revisit if we ever push to a
# registry -- see docs/notes/multi-harness-skills.md.
DISCOURAGED_KEYS = {
    "when_to_use": (
        "not in the Agent Skills spec — Claude Code honours it, but packaging and upload "
        "reject it; fold the trigger text into `description`"
    ),
    "tools": (
        "not in the Agent Skills spec — skills use `allowed-tools`; `tools` is the "
        "agent-definition field"
    ),
}

# Model IDs that providers have retired. Skills documenting a dead model send
# callers to an endpoint that 404s, and this rots silently — the audit that
# added this check found gemini-2.0-flash in 76 places, months after shutdown.
# Value is the current replacement.
DEPRECATED_MODELS = {
    "gemini-2.0-flash": "gemini-flash-latest",
    "gemini-2.0-flash-exp": "gemini-flash-latest",
    "gemini-1.5-pro": "gemini-3.1-pro-preview",
    "gemini-1.5-flash": "gemini-flash-latest",
    "gemini-3-flash-preview": "gemini-3.5-flash",
    "gemini-3-pro-preview": "gemini-3.1-pro-preview",
    "gemini-3-pro-image-preview": "gemini-3-pro-image",
    "gemini-3.1-flash-image-preview": "gemini-3.1-flash-image",
    "gemini-2.5-flash-image": "gemini-3.1-flash-image",
    "claude-sonnet-4-5": "claude-sonnet-5",
    "gpt-4": "gpt-5.6",
}

# A line that is *about* a model's retirement may name it legitimately.
DEPRECATION_CONTEXT = re.compile(
    r"deprecat|shut ?down|retired|superseded|no longer|do not pin|avoid any|since\b", re.IGNORECASE
)

# Terms that must not appear under gemini/. The tree is a port of claude/,
# so a hit here means a Claude-tree file was copied across unmodified —
# the exact regression a naive upstream re-sync reintroduces.
#
# The pattern stays deliberately broad. Narrowing it to markers like CLAUDE.md
# or .claude-plugin would miss most of the 29 leakage files it originally
# caught, which mentioned Claude only in prose.
CLAUDE_TERMS = re.compile(r"claude|anthropic", re.IGNORECASE)

# Files under gemini/ permitted to mention Claude, each with the reason why.
#
# These are references to Claude as a third-party tool — an MCP client, or a
# label value naming which agent ran a job — not Claude-tree content copied
# across. Every entry needs a reason; a file not listed here still fails, so
# adding one is a visible decision in review rather than a silent weakening.
GEMINI_PURITY_ALLOWLIST: dict[str, str] = {
    "gemini/google-cloud-storage-basics/references/mcp-usage.md": (
        "documents Claude Desktop and Claude Code as MCP clients for the GCS MCP server"
    ),
    "gemini/enforcing-resource-attribution/SKILL.md": (
        "'claude' is an enumerated attribution label value alongside 'workstation' and 'gemini-cli'"
    ),
    "gemini/gcp-pipeline-orchestration/SKILL.md": (
        "'job:datacloud:claude' is a documented Composer job label value"
    ),
}

# Manifest directory each tree's plugin bundles must use.
PLUGIN_DIR = {"claude": ".claude-plugin", "gemini": ".gemini-plugin"}

# groups.toml drives `./scripts/install.sh --group`, and the installer reads it
# with awk rather than a TOML parser. These checks are what make that safe: the
# manifest is guaranteed here to be well-formed, complete, disjoint, and to mean
# the same thing to that awk program as it does to tomllib.
GROUPS_FILE = "groups.toml"
GROUPS_PARSER = "scripts/parse-groups.awk"
GROUP_REQUIRED_KEYS = ("name", "tree", "description", "skills", "budget_tokens")

# A group's declared ceiling may exceed what it actually costs -- headroom is the
# point -- but a budget far above the real figure enforces nothing. Warn past
# this ratio so a ceiling cannot be quietly set high enough to never bind.
GROUP_BUDGET_SLACK = 1.5

# How many disagreeing entries to name before truncating; the first handful
# already identify the cause.
MAX_REPORTED_TRIPLES = 12

# The README's catalogue is checked against the trees because it has shipped
# entries for skills that did not exist -- four dangling `adk-*` rows survived
# the removal of the skills they named.
README_FILE = "README.md"

# The catalogue section is found by its *label*, not a literal heading string, so
# decorating headings (an emoji prefix, a trailing note) cannot silently unhook
# the check. Encoding the decoration into the constant instead would mean every
# cosmetic README edit is also a code edit — and a missed one fails open.
README_CATALOGUE_LABEL = "skill catalogue"
README_CATALOGUE_HEADING = "## Skill catalogue"   # for messages only

# Leading decoration on a heading: emoji, symbols, whitespace. Stripped before a
# heading is matched to CATALOGUE_SECTION_GROUPS.
HEADING_DECORATION = re.compile(r"^[^0-9A-Za-z`]+")
BACKTICKED = re.compile(r"`([^`\n]+)`")

# A parenthesised annotation on a catalogue entry, e.g. `gcp-data-pipelines`
# (router) or `property-based-testing` *(bundle)*.
CELL_ANNOTATION = re.compile(r"\*?\([^)]*\)\*?")

# `## Skill catalogue` subsections, mapped to the groups.toml group each one
# enumerates. Keyed by the heading's leading label — the words before its em dash
# or its parenthesised tree note, lowercased; see `section_label`.
#
# The mapping is explicit because headings are editorial and will not match group
# names: `### Google Cloud and data` enumerates `gcp`, and `### Meta — authoring
# skills and agent config` enumerates `meta`. Inferring the group from the words
# would be a guess, and a wrong guess reports hand-written prose as broken. A
# section with no entry here is simply not membership-checked.
CATALOGUE_SECTION_GROUPS = {
    "agents": "agents",
    "development workflow": "workflow",
    "testing": "testing",
    "diagrams": "diagrams",
    "tools and automation": "tools",
    "meta": "meta",
    "google cloud and data": "gcp",
}

# Splits a heading at the first em dash, en dash, or `(`/`*(` annotation.
SECTION_LABEL_SPLIT = re.compile(r"[—–]|\*?\(")

# Documents whose stated numbers are checked against scripts/repo_facts.py by
# `check_stated_counts`. Named explicitly, and deliberately short.
#
# Everything under docs/notes/ and docs/plans/ is excluded on purpose, because it
# is a point-in-time record rather than a description of the repo as it is now:
# docs/notes/decisions-not-taken.md gives gcp-diagram's file count because that
# measurement is what justified the decision, and a plan says "10 of 16 skills
# fail" because that state is what motivated the work. Re-stating either as
# today's number would destroy the evidence, so historical documents are neither
# validated here nor generated into by scripts/sync-docs.py.
#
# Making the set a constant rather than a side effect of which paths the checks
# happen to walk means the exemption survives someone adding a new check, and
# means a new live document has to be added here deliberately.
LIVE_DOCS = ("README.md", "CLAUDE.md", "GEMINI.md", "ATTRIBUTION.md")

# A plan is a live document for the few days it is being executed and a
# historical record forever after, and the blanket docs/plans/ exemption above
# fits only the second half. A plan opts into the first half by carrying this
# marker line; `check_stated_counts` then checks its numbers alongside LIVE_DOCS.
#
# Opting *out* is deleting the marker, which is deliberately the cheaper edit:
# a finished plan that forgot to opt out fails with a one-line fix, and the
# stale number that justified the work is never rewritten. Same explicit-opt-in
# shape as CATALOGUE_SECTION_GROUPS and GEMINI_PURITY_ALLOWLIST — a file is only
# ever covered because someone said so in the file.
PLANS_DIR = "docs/plans"
PLAN_LIVE_MARKER = "<!-- live-counts -->"

# Where this file names itself, for findings whose fix is in this file.
SELF = "scripts/validate-skills.py"


@dataclass
class Finding:
    """A single validation failure or warning, anchored to a file."""

    path: str
    message: str
    level: str = "error"

    def to_dict(self) -> dict:
        return {"path": self.path, "message": self.message, "level": self.level}


@dataclass
class Report:
    """Aggregate findings across the repo."""

    findings: list[Finding] = field(default_factory=list)
    skills_checked: int = 0

    def error(self, path: Path | str, message: str) -> None:
        self.findings.append(Finding(str(path), message, "error"))

    def warn(self, path: Path | str, message: str) -> None:
        self.findings.append(Finding(str(path), message, "warning"))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warning"]

    def to_dict(self) -> dict:
        return {
            "summary": {
                "skills_checked": self.skills_checked,
                "errors": len(self.errors),
                "warnings": len(self.warnings),
            },
            "findings": [f.to_dict() for f in self.findings],
        }


@cache
def repo_facts_for(repo: Path) -> dict:
    """`repo_facts.facts()` for this repo, computed once per run.

    It walks both trees and reads every SKILL.md. Two checks below need it, and
    they should describe the same snapshot as each other in any case.
    """
    return facts(repo)


def installable_sets(repo: Path) -> dict[str, set[str]]:
    """`repo_facts.installable_skills` as sets, for membership and difference."""
    return {tree: set(names) for tree, names in installable_skills(repo).items()}


def check_skill(skill_file: Path, repo: Path, report: Report) -> None:
    """Validate one SKILL.md: frontmatter fields and relative links."""
    rel = skill_file.relative_to(repo)
    try:
        content = skill_file.read_text(encoding="utf-8")
    except OSError as exc:
        report.error(rel, f"Unreadable: {exc}")
        return

    frontmatter, error = parse_frontmatter(content)
    if error:
        report.error(rel, error)
        return
    assert frontmatter is not None

    expected = skill_file.parent.name
    name = frontmatter.get("name")
    if not name:
        report.error(rel, "Missing required field: name")
    else:
        name = str(name)
        if not NAME_PATTERN.match(name):
            report.error(
                rel,
                f"Invalid name {name!r}: must be lowercase alphanumeric with hyphens, "
                f"max {MAX_NAME_LENGTH} chars",
            )
        elif name != expected:
            report.error(rel, f"Name {name!r} does not match directory {expected!r}")

    description = frontmatter.get("description")
    if not description:
        report.error(rel, "Missing required field: description (skills auto-trigger from it)")
    else:
        description = str(description).strip()
        if len(description) < MIN_DESCRIPTION_LENGTH:
            report.error(
                rel,
                f"Description too short ({len(description)} chars): write it as trigger "
                "conditions, not a title",
            )
        elif len(description) > MAX_DESCRIPTION_LENGTH:
            report.error(
                rel, f"Description too long: {len(description)} chars (max {MAX_DESCRIPTION_LENGTH})"
            )
        elif len(description) > WARN_DESCRIPTION_LENGTH:
            report.warn(
                rel,
                f"Description is {len(description)} chars — every session pays for this whether "
                f"or not the skill fires; aim under {WARN_DESCRIPTION_LENGTH}",
            )

    check_line_count(skill_file, repo, content, report)
    check_frontmatter_keys(skill_file, repo, frontmatter, report)
    check_links(content, skill_file, repo, report)


def check_links(content: str, skill_file: Path, repo: Path, report: Report) -> None:
    """Warn on relative markdown links that do not resolve.

    Skips external URLs, anchors, and template placeholders such as
    `{baseDir}/references/x.md` or `../images/{prefix}_arch.png`, which are
    substituted at runtime rather than being real paths.
    """
    rel = skill_file.relative_to(repo)
    broken = []
    for target in LINK_PATTERN.findall(content):
        if target.startswith(("http://", "https://", "mailto:", "#", "/")):
            continue
        if "{" in target or "}" in target:
            continue
        path = target.split("#")[0].strip()
        if not path:
            continue
        if not (skill_file.parent / path).exists():
            broken.append(path)
    if broken:
        report.warn(rel, f"Unresolved relative links: {sorted(set(broken))}")


def check_symlinks(repo: Path, report: Report) -> None:
    """Every symlink must resolve. Dangling ones ship as broken skills."""
    for link in sorted(repo.rglob("*")):
        if ".git" in link.parts:
            continue
        if link.is_symlink() and not link.exists():
            report.error(
                link.relative_to(repo), f"Dangling symlink -> {link.readlink()}"
            )


def tracked_paths(repo: Path) -> set[str] | None:
    """Every path git tracks, or None if git cannot be consulted."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "ls-files"],
            capture_output=True, text=True, check=True, timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return set(out.splitlines())


def check_artifacts(repo: Path, report: Report) -> None:
    """Build artifacts should never be *committed*.

    Only tracked paths count. `__pycache__` is gitignored, so merely importing
    a script in this directory used to fail validation with "Committed build
    artifact" for a file git had never seen — a false positive whose message
    sent you looking for a commit that did not exist.

    If git cannot be consulted, fall back to flagging every artifact: better a
    false positive than silently missing a real one.
    """
    tracked = tracked_paths(repo)
    for pattern in ARTIFACT_GLOBS:
        for path in sorted(repo.glob(pattern)):
            if ".git" in path.parts:
                continue
            rel = path.relative_to(repo)
            if tracked is not None and rel.as_posix() not in tracked:
                continue  # local build detritus, not committed
            report.error(
                rel,
                "Committed build artifact"
                if tracked is not None
                else "Build artifact (could not consult git to confirm it is tracked)",
            )


def check_gemini_purity(repo: Path, report: Report) -> None:
    """gemini/ must not contain Claude terminology.

    The tree is a port, not a mirror. A hit means Claude-tree content was
    copied across without adaptation. Files in GEMINI_PURITY_ALLOWLIST are
    exempt — they reference Claude as a third-party tool rather than being
    unported Claude-tree content.
    """
    tree = repo / "gemini"
    if not tree.is_dir():
        return
    seen_allowed: set[str] = set()
    for path in sorted(tree.rglob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits = sorted({m.group(0).lower() for m in CLAUDE_TERMS.finditer(content)})
        if not hits:
            continue
        rel = path.relative_to(repo).as_posix()
        if rel in GEMINI_PURITY_ALLOWLIST:
            seen_allowed.add(rel)
            continue
        report.error(
            rel,
            f"Claude terminology in the Gemini tree: {hits} "
            "(port the content, do not copy it; if this is a legitimate "
            "third-party reference, add it to GEMINI_PURITY_ALLOWLIST with a reason)",
        )

    # A stale allowlist entry hides the fact that the exemption is no longer
    # needed, so surface it rather than letting it accumulate.
    for rel in sorted(set(GEMINI_PURITY_ALLOWLIST) - seen_allowed):
        report.warn(rel, "Stale GEMINI_PURITY_ALLOWLIST entry: file is absent or no longer matches")


def check_deprecated_models(repo: Path, report: Report) -> None:
    """Flag retired model IDs outside of text that discusses their retirement.

    Documenting a dead model ID hands the reader an endpoint that 404s. Lines
    that are explicitly about a deprecation are allowed to name the model.
    """
    for tree in TREES:
        root = repo / tree
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".md", ".py", ".sh", ".js", ".ts"} or not path.is_file():
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for num, line in enumerate(lines, start=1):
                if DEPRECATION_CONTEXT.search(line):
                    continue
                for dead, live in DEPRECATED_MODELS.items():
                    # Word-boundary right side so gemini-2.0-flash does not
                    # match inside gemini-2.0-flash-exp, which has its own entry.
                    if re.search(rf"(?<![\w.-]){re.escape(dead)}(?![\w.-])", line):
                        report.error(
                            f"{path.relative_to(repo)}:{num}",
                            f"Retired model ID {dead!r} — use {live!r} "
                            "(or mention the shutdown explicitly on this line)",
                        )


def check_line_count(skill_file: Path, repo: Path, content: str, report: Report) -> None:
    """Enforce the documented 500-line SKILL.md ceiling.

    Long skills defeat progressive disclosure: SKILL.md is loaded in full whenever
    the skill triggers, so reference detail left inline is paid for on every use.
    Move it into references/ and link it.
    """
    n = content.count("\n") + 1
    rel = skill_file.relative_to(repo)
    if n > MAX_SKILL_LINES:
        report.error(
            rel,
            f"SKILL.md is {n} lines (limit {MAX_SKILL_LINES}) — move detail into references/ "
            "and leave a link behind",
        )
    elif n > WARN_SKILL_LINES:
        report.warn(rel, f"SKILL.md is {n} lines, approaching the {MAX_SKILL_LINES}-line limit")


def check_frontmatter_keys(skill_file: Path, repo: Path, frontmatter: dict, report: Report) -> None:
    """Warn on frontmatter keys outside the six the Agent Skills spec defines."""
    for key, why in DISCOURAGED_KEYS.items():
        if key in frontmatter:
            report.warn(skill_file.relative_to(repo), f"Frontmatter key `{key}`: {why}")


def check_script_dependencies(repo: Path, report: Report) -> None:
    """Warn when a helper script imports a third-party package it never declares.

    A skill's script is only useful if it runs. Without a declaration the reader
    has to infer the install list from import statements, and gets an
    ImportError if they guess wrong. Declaring PEP 723 inline metadata makes
    `uv run <script>` self-installing — the pattern this repo already uses.

    Local sibling modules are not third-party, so a `.py` next to the script
    counts as satisfied.
    """
    stdlib = set(sys.stdlib_module_names)
    for tree in TREES:
        root = repo / tree
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            if "node_modules" in path.parts or "__pycache__" in path.parts:
                continue
            try:
                src = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "# /// script" in src:
                continue  # declares its own dependencies
            if any((p / "pyproject.toml").exists() for p in (path.parent, path.parent.parent)):
                continue  # covered by a project manifest
            siblings = {p.stem for p in path.parent.glob("*.py")} | {
                p.name for p in path.parent.iterdir() if p.is_dir()
            }
            # An import guarded by `except ImportError` is an availability probe,
            # not a hard requirement — check_install.py exists precisely to detect
            # a missing package, so declaring it would defeat the script.
            optional = set(
                re.findall(
                    r"try:\s*\n\s+(?:import|from)\s+([a-zA-Z_]\w*)[\s\S]{0,400}?except\s+"
                    r"\(?[\w\s,]*ImportError",
                    src,
                )
            )
            imported = set(re.findall(r"^\s*(?:import|from)\s+([a-zA-Z_]\w*)", src, re.MULTILINE))
            undeclared = sorted(imported - stdlib - siblings - optional)
            if undeclared:
                report.warn(
                    path.relative_to(repo),
                    f"Imports undeclared third-party packages {undeclared} — add PEP 723 "
                    "inline metadata (`# /// script`) so `uv run` installs them",
                )


def check_plugin_manifests(repo: Path, report: Report) -> None:
    """Plugin bundles must use the manifest directory matching their tree."""
    for tree in TREES:
        wrong = PLUGIN_DIR["gemini" if tree == "claude" else "claude"]
        for path in sorted((repo / tree).glob(f"*/{wrong}")):
            report.error(
                path.relative_to(repo),
                f"Wrong plugin manifest for {tree}/ tree; expected {PLUGIN_DIR[tree]}",
            )


def check_groups(repo: Path, report: Report) -> None:
    """groups.toml must partition every skill directory into exactly one group.

    `./scripts/install.sh --group` reads this manifest with awk, so it cannot
    validate the file it parses. Everything that makes the awk parser safe is
    enforced here instead: the file exists, parses as TOML, every entry carries
    all four required keys, names a real tree, lists only skills that exist, and
    reads identically through the installer's parser and through tomllib.

    Completeness and disjointness are the load-bearing part. A skill in no group
    is unreachable via `--group` and shows as `-` in `--list`; a skill in two
    groups makes `--list`'s single GROUP column a lie. Requiring an exact
    partition means adding a skill without grouping it fails CI, which is what
    keeps the manifest from silently drifting away from the trees.
    """
    path = repo / GROUPS_FILE
    if not path.is_file():
        report.error(GROUPS_FILE, "Missing — `./scripts/install.sh --group` reads this manifest")
        return
    try:
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        report.error(GROUPS_FILE, f"Unparseable: {exc}")
        return

    check_groups_parser_agreement(repo, text, data, report)

    entries = data.get("group")
    if not isinstance(entries, list) or not entries:
        report.error(GROUPS_FILE, "No [[group]] entries — every skill must belong to a group")
        return

    available = installable_sets(repo)
    membership: dict[tuple[str, str], list[str]] = {}  # (tree, skill) -> groups naming it
    seen_groups: set[tuple[str, str]] = set()

    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            report.error(GROUPS_FILE, f"[[group]] #{index}: not a table")
            continue
        label = entry.get("name")
        where = f"[[group]] #{index}" + (f" ({label})" if isinstance(label, str) else "")
        for key in GROUP_REQUIRED_KEYS:
            if not entry.get(key):
                report.error(GROUPS_FILE, f"{where}: missing required key `{key}`")
        if not all(entry.get(key) for key in ("name", "tree", "skills")):
            continue

        name, tree, skills = entry["name"], entry["tree"], entry["skills"]
        if tree not in TREES:
            report.error(
                GROUPS_FILE, f"{where}: tree {tree!r} must be one of {', '.join(TREES)}"
            )
            continue
        if (tree, name) in seen_groups:
            report.error(
                GROUPS_FILE,
                f"{where}: duplicate group {name!r} for tree {tree!r} — the installer merges "
                "these silently; use one entry per (tree, group)",
            )
        seen_groups.add((tree, name))

        if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
            report.error(GROUPS_FILE, f"{where}: `skills` must be a list of strings")
            continue
        for skill in skills:
            if skill not in available.get(tree, set()):
                report.error(
                    GROUPS_FILE,
                    f"{where}: lists {skill!r}, which is not a skill directory in {tree}/",
                )
                continue
            membership.setdefault((tree, skill), []).append(name)

    for tree, skills in sorted(available.items()):
        for skill in sorted(skills):
            groups = membership.get((tree, skill), [])
            if not groups:
                report.error(
                    GROUPS_FILE,
                    f"{tree}/{skill} is in no group — add it to one, or `--group` installs and "
                    "`--list` silently omit it",
                )
            elif len(groups) > 1:
                report.error(
                    GROUPS_FILE,
                    f"{tree}/{skill} is in more than one group ({', '.join(groups)}) — "
                    "membership must be disjoint, one group per skill per tree",
                )


def check_group_budgets(repo: Path, report: Report) -> None:
    """Hold each group to the context budget it declares in groups.toml.

    Why per group and not per skill. Every installed skill's description sits in
    the model's context for the whole session, whether or not the skill fires.
    Claude Code meters that listing at a documented 1% of the context window and,
    on overflow, drops descriptions starting with the skills you invoke least --
    so an over-large tree does not fail loudly, it silently strips the trigger
    keywords off exactly the skills nobody remembers to invoke by name. The
    per-skill description limit cannot see that, because the binding constraint
    is the sum. `--group` is the unit people install, so it is the unit to budget.

    Why declared, not a single global ceiling. A fixed ceiling would fail
    `gemini/gcp` today, and the only way to pass would be editing 26 vendored
    Apache-2.0 Google descriptions -- which docs/notes/decisions-not-taken.md
    already rejected, on the grounds that every such edit is paid again at the
    next upstream re-sync, and that installable groups solve the same problem
    without upstream divergence. A group being large is not the defect. A group
    growing past what someone signed off on, unnoticed, is. So the manifest
    carries the number and CI holds it there: raising a budget is a visible diff
    with a reviewer, the same shape as the terminology allowlist.

    Tokens are the repo's usual chars/4 estimate -- good for comparing groups
    against each other, not an invoice. Deliberately no absolute ceiling here:
    Claude Code's budget is a fraction of a context window that varies by model,
    and its docs state it in characters and in tokens interchangeably, so any
    single number this script hard-coded would be wrong for someone.
    """
    facts = repo_facts_for(repo)
    groups = facts.get("groups") or {}
    if not groups:
        return  # check_groups already reported why there is nothing to measure

    for (tree, name), group in sorted(groups.items()):
        where = f"[[group]] {name} ({tree})"
        declared = group.get("budget_tokens")
        actual = group["tokens"]

        if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
            # A missing key is check_groups' business; a present-but-unusable one is ours.
            if declared is not None:
                report.error(
                    GROUPS_FILE,
                    f"{where}: `budget_tokens` must be a positive integer, got {declared!r}",
                )
            continue

        if actual > declared:
            report.error(
                GROUPS_FILE,
                f"{where}: descriptions cost ~{actual} tokens, over its declared "
                f"budget_tokens = {declared} by {actual - declared}. Trim a description, move a "
                f"skill to another group, or raise the budget deliberately in this file",
            )
        elif declared > actual * GROUP_BUDGET_SLACK:
            report.warn(
                GROUPS_FILE,
                f"{where}: budget_tokens = {declared} is far above the ~{actual} tokens it "
                f"actually costs, so it constrains nothing — lower it toward the real figure",
            )


def toml_group_triples(data: dict) -> set[tuple[str, str, str]]:
    """(tree, group, skill) triples as a real TOML parser reads groups.toml.

    Non-string scalars are stringified rather than dropped: `name = 12` is legal
    TOML that declares a group, and pretending it does not exist here would hide
    it from the comparison below — which is precisely the case that needs to be
    caught, since the installer's parser cannot see it at all.
    """
    triples: set[tuple[str, str, str]] = set()
    entries = data.get("group")
    if not isinstance(entries, list):
        return triples
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name, tree, skills = entry.get("name"), entry.get("tree"), entry.get("skills")
        if name is None or tree is None or not isinstance(skills, list):
            continue
        if isinstance(name, (list, dict)) or isinstance(tree, (list, dict)):
            continue
        for skill in skills:
            if not isinstance(skill, (list, dict)):
                triples.add((str(tree), str(name), str(skill)))
    return triples


def awk_group_triples(repo: Path, report: Report) -> set[tuple[str, str, str]] | None:
    """Run the installer's own parser over groups.toml. None if it could not run."""
    parser = repo / GROUPS_PARSER
    if not parser.is_file():
        report.error(
            GROUPS_PARSER,
            "Missing — `./scripts/install.sh --group` reads groups.toml with this awk program, "
            "and this validator runs it to check the two agree",
        )
        return None
    try:
        proc = subprocess.run(
            ["awk", "-f", str(parser), str(repo / GROUPS_FILE)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        report.error(
            GROUPS_PARSER,
            f"Could not run `awk`: {exc} — awk is already a hard dependency of "
            "./scripts/install.sh, so it must be available to validate the manifest",
        )
        return None
    if proc.returncode != 0:
        report.error(
            GROUPS_PARSER,
            f"awk exited {proc.returncode} on {GROUPS_FILE}: {proc.stderr.strip() or 'no output'}",
        )
        return None

    triples: set[tuple[str, str, str]] = set()
    for num, line in enumerate(proc.stdout.splitlines(), start=1):
        fields = line.split("\t")
        if len(fields) != 3:
            report.error(GROUPS_PARSER, f"Emitted a non-triple on output line {num}: {line!r}")
            continue
        triples.add((fields[0], fields[1], fields[2]))
    return triples


def format_triples(triples: list[tuple[str, str, str]]) -> str:
    """Render disagreeing entries as tree/group:skill, truncated so a whole-file
    disagreement does not bury the cause under 85 near-identical lines."""
    head = triples[:MAX_REPORTED_TRIPLES]
    shown = ", ".join(f"{tree}/{group}:{skill}" for tree, group, skill in head)
    if len(triples) > MAX_REPORTED_TRIPLES:
        shown += f", … ({len(triples) - MAX_REPORTED_TRIPLES} more)"
    return shown


def check_groups_parser_agreement(repo: Path, text: str, data: dict, report: Report) -> None:
    """groups.toml must mean the same thing to awk as it does to tomllib.

    `./scripts/install.sh` reads this manifest with scripts/parse-groups.awk so
    it needs no TOML library, which leaves a gap: legal TOML that awk reads
    differently. The old guard here re-encoded awk's shape rules as regexes and
    drifted from them — it never checked that `name` and `tree` were *double*
    quoted, so `name = 'agents'` or `name = 12` validated clean while `--group
    agents` failed with "no group 'agents'".

    So compare instead of re-derive: run the very same awk file the installer
    runs, and require its (tree, group, skill) triples to equal tomllib's.
    Nothing to keep in sync, and the message names the entries that disagree.

    Multi-line strings stay a separate rule. Not every one of them changes awk's
    output — a multi-line `description` happens to be invisible to it, so the
    differential would pass — but the parser is line-oriented and any value
    spanning lines is one edit away from being read as a `name`, `tree` or
    `skills` line.
    """
    if '"""' in text or "'''" in text:
        report.error(
            GROUPS_FILE,
            "Multi-line strings break the installer's line-based awk parser — keep every "
            "value on one line",
        )

    from_awk = awk_group_triples(repo, report)
    if from_awk is None:
        return
    from_toml = toml_group_triples(data)

    missed = sorted(from_toml - from_awk)
    if missed:
        report.error(
            GROUPS_FILE,
            f"{GROUPS_PARSER} does not see {len(missed)} entr"
            f"{'y' if len(missed) == 1 else 'ies'} that tomllib reads here, so the installer "
            f"would silently skip {'it' if len(missed) == 1 else 'them'}: {format_triples(missed)}"
            " — that parser matches double-quoted strings, one skill per line, with nothing "
            "after `skills = [`",
        )

    invented = sorted(from_awk - from_toml)
    if invented:
        report.error(
            GROUPS_FILE,
            f"{GROUPS_PARSER} reads {len(invented)} entr"
            f"{'y' if len(invented) == 1 else 'ies'} that are not in the parsed TOML, so the "
            f"installer would act on something this file does not say: {format_triples(invented)}",
        )


def catalogue_entries(section: str) -> set[str]:
    """Skill names the catalogue *lists*, as opposed to merely mentions.

    A listing is a markdown table cell containing nothing but backticked names,
    optionally annotated: `adk`, or `gcp-data-pipelines` (router), or a
    comma-separated run of them. Everything else in the section — prose, and the
    "What it covers" column — is deliberately out of scope, because a name there
    is a reference rather than a catalogue entry. Two live cases depend on it:

    - `frontend-design` is named in prose as a pointer to the official Claude
      Code plugin, and is intentionally in neither tree
    - the `testing-handbook-skills` sub-skills are listed in prose; they live
      under the bundle's `skills/`, not as top-level directories

    Both are honest text, and neither is the defect this catches: a dangling
    table row left behind when a skill is deleted.
    """
    listed: set[str] = set()
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        for cell in line.strip().strip("|").split("|"):
            names = [n for n in BACKTICKED.findall(cell) if CATALOGUE_NAME_PATTERN.match(n)]
            if not names:
                continue
            remainder = BACKTICKED.sub("", cell)
            remainder = CELL_ANNOTATION.sub("", remainder)
            if remainder.strip(" ,\t"):
                continue  # a prose cell that happens to quote a name
            listed.update(names)
    return listed


def catalogue_sections(section: str) -> list[tuple[str, str]]:
    """The catalogue split into (heading, body) pairs, one per `###` subsection.

    Text before the first subsection belongs to no group and is dropped.
    """
    sections: list[tuple[str, str]] = []
    heading: str | None = None
    body: list[str] = []
    for line in section.splitlines():
        if line.startswith("### "):
            if heading is not None:
                sections.append((heading, "\n".join(body)))
            heading, body = line[4:].strip(), []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        sections.append((heading, "\n".join(body)))
    return sections


def section_label(heading: str) -> str:
    """A heading's stable part: the words before its dash or its `*(…)*` note.

    `Agents — ADK, A2A, Agent Engine *(both trees)*` reduces to `agents`, so
    CATALOGUE_SECTION_GROUPS survives an edit to the descriptive tail — which is
    the part of a heading that actually gets rewritten.
    """
    stem = SECTION_LABEL_SPLIT.split(heading, maxsplit=1)[0]
    return " ".join(HEADING_DECORATION.sub("", stem).split()).lower()


def check_catalogue_membership(repo: Path, section: str, report: Report) -> None:
    """A catalogue row must sit in the section for the group that installs it.

    Existence is not enough. `ml-best-practices` stayed listed under `### Google
    Cloud and data` after it was rehomed to the `data` group: the table was
    internally consistent, every name in it resolved, and it still told the
    reader to run a `--group gcp` that would never install that skill. Only
    groups.toml can settle it, so compare against groups.toml.

    Trees where the section's group does not exist are skipped — `gcp` is
    Gemini-only, so a Claude skill appearing there says nothing about claude/.
    """
    data = repo_facts_for(repo)
    group_of: dict[tuple[str, str], str] = {}
    groups_in_tree: dict[str, set[str]] = {}
    for (tree, group), members in data["groups"].items():
        groups_in_tree.setdefault(tree, set()).add(group)
        for skill in members["skills"]:
            group_of[(tree, skill)] = group

    mapped: set[str] = set()
    for heading, body in catalogue_sections(section):
        expected = CATALOGUE_SECTION_GROUPS.get(section_label(heading))
        if expected is None:
            continue  # editorial section with no group; guessing would be worse
        mapped.add(section_label(heading))
        for name in sorted(catalogue_entries(body)):
            for tree in TREES:
                if expected not in groups_in_tree.get(tree, set()):
                    continue
                actual = group_of.get((tree, name))
                if actual is None or actual == expected:
                    continue  # absent from this tree, or filed correctly
                report.error(
                    README_FILE,
                    f"Catalogue lists `{name}` under `### {heading}`, which is the `{expected}` "
                    f"group, but groups.toml puts {tree}/{name} in `{actual}` — "
                    f"`--group {expected}` will not install it; move the row, or regroup the skill",
                )

    # A heading that no longer matches leaves its section silently unchecked, so
    # say so — the same reasoning as the stale GEMINI_PURITY_ALLOWLIST warning.
    for label in sorted(set(CATALOGUE_SECTION_GROUPS) - mapped):
        report.warn(
            README_FILE,
            f"No `{README_CATALOGUE_HEADING}` subsection matches CATALOGUE_SECTION_GROUPS entry "
            f"{label!r}, so nothing checks that its group's rows are filed there — update the "
            f"mapping in {SELF} or drop the entry",
        )


def check_readme_catalogue(repo: Path, report: Report) -> None:
    """The README catalogue must match the trees in both directions.

    Naming a skill that does not exist is an error: readers install by name, and
    a dangling entry sends them looking for something that was deleted. Omitting
    one is a warning — the catalogue is how a skill gets discovered at all, but a
    missing row breaks nothing. Listing a real skill in the wrong section is an
    error too; see `check_catalogue_membership`.

    Sub-skills inside a plugin bundle count as existing, so the bundle listings
    resolve without an exemption.
    """
    path = repo / README_FILE
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")

    start = -1
    for m in re.finditer(r"^## (.+)$", text, re.MULTILINE):
        if section_label(m.group(1)) == README_CATALOGUE_LABEL:
            start = m.start()
            break
    if start < 0:
        report.warn(README_FILE, f"No `{README_CATALOGUE_HEADING}` section to check against")
        return
    end = text.find("\n## ", start + 3)
    section = text[start:] if end < 0 else text[start:end]

    check_catalogue_membership(repo, section, report)

    installable = installable_sets(repo)
    known = {skill for skills in installable.values() for skill in skills}
    known |= {p.parent.name for p in find_skills(repo, TREES)}  # bundle sub-skills

    listed = catalogue_entries(section)
    for name in sorted(listed - known):
        report.error(
            README_FILE,
            f"Catalogue lists `{name}`, which is not a skill in either tree — remove the entry, "
            "or restore the skill",
        )

    mentioned = {n for n in BACKTICKED.findall(section) if CATALOGUE_NAME_PATTERN.match(n)}
    for tree, skills in sorted(installable.items()):
        for skill in sorted(skills - mentioned):
            report.warn(README_FILE, f"{tree}/{skill} is missing from the skill catalogue")


def _skills_total(data: dict, _match: re.Match[str]) -> int | None:
    return data["skills_total"]


def _tree_skills(data: dict, match: re.Match[str]) -> int | None:
    return data["skills_by_tree"].get(match.group("tree"))


def _google_published(data: dict, _match: re.Match[str]) -> int | None:
    return len(data["google_published"])


def _shared_skills(data: dict, _match: re.Match[str]) -> int | None:
    return len(data["shared"])


def _gcp_group(data: dict, _match: re.Match[str]) -> int | None:
    group = data["groups"].get(("gemini", "gcp"))
    return None if group is None else group["skill_count"]


def _gcp_share_of_gemini(data: dict, _match: re.Match[str]) -> int | None:
    """The `gcp` group's share of the whole gemini tree's standing cost, as a %."""
    group = data["groups"].get(("gemini", "gcp"))
    total = data["tokens_by_tree"].get("gemini")
    if group is None or not total:
        return None
    return percent_of(group["tokens"], total)


def _claude_agents_and_workflow(data: dict, _match: re.Match[str]) -> int | None:
    """Standing cost of installing exactly `--group agents --group workflow`.

    Summed from characters and rounded once, not from the two published
    figures: rounding twice can land 10 tokens off, the same trap repo_facts
    avoids by computing `tokens` and `tokens_rounded` independently.
    """
    groups = [data["groups"].get(("claude", name)) for name in ("agents", "workflow")]
    if any(group is None for group in groups):
        return None
    return estimate_tokens(sum(group["description_chars"] for group in groups), TOKEN_STEP)


def _claude_tree_tokens_k(data: dict, _match: re.Match[str]) -> str | None:
    """The claude tree's standing cost as the docs quote it: the string `1.8k`.

    A string, not an int, because the sentence quotes the rendered figure. The
    comparison is textual, so `~1.80k` would be reported too.
    """
    return data["tokens_k_by_tree"].get("claude")


@dataclass(frozen=True)
class StatedCount:
    """A phrase that states a derived number, bound to the fact it states.

    `pattern` must capture the stated value as `n`, and may capture a tree as
    `tree`. `actual` returns the fact from repo_facts, or None when the match
    turns out not to name anything derivable after all — in which case nothing
    is reported.

    `actual` may return a **string** rather than an int, for figures the docs
    quote pre-formatted (`~1.8k`). The comparison is then textual against the
    captured `n`, so the rendering is checked along with the number.

    `expect` is how many sites across the checked documents this phrasing is
    known to match. It defaults to 1, and it exists because `matched` used to
    be a set: a pattern with four sites was only reported retired once *all
    four* stopped matching, so rewording one of them was silent. Counting
    against `expect` makes each site's disappearance visible. Getting `expect`
    wrong is self-correcting — too low and a genuine retirement goes unwarned,
    too high and the warning fires until someone fixes the number here.
    """

    pattern: re.Pattern[str]
    actual: Callable[[dict, re.Match[str]], int | str | None]
    what: str
    expect: int = 1


# Prose the generator cannot reach, matched phrase by phrase.
#
# Attribution is the whole design. A number is only checkable when the words
# around it say unambiguously which fact it is: `29 Google-published skills`
# does, a bare `29` does not. So each entry recognises a specific phrasing and
# binds it to one fact, and anything unrecognised is left alone. Coverage is
# explicitly the lesser goal — a check that guesses invents errors on
# hand-written prose, and a check that cries wolf gets switched off. Prefer
# missing a number to inventing a finding; that is the same trade
# check_script_dependencies makes when it exempts guarded imports.
#
# A phrasing that stops matching is warned about rather than silently dropped,
# so rewording the prose cannot quietly retire the check on it. `expect` is what
# makes that true per *site* rather than per pattern — four documents say
# `29 Google-published skills`, and rewording one of them has to be visible.
STATED_COUNTS: tuple[StatedCount, ...] = (
    StatedCount(
        re.compile(r"\*\*(?P<n>\d+) skills\*\* across"),
        _skills_total,
        "the number of SKILL.md files across both trees",
    ),
    StatedCount(
        re.compile(r"(?P<n>\d+) skills, 0 errors"),
        _skills_total,
        "the number of SKILL.md files the validator checks",
    ),
    StatedCount(
        re.compile(r"`(?P<tree>claude|gemini)/` \((?P<n>\d+)\)"),
        _tree_skills,
        "the number of top-level skill directories in that tree",
        expect=2,  # README.md, one per tree, on one line
    ),
    StatedCount(
        re.compile(r"`(?P<tree>claude|gemini)/`[^`\n]*?(?P<n>\d+) directories"),
        _tree_skills,
        "the number of top-level skill directories in that tree",
        expect=2,  # GEMINI.md, one per tree
    ),
    StatedCount(
        re.compile(r"^(?P<tree>claude|gemini)/\s+(?P<n>\d+) skills for"),
        _tree_skills,
        "the number of top-level skill directories in that tree",
        expect=2,  # README.md layout block, one per tree
    ),
    StatedCount(
        re.compile(r"The `(?P<tree>claude|gemini)/` tree[^\n]*?\*\*(?P<n>\d+) skills\*\*"),
        _tree_skills,
        "the number of top-level skill directories in that tree",
    ),
    StatedCount(
        re.compile(r"(?P<n>\d+) Google-published skills"),
        _google_published,
        "the number of skills declaring `publisher: google`",
        expect=4,  # README.md, CLAUDE.md, GEMINI.md twice
    ),
    StatedCount(
        re.compile(r"(?P<n>\d+)-skill Google Cloud family"),
        _google_published,
        "the number of skills declaring `publisher: google`",
    ),
    StatedCount(
        re.compile(r"(?P<n>\d+) Apache-2\.0 Google Cloud and BigQuery skills"),
        _google_published,
        "the number of skills declaring `publisher: google`",
    ),
    StatedCount(
        re.compile(r"(?P<n>\d+) skills under `gemini/`, each declaring"),
        _google_published,
        "the number of skills declaring `publisher: google`",
    ),
    StatedCount(
        re.compile(r"(?P<n>\d+) of them install as `--group gcp`"),
        _gcp_group,
        "the size of the gemini `gcp` group in groups.toml",
    ),
    StatedCount(
        re.compile(r"--group gcp` installs the (?P<n>\d+)"),
        _gcp_group,
        "the size of the gemini `gcp` group in groups.toml",
    ),
    StatedCount(
        re.compile(r"of which (?P<n>\d+) exist in both"),
        _shared_skills,
        "the number of skills present in both trees",
    ),
    # The three below sit in the paragraph immediately under the generated cost
    # tables. That is the exact position docs/notes/documentation-drift.md
    # names as the failure mode of generation — the marked region stays right
    # while the sentence beside it rots — so leaving the showcase unchecked
    # would have been the design demonstrating its own bug.
    StatedCount(
        re.compile(r"\*\*(?P<n>\d+)% of the Gemini tree's standing cost\*\*"),
        _gcp_share_of_gemini,
        "the gemini `gcp` group's share of that tree's description budget",
    ),
    StatedCount(
        re.compile(r"`--group agents --group workflow` costs ~(?P<n>[\d,]+)"),
        _claude_agents_and_workflow,
        "the combined description budget of the claude `agents` and `workflow` groups",
    ),
    StatedCount(
        re.compile(r"against ~(?P<n>[\d.]+k) for `--all`"),
        _claude_tree_tokens_k,
        "the claude tree's whole description budget",
    ),
)


def opted_in_plans(repo: Path) -> list[str]:
    """Plans carrying PLAN_LIVE_MARKER, which asks for their numbers to be checked.

    docs/plans/ is exempt by default because a plan records what was true when
    it was written. A plan being *executed* is the exception, and it says so in
    itself rather than in a list here — see PLAN_LIVE_MARKER.
    """
    plans = repo / PLANS_DIR
    if not plans.is_dir():
        return []
    marked = []
    for path in sorted(plans.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if PLAN_LIVE_MARKER in text:
            marked.append(path.relative_to(repo).as_posix())
    return marked


def check_stated_counts(repo: Path, report: Report) -> None:
    """Numbers stated in prose must agree with scripts/repo_facts.py.

    scripts/sync-docs.py generates the tables whose every cell is derived, but
    the counts in sentences — `**117 skills**`, `29 Google-published skills`,
    `26 of them install as --group gcp` — cannot be generated without flattening
    the writing around them. They are the ones that went stale, so they are
    checked instead.

    The documents checked are LIVE_DOCS, plus any plan that opted in with
    PLAN_LIVE_MARKER. Everything else under docs/notes/ and docs/plans/ states
    numbers that were true when written and must stay that way; see LIVE_DOCS.

    A phrasing that stops matching as many sites as its `expect` says warns,
    rather than silently retiring the check on that number. Only LIVE_DOCS
    sites count toward `expect`: an opted-in plan is transient, and letting it
    contribute would let a plan mask a live document's reworded sentence.
    """
    data = repo_facts_for(repo)
    sites: dict[str, int] = {}
    for doc in list(LIVE_DOCS) + opted_in_plans(repo):
        path = repo / doc
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for num, line in enumerate(lines, start=1):
            for rule in STATED_COUNTS:
                for match in rule.pattern.finditer(line):
                    actual = rule.actual(data, match)
                    if actual is None:
                        continue
                    if doc in LIVE_DOCS:
                        sites[rule.pattern.pattern] = sites.get(rule.pattern.pattern, 0) + 1
                    # `actual` is a string for figures the docs quote
                    # pre-formatted, e.g. `~1.8k`; compare those as text so the
                    # rendering is checked too.
                    text = match.group("n")
                    stated = text if isinstance(actual, str) else int(text.replace(",", ""))
                    if stated != actual:
                        report.error(
                            f"{doc}:{num}",
                            f"{match.group(0).strip()!r} states {stated}, but {rule.what} "
                            f"is {actual} — correct the prose, or the thing it describes",
                        )

    for rule in STATED_COUNTS:
        found = sites.get(rule.pattern.pattern, 0)
        if found < rule.expect:
            report.warn(
                SELF,
                f"The stated-count pattern {rule.pattern.pattern!r} ({rule.what}) matches "
                f"{found} live document site(s), expected {rule.expect} — wording it recognised "
                "was probably edited, and that number is no longer checked there; update the "
                "pattern, correct `expect`, or drop the rule",
            )


def print_report(report: Report, verbose: bool) -> None:
    by_path: dict[str, list[Finding]] = {}
    for finding in report.findings:
        by_path.setdefault(finding.path, []).append(finding)

    for path in sorted(by_path):
        print(f"\n{path}")
        for finding in by_path[path]:
            marker = "ERROR  " if finding.level == "error" else "WARNING"
            print(f"  {marker} {finding.message}")

    errors, warnings = len(report.errors), len(report.warnings)
    print("\n" + "-" * 60)
    print(f"Skills checked: {report.skills_checked}")
    print(f"Errors:         {errors}")
    print(f"Warnings:       {warnings}")
    print("-" * 60)
    print("✓ All skills valid" if errors == 0 else f"✗ {errors} error(s)")
    if warnings and not verbose:
        print("  (warnings do not fail the build)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repo-wide structural validation for SKILL.md files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--tree", choices=TREES, help="Validate only one tree")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repo root (defaults to the script's parent directory)",
    )
    args = parser.parse_args()

    repo: Path = args.repo.resolve()
    trees = (args.tree,) if args.tree else TREES

    skills = find_skills(repo, trees)
    if not skills:
        print(f"ERROR: No SKILL.md files found under {repo}", file=sys.stderr)
        return 1

    report = Report(skills_checked=len(skills))
    for skill in skills:
        check_skill(skill, repo, report)

    check_symlinks(repo, report)
    check_artifacts(repo, report)
    check_plugin_manifests(repo, report)
    check_groups(repo, report)
    check_group_budgets(repo, report)
    check_readme_catalogue(repo, report)
    check_stated_counts(repo, report)
    check_script_dependencies(repo, report)
    check_deprecated_models(repo, report)
    if "gemini" in trees:
        check_gemini_purity(repo, report)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report, args.verbose)

    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
