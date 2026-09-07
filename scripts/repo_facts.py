# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Single source of truth for every number the documentation is allowed to state.

The README, CLAUDE.md and GEMINI.md quote counts — 117 skills, 28 and 57 per
tree, 29 Google-published, per-group token budgets. Each of those was hand
counted once and then drifted, because nothing recomputed them. This module is
the one place they are derived; the docs generator writes from it and the
validator checks against it, so the two can disagree with reality but never
with each other.

`facts(repo)` returns a plain dict. To publish a new number, add a key here and
both consumers see it.

A library first, with one read-only convenience on top:

    uv run scripts/repo_facts.py    # every fact as JSON, keys sorted

That dump exists because docs/notes/documentation-drift.md tells you to
re-derive a number from this module rather than trust a stale one in a plan,
and advice you cannot execute is not a mitigation. It only prints; it writes
nothing and takes no arguments. No shebang and no exec bit — `uv run` is how
CODE_STANDARDS.md says to invoke a Python script, and the PEP 723 block above
makes that resolve pyyaml with no setup.

`groups` is keyed by a `(tree, name)` tuple, which JSON cannot express as an
object key, so the dump flattens it to `"gemini/gcp"`. See `_jsonable`.

Deliberately tolerant: unreadable or malformed frontmatter contributes nothing
rather than raising. Judging a skill malformed is scripts/validate-skills.py's
job, and a counter that crashes on the file the validator exists to report is
useless. Nothing prints on import, and importing runs no work — the dump is
under `if __name__ == "__main__"`.

The token estimate
------------------
README.md documents the method: for each group in `groups.toml`, sum the
`description` field from every member skill's `SKILL.md` frontmatter and divide
the character count by 4. Two details it leaves implicit, both recovered by
reproducing all fourteen of its published figures:

- **Published figures are rounded to the nearest 10 tokens, half away from
  zero.** `gemini.tools` is exactly 1220 chars — 305.0 tokens — and the README
  says ~310. Python's `round()` is half-to-even and would say 300, so this uses
  `Decimal` with `ROUND_HALF_UP` rather than the builtin.
- **Whitespace inside a description counts.** Collapsing runs of whitespace
  first understates `gemini.gcp` by 20 tokens and `gemini.data` by 10, because
  several Google-published skills write `description:` as a literal `|` block
  whose newlines and indentation survive YAML parsing. Those characters really
  are loaded into context, so they really are part of the cost. Only leading
  and trailing whitespace is stripped, matching how validate-skills.py measures
  description length.

Both `tokens` (the estimate) and `tokens_rounded` (the figure docs quote) are
computed from the character count directly. Deriving the second from the first
would round twice and can land 10 tokens off.

The body estimate
-----------------
README.md also quotes what one *firing* skill adds: the median `SKILL.md`, in
full — frontmatter included, since the whole file is what loads — over **every**
`SKILL.md`, bundle sub-skills included, divided by 4.

Note the asymmetry with the description budget above, which counts only
top-level skills. It is deliberate rather than an oversight: a bundle sub-skill
has no top-level `SKILL.md` and so costs nothing at session start, but its body
does load when it triggers, so it belongs in the median and not in the budget.

Chars-per-token is a crude constant, not a tokenizer. It is the documented
method, it needs no dependency, and it is stable — the numbers are a budget for
comparing groups against each other, not an invoice.
"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

# `tomllib` is stdlib from 3.11, which the PEP 723 header above requires. ruff
# does not read that header, so under its default target version it sorts the
# import here rather than into the stdlib block above; keep it here so
# `uvx ruff check` stays clean without a config file. Same reasoning as
# scripts/validate-skills.py.
import tomllib
import yaml

# This module is the leaf: consumers import it, it imports none of them. The
# constants and helpers below are shared with scripts/validate-skills.py and
# scripts/sync-docs.py, which import them from here rather than restating them —
# two hand-written parsers of one file is how scripts/parse-groups.awk drifted.
# The dependency stays one-way or the modules form an import cycle.
TREES = ("claude", "gemini")
SKILL_FILE = "SKILL.md"
GROUPS_FILE = "groups.toml"

