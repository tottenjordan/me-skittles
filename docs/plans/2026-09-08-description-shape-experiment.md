# Description Shape Experiment Implementation Plan

> **Completed 2026-09-08. Result: null in all four cells.** Every arm scored 0/12 recall, 8/8
> precision, zero unstable cases across 96 sessions. Neither shape nor length nor their combination
> affects whether `writing-plans` fires. Task 6 (adopt the winner) was correctly not executed —
> there was no winner. Findings in [`docs/notes/skill-evals.md`](../notes/skill-evals.md) §5.
> Kept as written, including the pre-registered predictions, because a plan edited after the fact
> to match its outcome is not evidence of anything.

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` skill to implement this plan task-by-task.

**Goal:** Determine whether a skill's *description shape* — naming a failure the agent would
otherwise commit, versus stating a precondition — causes auto-triggering, independently of
description length.

**Architecture:** A 2×2 within-subject experiment on one skill (`claude/writing-plans`, currently
0/8). Four description variants are held in a new `evals/arms.json` and injected into the eval
sandbox at run time, so the repo's own `SKILL.md` is never modified during measurement. The corpus,
the installed skill group, the working directory and the run count are identical across arms; the
description is the only variable.

**Tech Stack:** The existing `scripts/run-evals.py` harness, `claude -p --output-format stream-json`,
stdlib Python, pytest. No new dependency.

**Save this plan to:** `docs/plans/2026-09-08-description-shape-experiment.md`

---

## Context

PR #18 measured all nine `claude/workflow` skills: **precision 72/72, recall 24/75.** Recall split
cleanly rather than spreading out — four skills fire, five never do:

| Fires | Never fires |
|---|---|
| `modern-python` 7/8, `receiving-code-review` 7/8, `finishing-a-development-branch` 5/8, `git-worktrees` 5/11 | `writing-plans`, `executing-plans`, `subagent-driven-development`, `requesting-code-review`, `ralph-wiggum` — all 0/8 |

Reading the descriptions side by side suggests why. Every firing description **names what goes wrong
without the skill**; no silent one does:

- `receiving-code-review` (7/8): "…requires technical rigor and verification, **not performative
  agreement or blind implementation**"
- `writing-plans` (0/8): "Use when you have a spec or requirements for a multi-step task, before
  touching code" — a precondition, and nothing about what the agent would otherwise get wrong

If that holds, it is an authoring rule for every future skill in this repo, which is worth far more
than fixing one description.

**The confound that makes this an experiment rather than an edit.** Firing descriptions average
**303 characters**; silent ones average **131**. Length is a complete alternative explanation, and
the last time a description was rewritten here on an unverified theory
([`docs/notes/skill-evals.md`](../../skittles-repo/me-skittles/docs/notes/skill-evals.md)), the
change turned out to do nothing — the real variable was listing size. Shape and length must be
varied separately.

**Pre-registered predictions.** Write these down before running anything:

|  | precondition-shaped | failure-mode-shaped |
|---|---|---|
| **short** (~90 chars) | BASELINE (expect 0/8) | **Arm A** |
| **long** (~300 chars) | **Arm B** | **Arm C** |

- Shape causes it → **A and C** fire, B does not
- Length causes it → **B and C** fire, A does not
- Both required → only **C** fires
- Neither → nothing fires; the cause is elsewhere and the hypothesis is dead

Any of those four is a publishable result. Only "we rewrote it and it got better" is not.

---

## Task 1: Holdout cases, written before any rewrite

**Files:** Modify `claude/writing-plans/evals/evals.json`

The existing 8 trigger cases were written against the current description. If a rewrite is tuned
against them, a green result means nothing. Add 4 more trigger queries now, and commit them in their
own commit so the ordering is verifiable in git rather than asserted — the same guard used for
`git-worktrees` in PR #18.

**Step 1:** Append four trigger queries phrased the way a user actually asks, not the way the
description reads. Suggested:

```
"We need to add multi-tenant support. Where do I even start?"
"This ticket is huge and I don't know what order to do things in."
"Can you scope out the work for the notifications rewrite?"
"I keep half-finishing this refactor. Help me get organised before I write more code."
```

**Step 2:** Add a note to the file's `notes` array recording that these are holdout cases for the
shape experiment and were committed before any arm existed.

**Step 3:** Verify the corpus still loads.

Run: `uv run --group dev pytest tests/test_evals.py -q`
Expected: PASS

**Step 4:** Commit.

```bash
git add claude/writing-plans/evals/evals.json
git commit -m "Add holdout trigger cases before the shape experiment"
```

## Task 2: Teach the harness to swap a description per arm

**Files:** Create `claude/writing-plans/evals/arms.json`; modify `scripts/run-evals.py`;
modify `tests/test_evals.py`

The repo's `SKILL.md` must not change during measurement: editing it would move the
`claude/workflow` group's `budget_tokens` and break the README's stated `~860` figure, adding two
irrelevant variables. The sandbox already lives in `$TMPDIR`, so the override belongs there.

**Step 1: Write the failing test** in `tests/test_evals.py`:

```python
def test_arm_overrides_the_description_in_the_sandbox(evals, tmp_path):
    """The repo's SKILL.md must be untouched; only the sandbox copy changes."""
    config, _ = evals.sandbox("claude", ["writing-plans"], arm="probe text here")
    text = (config / "skills" / "writing-plans" / "SKILL.md").read_text()
    assert "probe text here" in text
    original = (evals.REPO / "claude/writing-plans/SKILL.md").read_text()
    assert "probe text here" not in original
