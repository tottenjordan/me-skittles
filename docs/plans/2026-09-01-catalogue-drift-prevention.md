# Catalogue Drift Prevention Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` skill to implement this plan task-by-task.

**Goal:** Stop documentation drifting from the skill tree by generating the facts that are pure data, validating the facts that are embedded in prose, and leaving historical records alone.

**Architecture:** Three tiers, matched to what each region actually is. Pure-data tables get generated between markers with a CI `--check`. Prose numbers and catalogue membership get validated against the tree. `docs/notes/` and `docs/plans/` are exempt by design — they are snapshots, not descriptions of now.

**Tech Stack:** Python ≥3.11 (stdlib `tomllib`, `re`), reusing `scripts/validate-skills.py`'s existing tree-walking and manifest-parsing. No new dependency.

---

## Context

The same defect has now shipped three times, in three different forms:

| # | Incident | Class | Caught today |
|---|---|---|---|
| 1 | README listed four `adk-*` skills that did not exist | **existence** | ✅ `check_readme_catalogue` |
| 2 | Plan stated group counts that a refactor invalidated | **aggregate** | ❌ |
| 3 | README listed `ml-best-practices` under Google Cloud after it moved to `data` | **membership** | ❌ |

The root cause is that **prose restates structured data**. Counts, group membership and token budgets in `README.md`, `CLAUDE.md`, `GEMINI.md` and `ATTRIBUTION.md` are hand-maintained copies of facts that already exist in the filesystem tree and `groups.toml`. Copies drift. Each incident was fixed by adding a check for that specific class, never the general one.

Research (`docs/notes/` — see Task 6) established the taxonomy this plan is built on: **existence and membership are cheaply checkable** because prose and truth are both enumerable sets; **derived numerics are checkable only when stated machine-parseably**; free prose is not checkable at all.

It also produced the finding that shapes the whole design: **generation protects only the marked region, while adjacent prose drifts freely.** The canonical demonstration is `embedmd`'s own README, which documents a stdin mode removed in April 2026 while all 13 of its transcluded blocks stay in sync. That is precisely incident 3 — the Google Cloud *table* was correct; the *heading above it* said 29.

So generation alone would not have caught the bug that prompted this plan. Both tiers are required.

---

## The three tiers, and why each region gets the treatment it does

| Region | Nature | Treatment |
|---|---|---|
| README "What each group costs" table | **pure derived data** — every cell computed from `groups.toml` + frontmatter | **Generate** |
| README catalogue tables (`### Agents`, `### Testing`, …) | **mixed** — skill names derivable, "What it covers" is hand-written editorial | **Validate membership**, never generate |
| Prose counts (`**117 skills**`, `29 Google-published`) | **derived, but embedded mid-sentence** | **Validate** |
| `docs/notes/`, `docs/plans/` | **historical snapshots** | **Exempt** |

Generating the catalogue tables would destroy the hand-written descriptions, which are the most useful thing in them. Validating them preserves the voice and still catches incident 3.

---

## Task 1: A single source of derived facts

**Files:** Create `scripts/repo_facts.py`

One module both the generator and the validator import, so they can never disagree — the same lesson as `scripts/parse-groups.awk`, where two hand-written parsers of one file had already drifted.

Expose one function returning a dict of every derivable fact:

```python
def facts(repo: Path) -> dict:
    """Every number and membership set the docs are allowed to state."""
    # skills_total, per-tree dir counts, shared count,
    # google_published, group membership + per-group description chars/tokens
```

Reuse the existing patterns in `scripts/validate-skills.py`: `tomllib` for `groups.toml`, `Path.glob` for the trees, and the same `description`-summing method the README's Method paragraph documents (character count ÷ 4).

**Verify:** every number currently in `README.md` reproduces exactly. They are all correct today, so a mismatch means the module is wrong, not the docs.

## Task 2: Generate the cost table

**Files:** Create `scripts/sync-docs.py`; modify `README.md`

Wrap the "What each group costs" table in markers and generate it:

```markdown
<!-- BEGIN GENERATED: group-costs -->
| Group | `claude/` | `gemini/` |
...
<!-- END GENERATED: group-costs -->
```

`scripts/sync-docs.py` rewrites between markers; `--check` regenerates in memory and diffs, exiting non-zero without writing. Research finding: check-only is universally implemented as *regenerate and diff*, not a bespoke linter — do the same rather than inventing something.

**Three failure modes the research flagged, each with a required guard:**

- **Humans hand-edit generated regions.** Only `cog` defends against this. Make `--check` fail on any in-region edit, and say in the marker comment that edits will be overwritten.
- **"Safe" modes are not always safe.** `markdown-magic --dry` mutated the file and exited 0. `--check` must provably not write — verify by checksumming the file before and after.
- **Generators rot.** Keep it in-repo, stdlib-only, under ~80 lines. No external tool.

Leave the **Method** paragraph beneath the table hand-written and outside the markers. It explains *how* the numbers are derived, which is editorial, and Task 3 covers the numbers inside it.

## Task 3: Validate prose numbers

**Files:** Modify `scripts/validate-skills.py`

Add `check_stated_counts(repo, report)`. Match number-plus-noun patterns in the four **live** docs only — `README.md`, `CLAUDE.md`, `GEMINI.md`, `ATTRIBUTION.md` — and compare against `repo_facts.facts()`.

