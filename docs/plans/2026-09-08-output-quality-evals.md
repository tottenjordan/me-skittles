# Output-Quality Evals Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` skill to implement this plan task-by-task.

**Goal:** Measure whether a skill that fires actually improves the output, starting with one skill
and scaling only if the method demonstrably works.

**Architecture:** Each task runs twice in fresh sessions — the skill's group installed, and the same
group minus the skill — and each output is graded independently against a binary checklist derived
from the skill's own stated rules. The grader never sees which arm produced an output, and is itself
checked for self-consistency before any result is believed. A pilot on one skill gates all further
spend.

**Tech Stack:** `claude -p --output-format stream-json`, the existing `scripts/run-evals.py`
sandboxing, stdlib Python, pytest. No new dependency.

**Save this plan to:** `docs/plans/2026-09-08-output-quality-evals.md`

---

## Context

Trigger accuracy is measured for ten skills ([`docs/notes/skill-evals.md`](../../skittles-repo/me-skittles/docs/notes/skill-evals.md)):
six never fire, four do. What has never been measured is whether the four that fire **change the
output for the better**. A skill can load reliably and contribute nothing — stale advice, guidance
the model would have followed anyway, a procedure it silently skips.

That is the last unanswered question about whether this collection works, and a null answer is as
useful as a positive one: a skill that fires and changes nothing is pure context cost with a clear
disposition.

**Scope shrank by more than half.** Measuring output quality for a skill that never loads is
meaningless, so this covers only the four that fire: `modern-python`, `receiving-code-review`,
`finishing-a-development-branch`, `git-worktrees`.

### What already exists and must be reused

- `sandbox(tree, skill_names, ...)` in `scripts/run-evals.py:216` takes an arbitrary skill list, so
  the without-skill arm is **the group minus one entry** and needs no new code.
- `group_siblings(tree, skill)` at `:180` produces the realistic listing.
- The stream reader at `:262` shows the parsing shape, including the guard for events whose
  `message` is a string rather than an object — a real crash that cost a 20-minute run.
- The `result` event carries `result` (final text), `total_cost_usd`, `num_turns` and `duration_ms`.
  **Cost is therefore measured, not estimated** — record it.

### What this session's history demands of the design

Three tidy conclusions have already died under measurement here: the description-shape hypothesis
(null in all four cells), the query-phrasing hypothesis (null in matched pairs), and a "stable 2/2"
case that came back 0/2 on re-measurement. The design below assumes this one is wrong too until it
survives a gate.

---

## Task 1: A fixture repo the rubric can actually catch

**Files:** Create `scripts/quality_fixtures.py`

`sandbox()` builds a scratch repo containing a README and one commit. That is fine for asking *does
the skill fire*, and useless for asking *did it follow the procedure*: a rubric item like "verified
the worktree directory is gitignored" cannot discriminate in a repo with no `.gitignore` worth
checking and no tests to baseline.

Build a fixture with the conditions the rubric tests:

- a `.gitignore` that does **not** cover `.worktrees/`, so "verify it is ignored" has something to find
- a `tests/` directory with one passing and one **failing** test, so "establish a clean baseline" and
  "do not proceed past failing tests" both become live
- two or three source files, so the repo is not obviously a toy
- an ambiguous layout (both a `worktrees/` and a sibling directory would be plausible), so "do not
  assume a location" can be observed

**Verify:** `git status` in the fixture is clean, the test command fails as designed, and
`git check-ignore .worktrees` returns non-zero. A fixture that accidentally satisfies the rubric
makes both arms score full marks and the experiment reports nothing.

## Task 2: Capture the final output, not the first tool call

**Files:** Create `scripts/run-quality-evals.py`

`find_skill_call` returns as soon as a Skill call appears — correct for triggering, wrong here, where
the output *is* the measurement. Write a sibling reader that runs to completion and returns the
`result` text plus `total_cost_usd`, `num_turns` and `duration_ms`.

Keep `--permission-mode plan`: the model produces the procedure it would follow rather than mutating
the fixture, which is both safe and directly comparable between arms. **State the limit** — this
measures the stated plan, not the executed work.

Reuse `sandbox()` and `group_siblings()` by import; do not reimplement them.

**Step: write the failing test first**, in `tests/test_quality_evals.py`, using the stub-`claude`-on-PATH
pattern already established in `tests/test_evals.py`:

```python
def test_captures_final_text_and_cost(quality, fake_claude, tmp_path):
    fake_claude(result_text="the plan", cost=0.42)
    out = quality.run_once(tmp_path, tmp_path, "task")
    assert out.text == "the plan"
    assert out.cost_usd == 0.42
```

**Commit** once the reader is tested and green.

## Task 3: The rubric format, and one skill's rubric

**Files:** Create `claude/git-worktrees/evals/quality.json`

Rubric items must come from the **skill's own stated rules**, not from a general sense of quality.
`git-worktrees` supplies them directly in its *Red flags* section:

> **Never** create a project-local worktree without verifying it is ignored, skip the baseline test
> run, proceed past failing tests without asking, or assume a directory location when it is ambiguous.

That is four binary, independently checkable behaviours. Shape the file as tasks × rubric:

```json
{
  "skill": "git-worktrees",
  "tree": "claude",
  "tasks": [
    "Set up an isolated workspace so I can work on the auth refactor without disturbing my checkout."
  ],
  "rubric": [
    "Checks whether the worktree directory is gitignored before creating it",
    "Runs the test suite to establish a baseline after creating the worktree",
    "Stops and asks rather than proceeding past the failing test",
    "Asks where the worktree should live rather than assuming a location"
  ]
}
```