```

**Step 2: Run it to confirm it fails**

Run: `uv run --group dev pytest tests/test_evals.py -k arm_overrides -q`
Expected: FAIL — `sandbox() got an unexpected keyword argument 'arm'`

**Step 3: Implement.** In `scripts/run-evals.py`, extend `sandbox()` with an optional
`arm: str | None`. When set, the skill under test is **copied** rather than symlinked and its
frontmatter `description:` line is replaced. Every sibling stays a symlink. Add `--arm NAME` to the
CLI, reading `evals/arms.json`, and print the arm name and description length in the run header so a
result is never separated from the condition that produced it.

**Step 4: Run the test**

Run: `uv run --group dev pytest tests/test_evals.py -k arm -q`
Expected: PASS

**Step 5:** Write `claude/writing-plans/evals/arms.json` with all four variants. Keep A within ±10
characters of the baseline and B within ±20 of C, or the 2×2 is not a 2×2. Sketches:

- `baseline` — current text, verbatim
- `A-short-failure` (~90 c) — "Use before writing code for a multi-step task, so the work is
  sequenced rather than discovered halfway through."
- `B-long-precondition` (~300 c) — the current precondition, expanded with scope and coverage detail
  but naming **no** failure
- `C-long-failure` (~300 c) — names the failures: starting to code before the order is known,
  discovering dependencies mid-implementation, no checkpoints to review against

**Step 6: Commit.**

```bash
git add scripts/run-evals.py tests/test_evals.py claude/writing-plans/evals/arms.json
git commit -m "Support per-arm description overrides in the eval sandbox"
```

## Task 3: Re-measure the baseline at the experiment's run count

**Files:** none (measurement only)

The published 0/8 is `--repeat 1`, and a single run is a sample — that is the first finding in
[`docs/notes/skill-evals.md`](../../skittles-repo/me-skittles/docs/notes/skill-evals.md). Comparing
arms at `--repeat 2` against a baseline at `--repeat 1` would compare two different measurements.

Run: `uv run scripts/run-evals.py claude/writing-plans --arm baseline --repeat 2 --json /tmp/arm-baseline.json`
Expected: recall at or near 0/12, precision 8/8, ~18 minutes.

**If the baseline is not ~0, stop.** The premise has evaporated and the arms measure nothing.

## Task 4: Run the three arms

**Files:** none (measurement only)

One command per arm, identical but for `--arm`:

```bash
for arm in A-short-failure B-long-precondition C-long-failure; do
  uv run scripts/run-evals.py claude/writing-plans --arm "$arm" --repeat 2 \
    --json "/tmp/arm-$arm.json"
