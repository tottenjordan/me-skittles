# Documentation drift

Why this repo both **generates** and **validates** its documented facts, when either alone looks
like enough. The short answer is that they fail in different places, and the place generation fails
is not obvious until you have shipped the bug. Read this before simplifying the machinery down to
one mechanism, or before adding a number to a live document by hand.

Related: [decisions-not-taken.md](decisions-not-taken.md) · [tooling-gotchas.md](tooling-gotchas.md)
· plan: [`docs/plans/2026-09-01-catalogue-drift-prevention.md`](../plans/2026-09-01-catalogue-drift-prevention.md)

---

## The same defect shipped three times, in three forms

| # | What shipped | Class |
|---|---|---|
| 1 | The README listed four `adk-*` skills after the skills were deleted | **existence** |
| 2 | A plan's group counts (`workflow 8`, `meta 5`, `gcp 29`, no `data` at all) survived the refactor that invalidated them | **aggregate** |
| 3 | `ml-best-practices` stayed under *Google Cloud* after moving to the `data` group | **membership** |

Each was fixed on its own terms — delete the rows, correct the counts, move the row — and each fix
left the next class untouched. That is the reason for a general mechanism rather than a fourth
one-off: **prose restates structured data, and copies drift.** The names, counts and group
memberships in `README.md` already exist in the filesystem tree and in `groups.toml`.

Incident 3 is the one worth understanding, because it was not simply wrong. The section was headed
*29 Google-published skills*, its table named 28, and `--group gcp` installed 26 — three different
true numbers presented as one. A reader following it would run `--group gcp`, not get
`ml-best-practices`, and have no way to tell which of the three numbers had lied.

## What is checkable, and what is not

The tiers exist because the classes are not equally tractable.

| Class | Checkable? | Why |
|---|---|---|
| **Existence** — a name in prose | Cheaply | Both sides are enumerable sets: names in the document, directories on disk. Set difference. |
| **Membership** — a name in the *right place* | Cheaply | Same, once section headings are mapped to groups. Only `groups.toml` can settle it, so compare against it rather than re-deriving. |
| **Derived numerics** — counts, budgets | Only when stated machine-parseably | `29 Google-published skills` names its own fact; a bare `29` does not. |
| **Free-prose claims** — "the installer is idempotent" | Not at all | Out of reach of anything short of a test. Write a test. |

The third row is the design constraint that shapes `check_stated_counts`: it binds a *specific
phrasing* to one fact and stays silent on numbers it cannot attribute. Coverage is deliberately the
lesser goal, because a checker that guesses invents findings on hand-written prose, and a check that
cries wolf gets switched off. A phrasing that stops matching warns rather than silently retiring, so
rewording cannot quietly disable the check on a number.

That guarantee is **per site, not per pattern**, and getting it wrong is easy. Four documents say
`29 Google-published skills`. The first version of the check recorded matches in a *set*, so it only
noticed the phrasing was gone once all four sites had stopped matching — rewording one of them
produced no warning at all, and ten of the nineteen checked sites sat behind such a pattern. Each
rule now declares an `expect` count and the check counts matches, so a single reworded sentence is
visible. Getting `expect` wrong is self-correcting in one direction only: too low and a retirement
goes unnoticed, too high and the warning fires until someone reconciles it.

## Generation protects only the marked region — adjacent prose drifts freely

This is the non-obvious one, and the reason the answer is *both* mechanisms.

The canonical demonstration is `embedmd`'s own README: it documents a stdin mode that was removed in
April 2026, while all 13 of its transcluded blocks stay perfectly in sync. The tool works. The
generated regions are correct. The paragraph next to them is wrong, and nothing in the tool has any
opinion about it.

That is *exactly* how incident 3 happened here. The Google Cloud **table** was right; the **heading
above it** said 29. Had the table been generated, it would still have been right, and the heading
would still have said 29 — generation would not have caught the bug that prompted this work.

So: generate the regions that are pure data, and validate the prose that surrounds them. Deleting
either tier reopens one of the three classes above.

The rule applies to this repo's own showcase, which had to be pointed out. The paragraph directly
beneath the two generated cost tables in `README.md` states three derived numbers in prose — `gcp`
is 61% of the Gemini tree, `--group agents --group workflow` costs ~860 tokens, `--all` costs ~1.8k.
All three were correct and none was checked: the design sitting in the trap it names, one paragraph
below the tables that prove the point. They are `StatedCount` rules now. The `~1.8k` one compares
the *rendered string*, not an integer, because that is the form the sentence quotes.

## The catalogue is validated, not generated

The `### Agents`, `### Testing`, `### Google Cloud and data` tables could be generated from
`groups.toml` in an afternoon. They are not, because their **"What it covers" column is hand-written
editorial** — it is the most useful content in the file, and the part a reader actually reads to
choose a skill. Generating the table would flatten it to a list of names the tree already provides.