Fourteen such numbers exist today (all currently correct):

```
README.md:5    **117 skills**       README.md:98   29 Google-published
README.md:99   26 of them           README.md:227  26 skills
GEMINI.md:14   **57 skills**        CLAUDE.md:57   29 Google-published
ATTRIBUTION.md:10  29 skills        ...
```

**Design constraint that matters:** a number is only checkable if it is unambiguous about *which* fact it states. `29 Google-published` is; a bare `29` is not. Rather than guessing, error on a **recognised phrase whose number is wrong**, and stay silent on numbers you cannot attribute. A validator that guesses will produce false positives, and a check that cries wolf gets ignored — the same reasoning that made `check_install.py` exempt from the dependency check.

Report the stated value, the actual value, and the file:line.

## Task 4: Validate catalogue membership

**Files:** Modify `scripts/validate-skills.py`

Extend `check_readme_catalogue`, which already validates *existence*, to also validate *membership* — the gap that let incident 3 through.

For each `###` subsection of `## Skill catalogue` that corresponds to a group in `groups.toml`, error when a skill listed there belongs to a different group. Map section headings to group names explicitly (`### Google Cloud and data` → `gcp`), because the headings are editorial and will not always match a group name; skip any section with no mapping rather than guessing.

**This is the check that would have caught incident 3**, and it must be tested against exactly that case: put `ml-best-practices` back under Google Cloud and confirm it errors.

## Task 5: Exempt historical documents, explicitly

**Files:** Modify `scripts/validate-skills.py`; modify `docs/notes/README.md`

`docs/notes/` and `docs/plans/` state numbers that were true when written and **must never be synced**. `decisions-not-taken.md` says `gcp-diagram` is 160 files because that measurement justified a decision; a plan says "10 of 16 skills fail" because that state motivated the work. Auto-updating either destroys the evidence.

Make the exemption **explicit and named**, not an accident of which paths the checks happen to walk. Define the live set as a constant with a comment saying why the others are excluded, in the style of `GEMINI_PURITY_ALLOWLIST`. Add a line to `docs/notes/README.md` stating that notes are point-in-time and are deliberately not validated.

This is the one place the research's recommendation does not transfer: `kubernetes/community` and `awesome-selfhosted` generate current-state catalogues and have no historical-record documents. Adopting their pattern wholesale here would be actively harmful.

## Task 6: Wire into CI, and record the reasoning

**Files:** Modify `.github/workflows/validate-skills.yml`; create `docs/notes/documentation-drift.md`; modify `docs/notes/README.md`; modify `CODE_STANDARDS.md`

Add `uv run scripts/sync-docs.py --check` as a workflow step. The validator changes need no new step — they are already invoked.

Write `docs/notes/documentation-drift.md` covering: the three incidents and their classes; the taxonomy of what validation can and cannot catch; why the catalogue tables are validated rather than generated (editorial voice); why `docs/` is exempt; and the `embedmd` finding, because "generation protects only the marked region" is the non-obvious insight that a future maintainer would otherwise rediscover by shipping incident 4.

Add one line to `CODE_STANDARDS.md`: derived facts in live docs are generated or validated, never hand-maintained.

---

## Files that change

- **New:** `scripts/repo_facts.py`, `scripts/sync-docs.py`, `docs/notes/documentation-drift.md`
- **Modified:** `scripts/validate-skills.py`, `README.md`, `.github/workflows/validate-skills.yml`, `CODE_STANDARDS.md`, `docs/notes/README.md`

## Verification

1. **No regression:** `uv run scripts/validate-skills.py` → 117 skills, 0 errors; warnings not above 20.
2. **Each new check fires** — test in a `copytree` sandbox, never the real repo:
   - change `**117 skills**` to `**118 skills**` → error naming stated vs actual
   - move `ml-best-practices` back under Google Cloud in the README → membership error
   - hand-edit inside the generated markers → `sync-docs.py --check` exits non-zero
   - delete a skill directory → both the count check and the existence check fire
3. **`--check` provably does not write:** checksum `README.md` before and after a failing `--check`; they must match. The `markdown-magic --dry` failure is the reason this is a required step, not a nicety.
4. **Round-trip is stable:** `sync-docs.py` then `sync-docs.py --check` passes; running it twice produces no diff.
5. **Historical docs untouched:** mutate a count in `docs/notes/decisions-not-taken.md` and in a plan → validator stays silent, `sync-docs.py` does not rewrite them.
6. **Generator and validator agree:** assert `repo_facts.facts()` is the only source of numbers in both, so they cannot diverge the way the awk parser and validator did.
7. **CI green**, with the new step demonstrably failing on a deliberately stale README before it passes on a fresh one.

## Out of scope

- Generating the catalogue tables. The "What it covers" column is hand-written and is the most useful content in them; generation would flatten it. Research finding #7 — large projects preserve editorial voice with reserved hand-written regions rather than generating everything.
- Any change to `docs/notes/` or `docs/plans/` content. They are snapshots.
- Adopting `cog`, `markdown-magic`, `embedme` or `embedmd`. Literal transcluders cannot compute counts at all; the code-executing ones are a dependency this repo does not need for ~80 lines of stdlib Python. `embedme` has had no npm release in ~4 years, which is the rot risk in concrete form.
- Free-prose semantic claims ("the installer is idempotent"). Not machine-checkable; out of reach of any tier here.
