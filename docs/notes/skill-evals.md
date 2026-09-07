# Measuring whether a skill actually fires

Written 2026-09-07 while extending the eval harness from one skill to the whole `claude/workflow`
group. Everything here was found by measuring, and most of it contradicts something the pilot
asserted confidently. This is a [point-in-time note](README.md).

The short version: **three separate methodological errors each produced numbers that looked like
results.** All three inflated or deflated recall, none touched precision, and none would have been
caught by reading the code.

---

## 1. A single run is not a measurement

Two runs of the harness against a byte-identical configuration disagreed on **3 of 19 cases**.

Triggering is a model decision, not a function. The pilot's headline — "8/8 precision, 6/8 recall" —
was one sample reported as a fact, and PR #16 shipped it that way.

`--repeat` now defaults to 3, the outcome is the majority of runs, and a case that fired on some runs
and not others is reported **separately** from passes and failures. Folding it into a score turns
*"we do not know"* into a number.

**The two arms are not equally noisy.** Across every comparison run so far the should-not-trigger arm
was stable and every flip landed in should-trigger. Precision is the figure to trust; treat recall as
approximate even at `--repeat 3`.

## 2. Measuring one skill in isolation overstates it by about 3×

The pilot installed only the skill under test. That is a configuration nobody runs — people install
by `--group`.

Same corpus, same description, only the installed set differing:

| Installed | Recall |
|---|---:|
| `git-worktrees` alone | 6/11 |
| The whole `claude/workflow` group (9 skills) | **2/11** |

Precision stayed 8/8 in both. Only recall moved, and it collapsed.

Worse, a single-skill sandbox **cannot express** the failure that matters most in a group of adjacent
skills: with one skill installed, *"nothing fired"* and *"the wrong sibling fired"* are the same
observation. The sandbox now installs the skill's whole `groups.toml` group. `--isolated` keeps the
old behaviour, and should be understood as the flattering number.

## 3. "First tool call" systematically undercounted recall

The pilot stopped reading at the model's first tool call, reasoning that *a skill which matches a
request matches it at the point of reading*. That was stated as a deliberate, minor limit.

It was neither. Real sessions **explore the repo with Bash first**, then decide. A `git-worktrees`
case scored `0/3` under that rule fired as soon as the window widened to six tool calls.

So every recall number produced before that fix was too low, including the ones in §2 above.

Before changing it, `--permission-mode plan` was ruled out as the cause — plan mode and default mode
both explore with Bash first.

**The cost of being right:** ~5 s per case became ~33 s. A full pass over this group at `--repeat 3`
is several hours. That is why runs are a deliberate command and not a CI step, and why
`--max-tools` exists as an explicit budget knob rather than a claim about behaviour.

---

## What the harness is actually for

Trigger accuracy, and nothing else. Whether a skill *fires* and whether its instructions are any
*good* fail for different reasons, and a single number averaging them hides both. Output quality
needs a with/without baseline and a grader; it is deliberately absent.

Reproducibility depends on `CLAUDE_CONFIG_DIR`. Without it the listing includes whatever is in
`~/.claude/skills` — eleven personal skills on the machine this was written on, several overlapping
the trees under test — and the result depends on whose laptop ran it.

## Standing rules

- **Investigate a failing case before rewording a description.** Editing wording until the corpus
  goes green is teaching to the test, and it converts an eval suite into a rubber stamp.
- **A corpus without its measured result is an assertion.** Commit them together.
- **Near-misses are the part that earns the number.** Every `should_not_trigger` entry must be
  genuinely adjacent — for this group, mostly *other members of the same group*. A corpus of obvious
  non-matches reports a precision the skill has not earned, which is worse than reporting nothing.
- **Precision failures are more serious than recall failures.** A skill that misses costs one prompt.
  A skill that fires wrongly costs every session, and is much harder to notice.

## A worked example of the first rule

`git-worktrees` missed two lifecycle queries in the pilot. The description *did* claim "listing,
merging, or cleaning up", and the skill ships `scripts/wt_cleanup.sh`, so the gap looked real and the
description was rewritten to strengthen that half.

Disentangling the variables afterwards showed the edit did nothing:

| Configuration | Recall |
|---|---:|
| Isolated, original description | 6/8 |
| Isolated, rewritten description | 6/11 |
| Whole group, rewritten description | 2/11 |

The variable that mattered was the size of the listing, not the wording. The rewrite was reverted —
it cost 53 characters of standing context on every session for no measured benefit.

The holdout cases written *before* the rewrite stayed, and they are why the comparison was possible
at all. They are not proof against overfitting, since the same person wrote both, but they were not
the cases the wording was tuned against.

## Related

- [`docs/plans/2026-09-07-skill-evals-rollout.md`](../plans/2026-09-07-skill-evals-rollout.md) — the
  remaining tasks
- [multi-harness-skills.md](multi-harness-skills.md) §10 — the documented method this implements,
  and the reason trigger and quality are measured separately
- [documentation-drift.md](documentation-drift.md) — the generate/validate/exempt split; the same
  instinct applied to prose rather than behaviour
