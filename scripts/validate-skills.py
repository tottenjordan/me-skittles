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
- Relative markdown links resolve (warning; template placeholders are skipped)

Deliberately NOT checked here: required sections, line-count limits, and
Hugo-shortcode artifacts. Those are bundle-specific and owned by
claude/testing-handbook-skills/scripts/validate-skills.py.

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
MAX_DESCRIPTION_LENGTH = 1024
MIN_DESCRIPTION_LENGTH = 20
NAME_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
ARTIFACT_GLOBS = ("**/__pycache__", "**/*.pyc")

# Terms that must not appear under gemini/. The tree is a port of claude/,
# so a hit here means a Claude-tree file was copied across unmodified —
# the exact regression a naive upstream re-sync reintroduces.
CLAUDE_TERMS = re.compile(r"claude|anthropic", re.IGNORECASE)

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
    copied across without adaptation.
    """
    tree = repo / "gemini"
    if not tree.is_dir():
        return
    for path in sorted(tree.rglob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits = sorted({m.group(0).lower() for m in CLAUDE_TERMS.finditer(content)})
        if hits:
            report.error(
                path.relative_to(repo),
                f"Claude terminology in the Gemini tree: {hits} "
                "(port the content, do not copy it)",
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
    if "gemini" in trees:
        check_gemini_purity(repo, report)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report, args.verbose)

    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
