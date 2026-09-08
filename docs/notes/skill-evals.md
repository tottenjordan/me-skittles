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

## 6. The category holds outside `claude/workflow`, and phrasing does not rescue it

§5 left one theory standing: process skills — ones telling the agent *how to work* — do not
auto-trigger, whatever their description says. `test-driven-development` tests it from outside the
sample that produced it: process-shaped, 79 characters (structurally the same as `writing-plans`'
84-character precondition), but in the `testing` group.

**Run 1: 1/8 recall, 8/8 precision.** The theory generalises.

The single case that fired looked like a discovery. It was the only query asking for *guidance* —
"I'm about to add a discount calculator. **How should I start?**" — while all seven silent ones were
imperatives: *Implement*, *Add*, *Fix*, *Write*, *Build*. And it fired 2/2, stable. That suggested
the real determinant was never the description but the **user's phrasing**, which would neatly
explain why the 2×2 came back null in all four cells.

So it was tested properly: the same seven tasks, written twice, once imperative and once
guidance-shaped. Matched pairs isolate phrasing from subject matter.

**Run 2: 0/7 imperative, 0/8 guidance. Precision 8/8.**

Including the case that had fired 2/2 — this time **0/2**. Across both runs it is 2/4. It was noise,
and the elegant explanation built on it was a story told about a single sample.

That is the second time in this note a tidy pattern has come from too few observations: §4's
"firing descriptions name a failure" was pattern-matching on nine skills and died in §5. **A
hypothesis formed from one case deserves a measurement, not a paragraph** — and the harness's own
first finding (a single run is a sample) applies to a single *case* just as much as to a single run.

### Where that leaves it

Process skills do not auto-trigger. Confirmed across two groups, and unaffected by:

| Varied | Result |
|---|---|
| Description shape (precondition vs failure-naming) | no effect |
| Description length (84 vs ~300 chars) | no effect |
| Query phrasing (imperative vs guidance-seeking) | no effect |
| Group membership (`workflow` vs `testing`) | no effect |

Six skills across two groups now measure at or near zero recall with perfect precision. Nothing
tried moves the number, and each attempt was cheaper than the last because the harness was already
built.

**The actionable conclusion is unchanged and now much better supported:** these skills are
slash-command-only in practice. Stop trying to make them trigger; document that they are invoked by
name. What is *not* established is the mechanism — "the agent already knows how to do the task, so
no gap is felt" fits every observation here, and remains an explanation rather than a measurement.

## 7. A skill that fires can also be shown to help — `git-worktrees` does

Every section above measures whether a skill *loads*. This one measures whether it changes the
output. Different question, different harness (`scripts/run-quality-evals.py`), same fixture and
group for both arms — the only difference is whether the skill is installed.

Four tasks × two arms × two repeats, graded per rubric item, unlabelled. **$9.43 measured.**

