# Split Over-Length Skills Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` skill to implement this plan task-by-task.

**Goal:** Bring all 13 over-length `SKILL.md` files under 500 lines using progressive disclosure, then enforce the limit in CI.

**Architecture:** Move detail out of each `SKILL.md` into sibling `references/*.md`, leaving the workflow and a link. Non-vendored skills first (Phase A), vendored Trail of Bits fuzzing skills second (Phase B), then add a line-count check to the repo-wide validator and drop `continue-on-error` from CI (Phase C).

**Tech Stack:** Markdown skills, `scripts/validate-skills.py` (PEP 723 + pyyaml, run via `uv run`), GitHub Actions.

---

## Context

The repo's own vendored Anthropic guidance states the standard twice —
`claude/writing-skills/anthropic-best-practices.md:1099`: *"Keep SKILL.md body under 500 lines for
optimal performance. If your content exceeds this, split it into separate files using the
progressive disclosure patterns"* — and repeats it as a checklist item at `:1109`.

Thirteen skills violate it. The most pointed is `claude/writing-skills/SKILL.md` at **721 lines**:
the skill that ships that guidance is its largest violator.

This is the last item deferred from the PR #2 review. The `testing-handbook-skills` bundle already
enforces 500 via its own validator (`MAX_LINES = 500`) and currently **fails 10 of 16 skills**,
which is why its CI step carries `continue-on-error: true`. The repo-wide validator has no line
check at all.

Outcome: every skill under 500 lines, the limit enforced repo-wide, and CI fully strict.

**Decisions taken** (confirmed with the user):

| Decision | Choice |
|---|---|
| Scope | All 13 — non-vendored first, vendored second |
| Enforcement | Error at 500, warning at 450 |

---

## Constraints that shape every task

1. **Both trees, identically.** All 13 exist in `claude/` and `gemini/`. Their H2 structures are
   parallel (verified: `agent-engine` and `adk` have identical heading lists; `writing-skills`
   differs by 4 lines of heading text only). Split `claude/` first, then apply the same split to
   `gemini/` — never `cp` across, which would undo the Gemini port and trip `check_gemini_purity`.
2. **Bundle skills must keep their required H2 sections.** `claude/testing-handbook-skills/scripts/validate-skills.py`
   enforces per-type sections. These stay in `SKILL.md` no matter their size:
   - `fuzzer` → When to Use, Quick Start, Writing a Harness, Related Skills
   - `technique` → When to Apply, Quick Reference, Tool-Specific Guidance, Related Skills
   - `tool` → When to Use, Quick Reference, Installation, Core Workflow
   - `domain` → Background, Quick Reference, Testing Workflow, Related Skills
3. **Every moved section leaves a link behind.** An unlinked `references/*.md` is invisible —
   exactly the orphan bug fixed in `991296e`. Verify with the orphan sweep in Verification.
4. **Divergence from upstream is expected in Phase B** and must be recorded in `ATTRIBUTION.md`.

---

## Phase A — Non-vendored skills (3 skills × 2 trees)

### Task A1: `writing-skills` (721 → target ~380)

**Files:**
- Modify: `claude/writing-skills/SKILL.md`, then `gemini/writing-skills/SKILL.md`
- Create: `claude/writing-skills/references/cso.md`, `references/testing.md`
  (and the `gemini/` equivalents)

`references/` does not exist for this skill yet — create it.

**Step 1: Move Claude Search Optimization to `references/cso.md`**

This one section is **165 lines** (`## Claude Search Optimization (CSO)`, currently lines 158-323) —
by far the largest, and reference material rather than workflow. In the Gemini tree name the file
the same but retitle the heading to match its ported terminology.

**Step 2: Move the testing cluster to `references/testing.md`**

Five adjacent sections, ~175 lines total: `## Testing All Skill Types`, `## Common Rationalizations
for Skipping Testing`, `## Bulletproofing Skills Against Rationalization`, `## Red Flags - STOP and
Start Over`, `## RED-GREEN-REFACTOR for Skills`.

