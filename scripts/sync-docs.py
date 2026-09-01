#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Regenerate the pure-data tables in README.md from scripts/repo_facts.py.

Two regions are generated, each delimited by an HTML comment so it is invisible
in rendered Markdown: the context-cost-by-tree table and the per-group cost
table. Every cell in both is a number or a name derived from the working tree,
which is exactly why they drift when hand-maintained — four stale figures so far.

    uv run scripts/sync-docs.py            # rewrite in place
    uv run scripts/sync-docs.py --check    # CI: diff and fail, never write

`--check` returns before reaching any write, deliberately: the precedent for
this script is `markdown-magic --dry`, which mutated the file it was asked only
to inspect and then exited 0. A "safe" mode that writes is worse than no safe
mode, because CI stops being able to tell you the file was wrong.

Prose stays out. Only tables whose every cell is derived belong inside the
markers — the **Method** paragraph below them, and the "What it covers" column
of the skill catalogue, are editorial and are hand-written. Generating those
would flatten the most useful writing in the file. The catalogue is instead
*validated* by scripts/validate-skills.py.

No numbers are computed here. `repo_facts.facts()` is the single source of
derived facts; this module only lays them out. If a figure this prints is
wrong, it is wrong in repo_facts.py.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

# Same directory, so `uv run scripts/sync-docs.py` resolves it with no path
# setup. Kept below the stdlib block for ruff, as in scripts/repo_facts.py.
from repo_facts import TREES, facts

README = "README.md"
WARNING = "edits here are overwritten by scripts/sync-docs.py"


def begin_marker(name: str) -> str:
    """Opening delimiter. It carries the warning because humans edit here.

    Of the generators surveyed, only `cog` defends a generated region against a
    hand-edit at all. `--check` is that defence; this comment is what tells the
    person mid-edit, before CI has to.
    """
    return f"<!-- BEGIN GENERATED: {name} — {WARNING} -->"


def end_marker(name: str) -> str:
    """Closing delimiter. Bare: the warning has already been read by here."""
    return f"<!-- END GENERATED: {name} -->"


SHIELD = (
    '<img src="https://img.shields.io/badge/{label}-{message}-{colour}?style=flat-square"'
    ' alt="{alt}" />'
)


def cost_by_tree(data: dict) -> list[str]:
    """Standing per-session cost, and what one firing skill adds, per tree."""
    rows = [
        "| | Skills | Description budget | When one fires |",
        "|---|---|---|---|",
    ]
    rows.extend(
        f"| `{tree}/` | {data['described_by_tree'][tree]} top-level "
        f"| ~{data['tokens_k_by_tree'][tree]} tokens per session "
        f"| +{data['median_skill_tokens_k_by_tree'][tree]} tokens median |"
        for tree in TREES
    )
    return rows


def group_cell(group: dict | None) -> str:
    """One group's cost in one tree, or an em dash where the group does not exist."""
    if group is None:
        return "—"
    count = group["skill_count"]
    plural = "" if count == 1 else "s"
    return f"{count} skill{plural} · ~{group['tokens_rounded']:,} tokens"


def cost_by_group(data: dict) -> list[str]:
    """Per-group cost side by side, in groups.toml order, then the whole-tree total."""
    groups = data["groups"]
    names = list(dict.fromkeys(name for _tree, name in groups))
    rows = ["| Group | `claude/` | `gemini/` |", "|---|---|---|"]
    rows.extend(
        "| `{}` | {} |".format(
            name, " | ".join(group_cell(groups.get((tree, name))) for tree in TREES)
        )
        for name in names
    )
    totals = " | ".join(
        f"{data['skills_by_tree'][tree]} skills · ~{data['tokens_k_by_tree'][tree]}"
        for tree in TREES
    )
    rows.append(f"| **whole tree** | {totals} |")
    return rows


def shield(label: str, message: str, colour: str, alt: str) -> str:
    """One indented shields.io badge. `label`/`message` are URL-encoded; `alt` is not."""
    return "  " + SHIELD.format(label=label, message=message, colour=colour, alt=alt)


def badges(data: dict) -> list[str]:
    """Shields.io badges. Generated because three of them state derived counts.

    A badge is the most visible number in the file and the least likely to be
    re-checked by eye, so hand-maintaining `skills-117` is how a README ends up
    advertising a figure the tree stopped matching.
    """
    skills = data["skills_total"]
    claude, gemini = (data["skills_by_tree"][tree] for tree in TREES)
    return [
        '<p align="center">',
        shield("skills", skills, "8A2BE2", f"{skills} skills"),
        shield("Claude%20Code", f"{claude}%20skills", "D97757", f"Claude Code: {claude} skills"),
        shield("Gemini%20CLI", f"{gemini}%20skills", "4285F4", f"Gemini CLI: {gemini} skills"),
        shield("python", "3.11%2B", "3776AB", "Python 3.11+"),
        shield("packaging", "uv", "DE5FE9", "packaging: uv"),
        shield("lint", "ruff", "D7FF64", "lint: ruff"),
        shield("license", "Apache%202.0", "green", "license: Apache 2.0"),
        "</p>",
    ]


BLOCKS = {
    "badges": badges,
    "context-cost-tree": cost_by_tree,
    "group-costs": cost_by_group,
}


def render(text: str, data: dict) -> str:
    """Return `text` with every generated region replaced by freshly built content."""
    for name, build in BLOCKS.items():
        begin, end = begin_marker(name), end_marker(name)
        region = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
        # Blank lines around the table are cosmetic, not structural. A comment
        # is a CommonMark type-2 HTML block, which closes at its own `-->`, so
        # a table butted straight against a marker still renders as a table
        # (verified through cmark-gfm, markdown-it-py and Python-Markdown).
        # They are here so the marker reads as a separate thing from the table.
        block = "\n\n".join([begin, "\n".join(build(data)), end])
        # A function replacement, so backslashes and \g in the table stay literal.
        text, found = region.subn(lambda _match, block=block: block, text)
        if found != 1:
            raise SystemExit(f"{README}: expected exactly 1 '{name}' region, found {found}")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="print a diff and exit non-zero if README.md is stale; never writes",
    )
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent
    readme = repo / README
    current = readme.read_text(encoding="utf-8")
    updated = render(current, facts(repo))

    if args.check:
        if current == updated:
            print(f"{README}: generated regions are up to date")
            return 0
        sys.stdout.writelines(
            difflib.unified_diff(
                current.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=f"{README} (on disk)",
                tofile=f"{README} (generated)",
            )
        )
        print(f"\n{README} is stale — run `uv run scripts/sync-docs.py`")
        return 1

    if current == updated:
        print(f"{README}: generated regions are up to date")
        return 0
    readme.write_text(updated, encoding="utf-8")
    print(f"{README}: regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