| Rubric item (from the skill's own *Red flags*) | with | without |
|---|---:|---:|
| Checks the worktree directory is gitignored **before** creating it | **5/8** | **0/8** |
| Runs or plans a test-suite baseline after creating it | 7/8 | 3/8 |
| Notices the suite is not green and stops to ask | 7/8 | 3/8 |
| Asks where the worktree should live rather than assuming | 8/8 | 7/8 |
| **Total** | **27/32** | **13/32** |

**The skill roughly doubles adherence to its own rules**, and the per-item split says exactly where.

- **The gitignore check is 0/8 without the skill.** Not once, across eight runs, did a session think
  to check before creating a directory inside the repo. That is a real safety behaviour that exists
  only because the skill supplies it, and it is the single strongest result in this note.
- **The location question is 8/8 vs 7/8 — no benefit.** The model asks anyway. That rubric item is
  carrying no weight, and a "which output is better" judgement would have buried it inside a total.
  Worth noting it is also the item the grader was least stable on (80%), which fits: behaviour that
  is near-universal is exactly where a binary call gets borderline.

Cost and turns were near-identical between arms ($0.56 vs $0.62, 13.0 vs 12.8 turns), so the skill
buys adherence rather than simply making the model do more work.

### What this does not establish

- **Plan mode measures stated procedure, not executed work.** A run that says it will baseline the
  tests is scored as having done so.
- **8 samples per arm per item.** The 5/8-vs-0/8 gap is far outside noise; the 8/8-vs-7/8 one is
  meaningless in either direction.
- **An LLM graded it.** Validated first — five passes, three of four items unanimous, 4/4 on a
  planted positive and 0/4 on a planted negative, with results by majority of three — but a
  regression signal is still not evidence-grade measurement. Raw outputs are kept in the results
  JSON so a reader can disagree with any grade.

### The method note

The grader gate passed at 0% flips and then failed at 25% on the next run, same grader, same output.
Both figures came from two gradings of a four-item rubric, where the only possible answers are 0, 25,
50, 75 and 100 percent — the check was too coarse to measure what it claimed to. Sampled over five
passes instead, haiku is unanimous on three items and flips one; **Sonnet was worse** on the same
item, so the cheaper model is also the steadier one here.

That is the third time in this note a single measurement has been mistaken for a result. The
difference is that this time a gate caught it before it cost anything.

## 8. `modern-python` buys one thing, and the model already knew the rest

Same harness, same method, 16 runs, **$10.09 measured**. Rubric from the skill's own *Anti-Patterns*
table — concrete tool choices, so the grader was near-mechanical (5/5 items unanimous over five
passes, 5/5 planted positive, 0/5 planted negative: the cleanest gate of any skill so far).

| Rubric item | with | without | Δ |
|---|---:|---:|---:|
| uv for dependency management, not pip/Poetry | 7/8 | 7/8 | 0 |
| ruff for lint/format, not black/flake8 | 5/8 | 5/8 | 0 |
| **`ty` as the type checker, not mypy/pyright** | **5/8** | **0/8** | **+5** |
| `uv run` rather than activating a venv | 2/8 | 4/8 | −2 |
| `[dependency-groups]`, not optional-dependencies | 4/8 | 5/8 | −1 |
| **Total** | **23/40** | **21/40** | **+2** |

**A near-null, and far more useful than a clean win would have been.** Two items out of forty is
inside the noise this note has repeatedly warned about.

The shape is what matters:

- **uv and ruff are identical in both arms.** The base model reaches for them unprompted. Every
  character the skill spends advocating them is buying nothing.
- **`ty` is the entire measurable contribution** — 0/8 without, 5/8 with. It is new and niche, so
  the model has no default pull toward it. That is precisely the kind of thing a skill *can* teach.
- **Two items went the wrong way.** Probably noise at these sample sizes, but reported rather than
  rounded away, and worth a look if this is ever re-run.

### The generalisable lesson

**A skill's value is concentrated in whatever the base model would not do anyway.** `modern-python`
is a well-written document whose advice is, in 2026, mostly the model's own default. Restating
current best practice is dead weight; the parts that earn their place are the non-obvious choices —
`ty`, `prek`, `uv_build`, `[dependency-groups]`.

That is a testable claim about every skill in this repo, and it points at a cheaper design than
"write a thorough guide": say only what the model gets wrong on its own.

### Disposition

Not deleted, and not left alone. The evidence supports **shortening it** to the non-obvious
recommendations rather than removing it — but that is a judgement about a skill, made on 8 samples
per item, and the raw outputs are in the results JSON so the call can be re-examined. Consistent with
the standing rule: read the outputs before acting on a null.

## 9. Testing §8, and finding it necessary but not sufficient

§8 proposed that a skill's value concentrates in whatever the base model would not do anyway.
`receiving-code-review` was chosen to try to break it: its rules run *counter* to what looked like a
strong model default — never say "You're absolutely right", push back when the reviewer is wrong.

**Prediction, recorded before running: a large delta, bigger than `git-worktrees`' +14.**

**Result: +2.** The prediction was wrong, and the reason is more useful than the prediction would
have been. The without-skill arm scored **29/32 (91%)**. The model already declines to gush, already
verifies claims against the code, and already pushes back on a reviewer who is technically wrong —
8/8 on that last one, unprompted. Agreeableness was simply not the default I assumed it was.

### Delta hides two different diagnoses

Comparing all three skills by how much of the *available* room each one recovers:

| Skill | without | with | Δ | headroom | captured |
|---|---:|---:|---:|---:|---:|
| `git-worktrees` | 41% | 84% | +14 | 19 | **74%** |
| `receiving-code-review` | 91% | 97% | +2 | 3 | **67%** |
| `modern-python` | 52% | 57% | +2 | 19 | **11%** |

The two +2s are not the same thing at all:

- **`receiving-code-review` is effective but redundant.** It captures two-thirds of what is left to
  capture. There is just almost nothing left — the model is already good at this.
- **`modern-python` is ineffective.** It has *the same headroom as `git-worktrees`* — 19 items — and
  recovers a sixth as much of it. It is not redundant; it is failing to land.

Raw delta calls both of those "no benefit". They need opposite responses.

### What this does to §8

**Necessary, not sufficient.** Headroom is a ceiling on what any skill can achieve — a skill aimed at
behaviour the model already exhibits cannot help, and `receiving-code-review` confirms that. But
headroom does not deliver value on its own: `modern-python` has plenty and converts almost none.

So: **value ≈ headroom × capture**, and both terms have to be measured. That is a sharper claim than
§8's, and it comes with a warning attached.

### The warning, which is the real finding

I predicted the wrong answer, confidently, from a plausible story about model defaults. The story was
that agreeableness is trained in and hard to override. It was wrong, and only a measurement showed
it.

That is now the fourth hypothesis in this note to die on contact with data — after description shape,
query phrasing, and a "stable 2/2" that was noise. **The pattern is not that the hypotheses were
careless. It is that reasoning about what a model will do is unreliable at this granularity, full
stop.** Which parts of a skill are load-bearing cannot be argued; they have to be measured, per
skill, and the measurement is cheap enough that there is no excuse not to.

### Disposition

- **`git-worktrees`** — keep as is. Working, with room to work in.
- **`receiving-code-review`** — keep, but it is a candidate for shortening: it earns little because
  little is available, and it costs 234 characters every session.
- **`modern-python`** — the one that actually needs attention, which is the opposite of what its +2
  suggested in §8. 19 items of headroom and 11% capture means the advice is stated but not followed;
  worth reading the raw outputs to see whether it is competing with the model's own habits.

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