**Step 3: Leave links where each cluster was**

```markdown
## Claude Search Optimization (CSO)

Write descriptions and content so the right skill surfaces at the right moment.
Full guidance: **[references/cso.md](references/cso.md)**
```

**Step 4: Verify**

```bash
wc -l claude/writing-skills/SKILL.md   # expect < 500
uv run scripts/validate-skills.py      # expect 0 errors
```

**Step 5: Repeat for `gemini/writing-skills/`, then commit**

```bash
git add claude/writing-skills gemini/writing-skills
git commit -m "writing-skills: split CSO and testing guidance into references/"
```

### Task A2: `agent-engine` (636 → target ~420)

**Files:** Modify `{claude,gemini}/agent-engine/SKILL.md`; extend the existing
`references/advanced_deployment.md`, create `references/a2a-deployment.md`.

Move `## Multi-Agent Deployment (A2A)` (89 lines) to `references/a2a-deployment.md`, and
`## Complete Deployment Example` (59) plus `## Self-Contained Deployment Pattern (cloudpickle)` (37)
into the existing `references/advanced_deployment.md`. Keep `## Deploying Agents` (99) — it is the
skill's core workflow.

**Do not move** the regional-endpoint model callout added in `5d2c8a3`; it must stay visible in
`SKILL.md`.

### Task A3: `adk` (claude 540 / gemini 566 → target ~430)

**Files:** Modify `{claude,gemini}/adk/SKILL.md`; extend the existing
`references/advanced_patterns.md`.

Move into `references/advanced_patterns.md`: `## DiscoveryEngineSearchTool vs VertexAiSearchTool`
(29), `## Config-Driven Design Pattern` (29), `## Tool Output Size — Avoid Token Overflow` (19),
`## Memory Bank (PreloadMemoryTool)` (16), `## Common Patterns` (36).

Keep `## ADK 2.x` and the model-pinning callout in `SKILL.md` — both are recent, load-bearing
guidance. Note the Gemini copy is 26 lines longer; it needs one extra section moved to clear 500.

---

## Phase B — Vendored Trail of Bits skills (10 skills × 2 trees)

Same pattern for each, driven by the type table in Constraints. Work in descending size so the
hardest lands first: `libfuzzer` (795), `aflpp` (640), `libafl` (625), `harness-writing` (614),
`coverage-analysis` (607), `semgrep` (601), `codeql` (549), `wycheproof` (533), `atheris` (515),
`constant-time-testing` (507).

**The pattern, using `libfuzzer` (type `fuzzer`) as the worked example:**

Keep in `SKILL.md`: `When to Use` (16), `Quick Start` (23), `Writing a Harness` (105),
`Related Skills` (20) — all required — plus `Installation` (42) and `Troubleshooting` (13).

Move to `references/`, each with a link left behind:
- `references/campaigns.md` ← `Running Campaigns` (109), `Corpus Management` (45), `Fuzzing Dictionary` (51)
- `references/analysis.md` ← `Coverage Analysis` (43), `Sanitizer Integration` (68)
- `references/examples.md` ← `Real-World Examples` (82), `Advanced Usage` (53), `Compilation` (81)

Result ≈ 260 lines. Group by theme rather than splitting one file per section — three reference
files beat nine.

**Per-skill commit**, so a bad split is revertable in isolation:

```bash
git add claude/testing-handbook-skills/skills/libfuzzer gemini/testing-handbook-skills/skills/libfuzzer
git commit -m "testing-handbook: split libfuzzer into references/ (795 -> ~260 lines)"
```

**After each skill**, run the bundle validator and confirm the count of failures drops by one:

```bash
cd claude/testing-handbook-skills && uv run scripts/validate-skills.py 2>&1 | tail -6
```