Validation gets the same defence without the loss: `check_readme_catalogue` errors on a name that
exists nowhere, warns on a skill missing from the catalogue, and `check_catalogue_membership` errors
when a row sits under a section whose group would not install it. The voice survives; incidents 1
and 3 do not.

The general rule this repo settled on: **generate a region only when every cell in it is derived.**
Mixed regions get validated. This is why `scripts/sync-docs.py` owns two tables and nothing else,
and why the **Method** paragraph beneath them is hand-written and outside the markers.

## `docs/` is exempt, and that is the correct behaviour

`scripts/validate-skills.py` checks stated counts only in the four documents named in its
`LIVE_DOCS` constant — `README.md`, `CLAUDE.md`, `GEMINI.md`, `ATTRIBUTION.md` — plus any plan that
opts in (below). `docs/notes/` and the rest of `docs/plans/` are excluded on purpose, and
`scripts/sync-docs.py` writes into none of them.

The concrete case:
[`docs/plans/2026-09-01-installable-skill-groups.md:20`](../plans/2026-09-01-installable-skill-groups.md)
says `claude/` costs **~1.9k tokens** per session. The live figure is ~1.8k. The plan is **not
wrong** — 1.9k is what was measured when the plan was written, and it is the number that justified
the work. Syncing it to today's figure would delete the evidence and leave a plan arguing for a
decision on grounds it no longer states.

The same applies throughout [decisions-not-taken.md](decisions-not-taken.md), whose figures are
measurements-that-justified-a-decision rather than descriptions of now.

**The exemption has a cost, and it is worth naming:** incident 2 happened in a plan, so a blanket
exemption would not have caught it *in situ*. A plan is a live document for the few days it is being
executed and a historical record forever after, and no single policy fits both halves of that life.

So the plan chooses, by carrying a marker line:

```markdown
<!-- live-counts -->
```

A plan with that line is checked alongside `LIVE_DOCS`; every other plan stays exempt. The polarity
is the point. **Deleting the marker is the act of declaring the plan historical**, so a finished plan
that forgot to opt out fails with a fix that is "delete one comment line" — and the stale number
that justified the work is never rewritten.

Be honest about the reach of this. Opting in subjects a plan to `STATED_COUNTS`, and those rules
only recognise phrasings they were written for. Incident 2's own `workflow 8 / meta 5 / gcp 29`
matches none of them, so the marker alone would *not* have caught it; someone would also have had
to add a rule for that phrasing. What the marker removes is the structural exemption — the reason a
number in an executing plan could not be checked even in principle. Coverage is still opt-in, twice
over, and still deliberately partial for the reasons in "What is checkable, and what is not".

This is the same explicit opt-in shape as `CATALOGUE_SECTION_GROUPS` and `GEMINI_PURITY_ALLOWLIST`:
a file is covered because something says so, never because a walk happened to reach it. Do not add
the marker to a plan that is already complete —
[`2026-09-01-installable-skill-groups.md`](../plans/2026-09-01-installable-skill-groups.md) is
finished, and its `~1.9k` is evidence.

For an unmarked plan the mitigation stays behavioural, and it is now executable: when a number in a
plan matters for the step you are about to take, re-derive it rather than trust it.

```bash
uv run scripts/repo_facts.py        # every derived fact, as JSON, keys sorted
```

That dump is read-only and takes no arguments. It exists because this paragraph used to tell you to
re-derive from a module that printed nothing when you ran it.

## Two measurement details that cost real time

Both were recovered by reproducing all fourteen published figures, and both are load-bearing in
`scripts/repo_facts.py`. Change either and a table silently shifts by 10 or 20 tokens.

**The token estimate rounds half away from zero, not half to even.** Python's built-in `round()` is
banker's rounding. `gemini.tools` is exactly 1220 description characters — 305.0 tokens — where
`round()` gives 300 and the README correctly says 310. It is the *only* group in either tree where
the two modes disagree, which is precisely what makes it dangerous: use the builtin and every other
published figure still reproduces, so the method looks confirmed while one cell is quietly wrong.
Hence `Decimal` with `ROUND_HALF_UP`.

**Description whitespace must not be collapsed.** Normalising runs of whitespace before counting
looks like obvious hygiene. It understates `gemini.gcp` by 20 tokens and `gemini.data` by 10,
because ten Gemini skills — all Google-published — write `description:` as a YAML `|` block scalar,
whose newlines and indentation survive parsing and are loaded into context verbatim. Those
characters are really paid for, so they really are part of the cost. Only leading and trailing
whitespace is stripped, matching how the validator measures description length.
