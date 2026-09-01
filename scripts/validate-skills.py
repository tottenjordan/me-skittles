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
- Descriptions stay under 500 chars — they are loaded every session (warning)
- Helper scripts declare their third-party dependencies (warning)
- No frontmatter keys the harness silently ignores (warning)
- Relative markdown links resolve (warning; template placeholders are skipped)

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
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

TREES = ("claude", "gemini")
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024   # hard API limit
MIN_DESCRIPTION_LENGTH = 20

# Every skill's description is loaded on every session, whether or not the skill
# fires — so description length is a fixed context tax that scales with the
# catalogue. At 117 skills the two trees already cost roughly 1.9k and 5.2k
# tokens per session. 1024 is the API ceiling; this is the budget that keeps the
# total sane, and the guidance calls a description "one line".
WARN_DESCRIPTION_LENGTH = 500

# Everything in SKILL.md loads up front, so detail that belongs in references/
# costs context on every single use. 500 is the repo's own documented standard --
# claude/writing-skills/anthropic-best-practices.md states it twice, including as
# a checklist item -- and is what the testing-handbook bundle validator enforces.
MAX_SKILL_LINES = 500
WARN_SKILL_LINES = 450
NAME_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
ARTIFACT_GLOBS = ("**/__pycache__", "**/*.pyc")

# Frontmatter keys that look right but are not what the harness reads.
# `when_to_use` is the worst of these: skills auto-trigger from `description`
# alone, so trigger conditions parked in `when_to_use` are simply never seen.
DISCOURAGED_KEYS = {
    "when_to_use": "triggers belong in `description` — only that field drives auto-triggering",
    "tools": "skills use `allowed-tools`; `tools` is the agent-definition field",
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


def extract_frontmatter(content: str) -> tuple[dict | None, str | None]:
    """Return (parsed frontmatter, error message). Exactly one will be set."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, "No frontmatter (file must start with ---)"

    end = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if end is None:
        return None, "Frontmatter not closed (missing closing ---)"

    try:
        parsed = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        return None, f"YAML parse error: {exc}"

    if parsed is not None and not isinstance(parsed, dict):
        return None, "Frontmatter is not a mapping"
    return parsed or {}, None


def check_skill(skill_file: Path, repo: Path, report: Report) -> None:
    """Validate one SKILL.md: frontmatter fields and relative links."""
    rel = skill_file.relative_to(repo)
    try:
        content = skill_file.read_text(encoding="utf-8")
    except OSError as exc:
        report.error(rel, f"Unreadable: {exc}")
        return

    frontmatter, error = extract_frontmatter(content)
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


def check_artifacts(repo: Path, report: Report) -> None:
    """Build artifacts should never be committed."""
    for pattern in ARTIFACT_GLOBS:
        for path in sorted(repo.glob(pattern)):
            if ".git" in path.parts:
                continue
            report.error(path.relative_to(repo), "Committed build artifact")


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
    return


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
    """Warn on keys the harness ignores but an author may believe are load-bearing."""
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
            imported = set(re.findall(r"^\s*(?:import|from)\s+([a-zA-Z_]\w*)", src, re.M))
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


def find_skills(repo: Path, trees: tuple[str, ...]) -> list[Path]:
    """Locate every SKILL.md, including those nested inside plugin bundles."""
    found: list[Path] = []
    for tree in trees:
        root = repo / tree
        if root.is_dir():
            found.extend(root.rglob("SKILL.md"))
    return sorted(found)


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