**Task B11: record the divergence.** Add a note to `ATTRIBUTION.md` under the Trail of Bits section
stating that these skills were reorganised for progressive disclosure — content preserved, structure
changed — so a future re-sync knows not to blindly overwrite.

---

## Phase C — Enforce

### Task C1: Add the line check to the repo-wide validator

**File:** Modify `scripts/validate-skills.py`

Add beside the existing limits at the top:

```python
MAX_SKILL_LINES = 500      # documented in writing-skills/anthropic-best-practices.md
WARN_SKILL_LINES = 450     # early signal before a skill breaks the build
```

Add a check called from `check_skill()`, following the existing `check_frontmatter_keys` shape:

```python
def check_line_count(skill_file: Path, repo: Path, content: str, report: Report) -> None:
    """Enforce the documented 500-line SKILL.md ceiling.

    Long skills defeat progressive disclosure: everything in SKILL.md is loaded
    up front, so detail that belongs in references/ costs context on every use.
    """
    n = content.count("\n") + 1
    rel = skill_file.relative_to(repo)
    if n > MAX_SKILL_LINES:
        report.error(rel, f"SKILL.md is {n} lines (limit {MAX_SKILL_LINES}) — move detail into references/")
    elif n > WARN_SKILL_LINES:
        report.warn(rel, f"SKILL.md is {n} lines, approaching the {MAX_SKILL_LINES} limit")
```

Update the module docstring, the Validation section of `CLAUDE.md`, and the Validation section of
`README.md` — all three already list the other checks.

### Task C2: Verify the check catches regressions

Prove it fires in both directions before trusting it:

```bash
uv run scripts/validate-skills.py                      # expect 0 errors
yes '' | head -200 >> claude/adk/SKILL.md              # push it over
uv run scripts/validate-skills.py | grep 'lines (limit' # expect an ERROR
git checkout claude/adk/SKILL.md
```

### Task C3: Make CI strict

**File:** Modify `.github/workflows/validate-skills.yml`

Remove `continue-on-error: true` from the "Validate testing-handbook bundle (non-blocking)" step and
rename it to drop "(non-blocking)". Delete the comment above it explaining the exemption.

Only do this once the bundle validator reports 16/16 passing.

---

## Verification

1. **No skill over the limit:**
   `find claude gemini -name SKILL.md -exec wc -l {} + | awk '$1>500 && $2!="total"'` → empty
2. **Repo-wide validator clean:** `uv run scripts/validate-skills.py` → 118 skills, 0 errors
3. **Bundle validator clean:** from `claude/testing-handbook-skills/`,
   `uv run scripts/validate-skills.py` → 16 passed, 0 failed (was 6/10)
4. **No orphaned references** — every new file must be linked, per Constraint 3:
   ```bash
   uv run python -c "
   import pathlib
   for refs in sorted(pathlib.Path('.').glob('*/**/references')):
       skill = refs.parent
       body = '\n'.join(p.read_text(errors='ignore') for p in skill.rglob('*.md') if p.parent != refs)
       for r in refs.glob('*.md'):
           if r.name not in body: print('ORPHAN', r)"
   ```
   Expect only the 5 known upstream-orphaned Google files (`bigquery-bigframes`, `gcp-dataflow`).
5. **No content lost** — total line count across each skill directory should be roughly flat before
   and after: `find claude/writing-skills -name '*.md' -exec cat {} + | wc -l`
6. **Trees still consistent:** `uv run scripts/validate-skills.py --tree gemini` → 0 errors, and no
   new Claude terminology in `gemini/`
7. **CI green** on the PR with `continue-on-error` removed

## Out of scope

- Rewriting or condensing skill *content* — this is relocation, not editing. If a section is
  genuinely redundant, note it rather than deleting it in the same pass.
- The 5 upstream-orphaned Google reference docs — unreferenced in upstream too, left alone.
- Skills between 450 and 500 lines; they will warn, which is the intended signal, not a defect.