# Descriptions load every session; 4 chars per token is the estimate README.md
# documents, and 10 is the granularity it publishes at.
CHARS_PER_TOKEN = 4
TOKEN_STEP = 10

# Descriptions above this are a standing context cost worth naming. The README
# quotes how many skills exceed it and scripts/validate-skills.py warns above it,
# so the count and the warning have to mean one thing: this is that one thing.
WARN_DESCRIPTION_LENGTH = 500

# `metadata.publisher` marking a skill as vendored from Google rather than
# written here. It is what distinguishes upstream content, which ATTRIBUTION.md
# and CODE_STANDARDS.md say to leave alone, from local content.
GOOGLE_PUBLISHER = "google"


def parse_frontmatter(content: str) -> tuple[dict | None, str | None]:
    """Parse a SKILL.md's YAML frontmatter. Returns (frontmatter, error message).

    Exactly one of the two is set. This is the repo's only frontmatter parser:
    scripts/validate-skills.py reports the error string to the author, and
    `extract_frontmatter` below throws it away. Empty frontmatter (`---\\n---`)
    is well-formed and yields `{}`, not an error.
    """
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


def extract_frontmatter(content: str) -> dict:
    """Frontmatter as facts, or {} if there is nothing usable to count.

    The tolerant face of `parse_frontmatter`: absent, unclosed, unparseable and
    non-mapping frontmatter all contribute nothing rather than raising. Judging a
    skill malformed belongs to scripts/validate-skills.py.
    """
    parsed, _error = parse_frontmatter(content)
    return parsed or {}