3–5 tasks. Each must be a job the skill claims to improve, phrased as a user would ask.

**Why a checklist and not "which output is better".** A preference judgement invites the grader to
reward verbosity and gives no diagnosis. Per-item binary answers say *where* a skill helps, and a
per-item breakdown is what makes a null result interpretable later.

## Task 4: The grader, and proof the grader works

**Files:** modify `scripts/run-quality-evals.py`; modify `tests/test_quality_evals.py`

Grade each output **independently and unlabelled**: one `claude -p` call per (output, rubric),
answering each item strictly yes/no with a one-line justification, returning JSON. The grader never
sees the other arm, never learns which arm it is reading, and never compares.

**The grader must be validated before its output is believed.** Two checks, both cheap:

1. **Self-consistency.** Grade the same output twice. Items that flip are noise, and a grader that
   disagrees with itself cannot be used to compare arms. Report the flip rate alongside the results.
2. **A planted negative.** Grade an output known to violate the rubric — the without-skill output
   generally will — and confirm the grader marks the items false. A grader that says yes to
   everything produces a tie and looks like a null result.

Use a cheaper model for grading if it passes both checks; binary rubric answers are a much easier
task than the work being graded. Record which model graded, in the results.

**Commit** with the self-consistency figure in the message.

## Task 5: Run the pilot, then STOP

**Files:** none (measurement only)

```bash
uv run scripts/run-quality-evals.py claude/git-worktrees --repeat 2 --json /tmp/q-gw.json
```

4 tasks × 2 arms × 2 repeats = 16 runs at roughly $0.50, so **about $8** — and the harness reports
actual cost, so replace this estimate with the measured figure.

Report per rubric item, per arm, not just a total. The interesting result is *which* item moved.

### The gate

`git-worktrees` is the most favourable skill in the set: its value is a concrete safety procedure
with four explicit rules. If the method cannot show a difference here, it cannot show one anywhere.

| Outcome | Meaning | Action |
|---|---|---|
| With-arm clearly ahead on rubric items the skill owns | Method works, skill earns its place | **Stop and report.** Scaling is the user's call |
| Both arms score full marks | Fixture too easy — the model does this unprompted | **Do not scale.** Fix the fixture or accept the skill is redundant here |
| Both arms score near zero | Rubric untestable from a plan-mode output, or tasks wrong | **Do not scale.** Method problem, not a skill finding |
| Grader flip rate above ~10% | Grader is noise | **Do not scale.** Nothing measured yet |

**Stop at the gate regardless of outcome** and report. The remaining ~$24 is a spend decision, not a
technical one.

## Task 6: Scale, only on an explicit go-ahead

**Files:** `claude/<skill>/evals/quality.json` × 3

`receiving-code-review`, `finishing-a-development-branch`, `modern-python`. Same shape, rubric drawn
from each skill's own stated rules — most have an equivalent of the *Red flags* section; if one does
not, its rubric is weaker and that should be said rather than invented around.

Run one skill at a time, recording each result before starting the next, so a method problem
surfaces after $8 rather than $24.

## Task 7: Record, and decide per skill

**Files:** modify `docs/notes/skill-evals.md`; modify `docs/notes/README.md`

Report per skill: per-rubric-item scores for both arms, the grader's flip rate, the model that
graded, and measured cost.

**Disposition is case by case, not a rule.** A null can mean the skill is redundant, that the task
was too easy to discriminate, or that the rubric was poorly chosen. Read the raw outputs before
concluding anything — and record the outputs alongside the score so a reader can disagree with the
grade.

State the standing limits every time a number from this harness is quoted:

- an LLM judged unlabelled output; a regression signal, not evidence-grade measurement
- plan mode measures the *stated* procedure, not executed work
- 4 tasks × 2 repeats is a small sample; a one-item difference is noise

---

## Files that change

- **New:** `scripts/run-quality-evals.py`, `scripts/quality_fixtures.py`,
  `tests/test_quality_evals.py`, `claude/git-worktrees/evals/quality.json`,
  `docs/plans/2026-09-08-output-quality-evals.md`
- **New only after the gate:** `claude/<skill>/evals/quality.json` × 3
- **Modified:** `docs/notes/skill-evals.md`, `docs/notes/README.md`

## Verification

1. `uv run --group dev pytest` green throughout; the reader and grader get tests before they get
   results, using the stub-`claude` pattern from `tests/test_evals.py`.
2. The fixture is verified to fail the rubric *before* any run — `git check-ignore .worktrees`
   non-zero, the test suite red.
3. Grader self-consistency measured and reported, not assumed.
4. Grader confirmed to mark a planted negative false.
5. Both arms differ **only** in the installed skill list: same fixture, same tasks, same repeats,
   same permission mode.
6. Cost reported from `total_cost_usd`, not estimated.
7. `uv run scripts/validate-skills.py` → 117 skills, 0 errors, and `sync-docs.py --check` passes.

## Out of scope

- **The six slash-command-only skills.** Measuring whether a skill improves output is meaningless for
  one that never loads. If they are ever invoked by name in a workflow, revisit.
- **The `gemini/` tree.** No headless Gemini CLI equivalent has been verified; do not assume
  `claude -p`'s approach ports.
- **CI integration.** At ~$0.50 a run this cannot gate a pull request. A deliberate command, like the
  trigger harness.
- **Executing rather than planning.** Letting runs mutate the fixture would measure work instead of
  intent, and makes grading far harder. Worth revisiting only if plan-mode outputs prove ungradeable.
- **Acting on a null without reading the outputs.** Deleting a skill because a rubric was weak is the
  failure mode this plan is shaped to avoid.