done
```

Roughly 70 minutes total, unattended. Run them in the background and poll; do not interleave with
other `claude -p` work, which would compete for the same rate limit.

**Watch precision, not just recall.** A longer or vaguer description can buy recall by firing on
everything. An arm that gains recall and loses precision has failed, because a false fire costs every
session while a miss costs one prompt.

## Task 5: Read the result against the pre-registered predictions

**Files:** Modify `docs/notes/skill-evals.md`; modify `docs/notes/README.md`

Tabulate all four conditions — recall, precision, and unstable-case count — and state which
prediction the data matches. Record the outcome **even if it is "neither"**, which is the most likely
single result and the most useful one to have written down, because it stops the next person
re-running this.

Two honest limits to state:

- One skill. A rule for the repo needs the winning transform replicated on a second silent skill
  (`requesting-code-review` is the natural candidate); until then this is a hypothesis with one data
  point.
- `--repeat 2` on 12 trigger cases is a small sample. A 1-case difference between arms is noise; only
  treat a difference of 3 or more as real.

**Commit** the note before touching any skill, so the finding is recorded independently of whether
anything is adopted.

## Task 6: Adopt the winner, if there is one

**Files:** `claude/writing-plans/SKILL.md`; possibly `gemini/writing-plans/SKILL.md`,
`groups.toml`, `README.md`, `CODE_STANDARDS.md`, `claude/writing-skills/SKILL.md`

Only if an arm beat the baseline by 3+ cases with precision intact.

**Step 1:** Apply the winning description to `claude/writing-plans/SKILL.md`.

**Step 2:** Re-run the validator. A longer description raises the `claude/workflow` group total
(currently 469 tokens against a declared 550) and will break the README's stated `~860` figure for
`--group agents --group workflow`. Both are *supposed* to fail — that is the drift machinery working.
Update the README figure, and raise `budget_tokens` in `groups.toml` only if genuinely needed.

Run: `uv run scripts/validate-skills.py`
Expected: 117 skills, 0 errors, 20 warnings after the figures are corrected.

**Step 3:** Port to `gemini/writing-plans/SKILL.md`. `check_cross_tree_parity` will fail if the trees
diverge and the file is not in `CROSS_TREE_DIVERGENCE` — `writing-plans/SKILL.md` already is, but the
port should still be made rather than relying on the exemption.

**Step 4:** Write the authoring rule where skill authors will meet it — a short section in
`claude/writing-skills/SKILL.md` (and its Gemini port) saying that a description should name the
failure the agent would otherwise commit, with the measured before/after as the evidence.

**Step 5: Verify and commit.**

```bash
uv run --group dev pytest && uvx ruff check scripts/ tests/ && uv run scripts/sync-docs.py --check
git add -A && git commit -m "Adopt the measured description shape for writing-plans"
```

---

## Files that change

- **New:** `claude/writing-plans/evals/arms.json`,
  `docs/plans/2026-09-08-description-shape-experiment.md`
- **Modified:** `scripts/run-evals.py`, `tests/test_evals.py`,
  `claude/writing-plans/evals/evals.json`, `docs/notes/skill-evals.md`, `docs/notes/README.md`
- **Modified only if an arm wins:** `claude/writing-plans/SKILL.md`, `gemini/writing-plans/SKILL.md`,
  `claude/writing-skills/SKILL.md` + Gemini port, `README.md`, `groups.toml`, `CODE_STANDARDS.md`

## Verification

1. `uv run --group dev pytest` green throughout; the arm-override test asserts the repo's `SKILL.md`
   is untouched.
2. Baseline reproduces at ~0 recall before any arm is trusted.
3. All four conditions differ **only** in the description: same corpus, same installed group, same
   `--repeat`, same `--max-tools`.
4. Arm A is within ±10 characters of baseline; B within ±20 of C. Verify with `wc -c` before running,
   because an unmatched length silently turns the 2×2 back into the confounded single-arm test.
5. Precision reported for every arm, not only recall.
6. `uv run scripts/validate-skills.py` → 117 skills, 0 errors, and `sync-docs.py --check` passes at
   the end, whether or not a winner is adopted.

## Out of scope

- **The other four silent skills.** Fix the method first; a rule proven on one skill and replicated
  on one more is enough to act on.
- **Output-quality evals.** Different question, different harness, ~$35 a pass.
- **`--repeat 3` or higher.** Would firm up the numbers and roughly doubles the runtime; only worth it
  if an arm lands within 1–2 cases of the baseline and the call is genuinely close.
- **Rewriting descriptions to pass the corpus.** If an arm fails, that is the result. The standing
  rule in `docs/notes/skill-evals.md` is to investigate a failing case, not to reword until green.
