# Skill Evals Rollout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` skill to implement this plan task-by-task.

**Goal:** Extend the eval harness from one proven skill to the whole `claude/workflow` group, add the
output-quality half, and wire both into CI at a cost the repo can actually pay.

**Architecture:** Trigger accuracy and output quality stay separate harnesses with separate corpora,
because they fail for different reasons. Trigger runs are cheap and run on every touched skill;
quality runs are expensive and run on demand. Neither ever gates a merge on a model's opinion alone.

**Tech Stack:** `claude -p --output-format stream-json` for real sessions, stdlib Python, pytest for
the scoring logic. No new dependency.

---

## Context

The pilot ([PR #16](https://github.com/tottenjordan/me-skittles/pull/16)) proved the shape on
`claude/git-worktrees`: 16 cases, 79 seconds, **8/8 precision, 6/8 recall**. It also produced the
first real finding — two lifecycle queries the description claims to cover ("listing, merging, or
cleaning up") went straight to `Bash` instead.

What exists now: `scripts/run-evals.py`, the `evals/evals.json` format, isolated per-case sandboxes,
first-tool-call early exit, and unit-tested scoring.

What does not: any second corpus, the output-quality half, CI integration, and any decision about
the pilot's two misses.

### The measurement that shapes the budget

| Mode | Per case | 16-case corpus |
|---|---|---|
| Run to completion | ~$0.51, 91 s | ~$8, 24 min |
| Stop at first tool call | ~4 s | 79 s |

Early exit is what makes this affordable. Preserve it.

### Amended 2026-09-07: sibling confusion moved ahead of the corpora

As first written, this plan built the eight corpora (then Task 2) before teaching the sandbox to
install more than one skill (then Task 4). That was the wrong order.

Those corpora are explicitly cross-skill — `writing-plans` against `executing-plans`, the two
code-review skills against each other — but with a single-skill sandbox, *"nothing fired"* and
*"the wrong sibling fired"* produce the identical observation. Writing eight corpora against a
harness that cannot distinguish them means writing eight corpora that have to be revisited, and
reporting a precision figure that quietly excludes the group's most likely failure.

The sandbox change is small and the scoring already handles it. Do it first.

---

## Task 1: Decide the pilot's two misses before writing more corpora

**Files:** `claude/git-worktrees/SKILL.md` (maybe), `docs/notes/multi-harness-skills.md`

Do this first. It sets the precedent every later corpus inherits: when a case fails, is the skill
wrong or is the case wrong?

Both misses are real queries about worktree teardown and merge-back that reached for `Bash`. Three
honest options, in order of preference:

1. **Accept them as correct behaviour.** `git worktree list` genuinely does not need a skill. Move
   the two cases to `should_not_trigger` and narrow the description's claim of "listing, merging, or
   cleaning up", so it stops promising what it does not win.
2. **Strengthen the description** for the teardown half, then re-run.
3. **Leave both as known misses**, recorded with the reason.

**Do not** quietly reword the description until the corpus goes green. That is teaching to the test,
and it converts an eval suite into a rubber stamp. Whatever is chosen, write the reasoning into the
note.

**Verify:** re-run `uv run scripts/run-evals.py claude/git-worktrees`; the result matches the
decision, and the decision is written down.

## Task 2: Sibling confusion

**Files:** `scripts/run-evals.py`

Extend the sandbox to install a *set* of skills rather than one, so a case can assert "`writing-plans`
fired, not `executing-plans`". `Case.fired` already records the name, and the scoring already treats
a different skill firing as a miss — only the sandbox needs to change.

This is the check that catches the most expensive real-world failure in a group of adjacent skills,
and the pilot cannot express it today: with one skill installed, "nothing fired" and "the wrong
sibling fired" are the same observation.

**Verify:** a case where the neighbouring skill fires is reported as a miss naming what fired.

## Task 3: Corpora for the remaining eight workflow skills

**Files:** `claude/<skill>/evals/evals.json` × 8

`writing-plans`, `executing-plans`, `subagent-driven-development`, `requesting-code-review`,
`receiving-code-review`, `finishing-a-development-branch`, `ralph-wiggum`, `modern-python`.

8–10 `should_trigger` and 8–10 `should_not_trigger` per skill. **Write the near-misses first.** They
are the part that earns the number: every entry must be genuinely adjacent, so an over-broad
description fires on it. A corpus of obvious non-matches reports a precision the skill has not
earned, which is worse than reporting nothing.

The hazard specific to this group is that **these skills overlap each other.** `writing-plans` and
`executing-plans` are adjacent by design; so are the two code-review skills. A query that should fire
one is a *near-miss for its neighbour*, so reuse queries across corpora deliberately — that
cross-checking is free signal, and Task 2 is what makes it legible rather than ambiguous.

Commit one skill per commit, with its measured result in the message. A corpus without its result is
an assertion.

**Verify:** each corpus runs; record precision and recall per skill; investigate any skill with
precision below 100% before moving on, since a false fire costs every session.

## Task 4: The output-quality harness

**Files:** Create `scripts/run-quality-evals.py`, `claude/<skill>/evals/quality.json`

The half the pilot deliberately skipped. Different question, different method:

- 3–5 realistic tasks per skill, each a job the skill claims to improve.
- Run each **twice in fresh sessions**: skill available, skill absent. A fresh session matters —
  leftover authoring context masks gaps in the written instructions.
- No early exit here. The output *is* the measurement, so runs go to completion at ~$0.5 each.
- Grade with a rubric derived from the skill's own stated rules, not from a general sense of quality.
  Pass the grader the two outputs unlabelled.

**State the limits in the script's docstring, not just here:** the grader is an LLM judging
unlabelled output, so this is a regression signal and not evidence-grade measurement. Report the
rubric and both raw outputs alongside any score, so a reader can disagree with the grade.

Budget: 9 skills × 4 tasks × 2 arms ≈ 72 runs ≈ **$35** for a full pass. This is why it is on demand.

**Verify:** run on `git-worktrees` first, where the skill's value is a concrete safety procedure and
a with/without difference should be visible. If no difference shows on a skill, that is a finding
about the skill, not a broken harness — record it either way.

## Task 5: CI, scoped to what a PR touches

**Files:** `.github/workflows/validate-skills.yml`, `CODE_STANDARDS.md`

Trigger evals only, only for skills whose files a PR changes. 117 corpora per commit is not
affordable; two or three is.

Requires an API key in CI. **If that is not available or not wanted, stop before this task** and keep evals
a local command — say so in `CODE_STANDARDS.md` rather than leaving a workflow that silently never
runs. A check that cannot run is worse than a documented manual step.

Fail the job on a **false fire**; report a **miss** without failing. Precision failures cost every
session and are hard to notice; recall failures cost one prompt and are obvious to the person who
hit them. They do not deserve the same severity.

**Verify:** open a PR touching one skill; exactly that skill's corpus runs.

## Task 6: Record what the numbers mean

**Files:** `docs/notes/skill-evals.md`, `docs/notes/README.md`

A note covering: why trigger and quality are measured separately; why runs stop at the first tool
call and what that rules out; why the isolated config dir is mandatory (11 personal skills on the
author's machine would otherwise join the listing); why precision is treated as more serious than
recall; and the standing rule that a failing case is investigated before a description is reworded.

Include the pilot's numbers as the worked example, and the cost table above, since "why not just run
everything" is the obvious question.

---

## Files that change

- **New:** `scripts/run-quality-evals.py`, `docs/notes/skill-evals.md`,
  `claude/<skill>/evals/evals.json` × 8, `claude/<skill>/evals/quality.json` × 9
- **Modified:** `scripts/run-evals.py`, `.github/workflows/validate-skills.yml`,
  `CODE_STANDARDS.md`, `docs/notes/README.md`, possibly `claude/git-worktrees/SKILL.md`

## Verification

1. Every corpus loads and runs; per-skill precision and recall recorded in the commit that adds it.
2. No skill ships with precision below 100% unaccepted — either fixed, or recorded with a reason.
3. `uv run --group dev pytest` stays green; scoring changes get tests first.
4. Cost per full trigger pass stays under two minutes and a few dollars; if it does not, early exit
   has regressed.
5. The quality harness produces both raw outputs, not just a score.

## Out of scope

- **The `gemini/` tree.** No headless Gemini CLI equivalent was verified. Do not assume `claude -p`'s
  approach ports; check before planning it.
- **The other 108 skills.** This group is the pilot for a method, not a first slice of a commitment
  to cover everything. Vendored Google skills especially: evals for content this repo does not own
  are a cost with no authority to act on the result.
- **Fleet telemetry.** No harness examined offers "did this skill fire in production, and did it
  help". The should-not-trigger corpus is the only false-activation control that exists.
- **Grading trigger accuracy with a judge.** It is directly observable from the tool call; a judge
  would add cost and doubt to a measurement that currently has neither.
