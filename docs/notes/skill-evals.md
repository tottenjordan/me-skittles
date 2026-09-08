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

## 4. The result: precision is perfect, recall is bimodal

The whole `claude/workflow` group, measured the same way — group install, six-tool window, one run
per case. 147 cases, ~33 s each.

| Skill | Recall | Precision |
|---|---:|---:|
| `modern-python` | 7/8 | 8/8 |
| `receiving-code-review` | 7/8 | 8/8 |
| `finishing-a-development-branch` | 5/8 | 8/8 |
| `git-worktrees` | 5/11 | 8/8 |
| `writing-plans` | **0/8** | 8/8 |
| `executing-plans` | **0/8** | 8/8 |
| `subagent-driven-development` | **0/8** | 8/8 |
| `requesting-code-review` | **0/8** | 8/8 |
| `ralph-wiggum` | **0/8** | 8/8 |
| **Total** | **24/75** | **72/72** |

**Precision is 72/72.** Not one skill fired on a query belonging to a neighbour, across a near-miss
arm built almost entirely from other members of the same group. Eleven near-misses were answered by
the *correct* sibling, which is the group working as designed.

**Recall splits cleanly in two, and the split is not about quality.** Four skills fire; five never
do. The line between them looks like this:

- **Skills that fire** describe a *situation the user is in* — "the reviewer says X and I disagree",
  "the feature is done, what now", "set up a Python project with modern tooling". The agent does not
  already know what to do, so it reaches for something.
- **Skills that never fire** describe *how to work* — write a plan, execute a plan, delegate to
  subagents, request a review, iterate until green. The agent simply does the task. It has no felt
  gap to fill, so nothing gets loaded.

That is a finding about a whole category of skill, not about five badly written descriptions. Five
of the nine skills in this group are, in practice, **slash-command-only**: they work when invoked by
name and effectively never trigger on their own.

Worth stating plainly what this does *not* establish. It does not say those five are useless — a
skill invoked deliberately is still a skill. It does not say their descriptions are wrong. And
`--max-tools 6` means a skill loaded later in a long session was not measured.

## 5. Description wording is not why the silent skills are silent

§4 suggested a rule: firing descriptions **name a failure the agent would otherwise commit**
("*not performative agreement or blind implementation*"), silent ones state a precondition ("*use
when you have a spec…*"). Firing descriptions were also 2.3× longer, so shape and length had to be
separated. A 2×2 on `writing-plans`, four descriptions against one fixed corpus, 96 sessions:

|  | precondition | failure-mode |
|---|---:|---:|
| **short** (~90 chars) | 0/12 *(baseline)* | 0/12 |
| **long** (~300 chars) | 0/12 | 0/12 |

Precision 8/8 in every cell. **Zero unstable cases across all 96 runs** — no case fired even once.

**The hypothesis is dead.** Not weakly supported: refuted, in all four cells, with no variance to
hide behind. Rewriting a description does not make `writing-plans` trigger, and the pattern spotted
in §4 was pattern-matching on a sample of nine.

The absence of noise is itself the strongest part of the result. Elsewhere this harness flips 3 cases
in 19 between identical runs; here nothing moved at all. Whatever suppresses these skills is
deterministic, and it is not the text.

**What that redirects.** The five silent skills are silent because of *what they are* — process
instructions about how to work — not how they are written. The agent asked to plan a feature simply
plans it; there is no felt gap for a "how to plan" skill to fill. So:

- **Do not spend more effort rewriting descriptions** for `writing-plans`, `executing-plans`,
  `subagent-driven-development`, `requesting-code-review` or `ralph-wiggum`. That road is measured
  and closed.
- The remaining options are to accept them as slash-command-only (and consider
  `disable-model-invocation: true`, which frees listing budget honestly), or to look at a different
  mechanism entirely.

**Limits.** One skill, `--repeat 2`, `--max-tools 6`. A second silent skill might behave differently,
though four flat cells with zero variance make that unlikely. And this measures *auto-triggering
only* — all five work perfectly well when invoked by name.

Method detail worth keeping: the arms lived in `evals/arms.json` and were injected into the sandbox
at run time, so the repo's `SKILL.md` never changed and the group's `budget_tokens` and the README's
derived figures stayed out of the experiment. Length matching was asserted in code rather than
eyeballed, which caught a first draft whose long arms were 22 characters apart.

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