def frontmatter_of(skill_file: Path) -> dict:
    """Frontmatter of a SKILL.md on disk; {} if it is missing or unreadable."""
    try:
        return extract_frontmatter(skill_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return {}


def description_of(skill_file: Path) -> str:
    """A skill's description exactly as it is loaded, stripped at the ends only.

    Internal whitespace is preserved: a literal `|` block scalar's newlines and
    indentation are characters the session pays for. See the module docstring.
    """
    description = frontmatter_of(skill_file).get("description")
    return str(description).strip() if description else ""


def publisher_of(skill_file: Path) -> str | None:
    """`metadata.publisher`, or None if the skill does not declare one."""
    metadata = frontmatter_of(skill_file).get("metadata")
    return metadata.get("publisher") if isinstance(metadata, dict) else None


def find_skills(repo: Path, trees: tuple[str, ...] = TREES) -> list[Path]:
    """Every SKILL.md, including those nested inside plugin bundles."""
    found: list[Path] = []
    for tree in trees:
        root = repo / tree
        if root.is_dir():
            found.extend(root.rglob(SKILL_FILE))
    return sorted(found)


def installable_skills(repo: Path, trees: tuple[str, ...] = TREES) -> dict[str, list[str]]:
    """Top-level skill directory names per tree — exactly what install.sh offers.

    This is the count the docs mean by "skills in the tree". It differs from
    len(find_skills()) in both directions: plugin bundles are one directory but
    many SKILL.md files, and a bundle has no SKILL.md of its own.
    """
    return {
        tree: sorted(
            path.name
            for path in (repo / tree).iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )
        for tree in trees
        if (repo / tree).is_dir()
    }


def median_skill_chars(skill_files: list[Path]) -> Decimal:
    """Median full-file length of a set of SKILL.md files; 0 if there are none.

    Full file, frontmatter included — the whole thing is what a trigger loads.
    Kept exact with `Decimal` rather than `statistics.median`, whose float
    average of the two middle values can land a .5 case on the wrong side once
    it reaches `estimate_tokens`.
    """
    lengths = []
    for path in skill_files:
        try:
            lengths.append(len(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            continue  # Unreadable contributes nothing, as everywhere else here.
    lengths.sort()
    if not lengths:
        return Decimal(0)
    middle = len(lengths) // 2
    if len(lengths) % 2:
        return Decimal(lengths[middle])
    return Decimal(lengths[middle - 1] + lengths[middle]) / 2


def estimate_tokens(chars: int | Decimal, step: int = 1) -> int:
    """Estimate tokens from a character count, rounded half-up to `step`.

    Half-up rather than the builtin `round()`, which is half-to-even: at exactly
    305.0 tokens those two disagree, and the README's figure is the half-up one.
    """
    tokens = Decimal(chars) / CHARS_PER_TOKEN
    return int((tokens / step).quantize(Decimal(1), rounding=ROUND_HALF_UP)) * step


def percent_of(part: int, whole: int) -> int:
    """`part` as a whole-number percentage of `whole`, rounded half away from zero.

    Same rounding as `estimate_tokens`, and here for the same reason: rounding
    policy belongs in one place, or a share and a token count computed by two
    callers disagree on the .5 case.
    """
    if not whole:
        return 0
    share = Decimal(part) * 100 / Decimal(whole)
    return int(share.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def format_k(tokens: int) -> str:
    """Render a token count the way the README quotes tree totals: `1.8k`."""
    return f"{(Decimal(tokens) / 1000).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}k"


def load_groups(repo: Path) -> list[dict]:
    """The [[group]] entries of groups.toml, or [] if it is missing or broken.

    Well-formedness is checked by validate-skills.py's `check_groups`; entries
    too malformed to describe a group are skipped rather than reported here.
    """
    path = repo / GROUPS_FILE
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return []
    entries = data.get("group")
    if not isinstance(entries, list):
        return []
    return [
        entry
        for entry in entries
        if isinstance(entry, dict)
        and isinstance(entry.get("name"), str)
        and isinstance(entry.get("tree"), str)
        and isinstance(entry.get("skills"), list)
    ]


def group_facts(repo: Path) -> dict[tuple[str, str], dict]:
    """Per-(tree, group) membership and description budget, keyed as in groups.toml.

    `skill_count` is membership; `described_count` is how many of those members
    contribute a description. They differ by exactly the plugin bundles, which
    are directories with no top-level SKILL.md and so cost nothing at session
    start — the reason group totals run ahead of the top-level skill counts.
    """
    facts_by_group: dict[tuple[str, str], dict] = {}
    for entry in load_groups(repo):
        tree, name = entry["tree"], entry["name"]
        skills = [skill for skill in entry["skills"] if isinstance(skill, str)]
        described: list[str] = []
        undescribed: list[str] = []
        chars = 0
        for skill in skills:
            text = description_of(repo / tree / skill / SKILL_FILE)
            if text:
                described.append(skill)
                chars += len(text)
            else:
                undescribed.append(skill)
        facts_by_group[(tree, name)] = {
            "tree": tree,
            "name": name,
            "description": entry.get("description", ""),
            # Passed through unvalidated and possibly absent: this module reports
            # what the manifest says, and validate-skills.py decides whether that
            # is usable. Keeping the judgement in one place is why the generator
            # and the validator cannot disagree.
            "budget_tokens": entry.get("budget_tokens"),
            "skills": skills,
            "skill_count": len(skills),
            "described": described,
            "described_count": len(described),
            "undescribed": undescribed,
            "description_chars": chars,
            "tokens": estimate_tokens(chars),
            "tokens_rounded": estimate_tokens(chars, TOKEN_STEP),
        }
    return facts_by_group


def facts(repo: Path) -> dict:
    """Every number and membership set the docs are allowed to state.

    Keys, all derived from the working tree at `repo`:

    - `skills_total`, `skill_files_by_tree` — every SKILL.md, bundles included
    - `skills_by_tree`, `skill_names` — top-level skill directories, what
      install.sh offers and what the docs mean by "skills in the tree"
    - `described_by_tree`, `bundles` — how many of those directories carry a
      top-level SKILL.md, and which do not
    - `shared`, `claude_only`, `gemini_only` — cross-tree membership
    - `google_published` — vendored from Google, per `metadata.publisher`
    - `description_chars_by_tree`, `tokens_by_tree`, `tokens_k_by_tree` —
      standing per-session cost of a whole tree
    - `median_skill_chars_by_tree`, `median_skill_tokens_by_tree`,
      `median_skill_tokens_k_by_tree` — what one firing skill adds; see the
      module docstring for why this one counts bundle sub-skills
    - `oversized_descriptions` — skills above WARN_DESCRIPTION_LENGTH chars
    - `groups` — per-(tree, group) facts; see `group_facts`
    """
    repo = Path(repo)
    names = installable_skills(repo)
    # Keyed off `names` rather than TREES so every per-tree dict below has the
    # same keys: a caller iterating one and indexing another cannot KeyError.
    skill_files = {tree: find_skills(repo, (tree,)) for tree in names}
    every_skill = [path for paths in skill_files.values() for path in paths]

    described_by_tree: dict[str, int] = {}
    bundles: dict[str, list[str]] = {}
    description_chars: dict[str, int] = {}
    for tree, tree_names in names.items():
        top_level = {name: repo / tree / name / SKILL_FILE for name in tree_names}
        present = {name: path for name, path in top_level.items() if path.is_file()}
        described_by_tree[tree] = len(present)
        bundles[tree] = sorted(set(top_level) - set(present))
        description_chars[tree] = sum(len(description_of(path)) for path in present.values())

    median_chars = {tree: median_skill_chars(paths) for tree, paths in skill_files.items()}

    claude = set(names.get("claude", []))
    gemini = set(names.get("gemini", []))
    google = sorted(
        path.parent.name for path in every_skill if publisher_of(path) == GOOGLE_PUBLISHER
    )
    oversized = sorted(
        path.relative_to(repo).as_posix()
        for path in every_skill
        if len(description_of(path)) > WARN_DESCRIPTION_LENGTH
    )

    return {
        "skills_total": len(every_skill),
        "skill_files_by_tree": {tree: len(paths) for tree, paths in skill_files.items()},
        "skills_by_tree": {tree: len(tree_names) for tree, tree_names in names.items()},
        "skill_names": names,
        "described_by_tree": described_by_tree,
        "bundles": bundles,
        "shared": sorted(claude & gemini),
        "claude_only": sorted(claude - gemini),
        "gemini_only": sorted(gemini - claude),
        "google_published": google,
        "description_chars_by_tree": description_chars,
        "tokens_by_tree": {
            tree: estimate_tokens(chars) for tree, chars in description_chars.items()
        },
        "tokens_k_by_tree": {
            tree: format_k(estimate_tokens(chars)) for tree, chars in description_chars.items()
        },
        "median_skill_chars_by_tree": median_chars,
        "median_skill_tokens_by_tree": {
            tree: estimate_tokens(chars) for tree, chars in median_chars.items()
        },
        "median_skill_tokens_k_by_tree": {
            tree: format_k(estimate_tokens(chars)) for tree, chars in median_chars.items()
        },
        "oversized_descriptions": oversized,
        "groups": group_facts(repo),
    }


def _jsonable(data: dict) -> dict:
    """`facts()` with its one non-JSON-serialisable shape flattened.

    Only `groups` needs it: it is keyed by a `(tree, name)` tuple, which `json`
    cannot use as an object key. Rendered as `"gemini/gcp"`, matching how
    groups.toml and `install.sh --group` name a group. Decimals go through
    `default=str` below rather than losing exactness to float.
    """
    return {**data, "groups": {f"{tree}/{name}": g for (tree, name), g in data["groups"].items()}}


if __name__ == "__main__":
    # Read-only dump, so a number in a historical document can be re-derived
    # rather than trusted -- the mitigation docs/notes/documentation-drift.md
    # names for docs/plans/ files that carry no `<!-- live-counts -->` marker.
    # Nothing prints on import: this runs only under `uv run`.
    _repo = Path(__file__).resolve().parent.parent
    print(json.dumps(_jsonable(facts(_repo)), indent=2, sort_keys=True, default=str))
