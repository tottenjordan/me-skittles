# Managing skills across teams, providers, and harnesses

Researched 2026-09-01 against primary sources — vendor docs, the Agent Skills spec and its reference
validator, harness source code, and the Skill Registry documentation. Numbers measured against this
repo on that date; this file is a [point-in-time note](README.md) and is not validated.

The short version: **the portable layer is smaller than it looks, and everything above it — triggering,
permissions, precedence, packaging — fragments.** Design for a thin shared core and treat the rest as
port-layer content policed by CI.

---

## 1. The portable contract is exactly six frontmatter fields

The [Agent Skills spec](https://agentskills.io/specification) defines `name`, `description`, `license`,
`compatibility`, `metadata`, and `allowed-tools`. The reference validator closes the set in code —
`ALLOWED_FIELDS`, with extra top-level keys a hard **error**, not a warning.

Claude Code documents **20** fields and says plainly that it "extends the standard". The failure mode is
asymmetric, and that asymmetry is the whole practical point:

| Path | Non-spec key |
|---|---|
| Claude Code, reading a local skill | Accepted, works |
| `package_skill.py`, the Skills API, claude.ai upload | **Hard error:** `Unexpected key(s) in SKILL.md frontmatter` |

Divergence runs both directions. Claude Code marks `name` **not required** (defaults to the directory
name) and `description` merely *recommended* — so a skill Claude Code is perfectly happy with can fail
spec validation on required fields.

**Rule:** the shared core carries only the six spec fields. Anything else goes under the spec's sanctioned
extension point, the `metadata` string map. Reject non-spec top-level keys in CI outright.

> The spec is silent on how a harness should treat unknown keys. "A conformant harness ignores them" is
> inference, not spec text — don't rely on it.

## 2. `allowed-tools` is not a security boundary

It is the only field carrying an **Experimental** marker, and the spec warns support "may vary between
agent implementations". Even in Claude Code it is a *pre-approval convenience*: the grant applies during
the invoking turn, clears on your next message, and "does not restrict which tools are available: every
tool remains callable."

The field that actually restricts — `disallowed-tools` — is **non-spec**, so it is rejected on every
packaging path. Cursor documents no `allowed-tools` support at all.

**Rule:** skills are advisory content, never a sandbox. Enforce real boundaries with harness-native
permission settings and hooks.

## 3. Progressive disclosure, quantified

Spec: metadata ~100 tokens loaded at startup **for every installed skill**; body <5,000 tokens loaded on
activation; resources on demand. "Keep your main SKILL.md under 500 lines."

Gemini CLI implements this identically — it "injects the name and description of all enabled skills into
the system prompt" at session start, and adds the body on activation.

Two honest qualifications worth recording, because this repo enforces stricter numbers:

- `~100 tokens` is **nominal, not a cap**. A spec-legal description may run to 1,024 characters.
- `<5,000 tokens` and `500 lines` are stated as recommendations "for optimal performance", with **no
  published measurement** behind them.

So `MAX_SKILL_LINES = 500` and the <500-character description warning are *documented convention plus
local policy*, which is defensible — but the rationale comments should say that rather than implying an
empirical threshold.

## 4. The listing budget is the real argument for `--group`

This is the highest-value operational finding. Claude Code, verbatim:

> The listing always contains every skill name, but if you have many skills, Claude Code shortens
> descriptions to fit the listing's character budget… The budget scales at 1% of the model's context
> window. When the listing overflows, Claude Code **drops descriptions starting with the skills you
> invoke least**, so the skills you use most keep their full text.

Per-entry, `description` + `when_to_use` is truncated at **1,536 characters**.

The failure mode is nasty: an over-large tree doesn't error, it *silently strips the trigger keywords from
your rarest skills* — precisely the ones whose descriptions you most need intact, because you won't
remember to invoke them by name.

Levers, all configurable:

| Lever | Effect |
|---|---|
| `skillListingBudgetFraction` | Raise the 1% (e.g. `0.02`) |
| `SLASH_COMMAND_TOOL_CHAR_BUDGET` | Fixed character budget instead |
| `skillListingMaxDescChars` | Move the 1,536 cap |
| `skillOverrides: "name-only"` | List a low-priority skill without its description |

Detection is possible but not surfaced by default: `/doctor` estimates the listing cost and names the
biggest contributors, `/context` has a Skills row, and overflow writes a warning **only to the `--debug`
log**.

**Rules for this repo:** `--group` is the default install path and `--all` is an anti-pattern for daily
driving. `repo_facts.py` already computes per-group description totals — publish a per-group ceiling and
fail CI on it, since the aggregate listing, not the individual description, is the binding constraint.
Quote the *ratio*, never a computed character count: the docs mix characters and "1% of the context
window".

## 5. Scope precedence differs per harness — and inverts

The trap is assuming one mental model transfers. It does not:

| Harness | Precedence | Direction |
|---|---|---|
| Claude Code (skills) | enterprise > personal > project | **Broader scope wins** |
| Cursor (rules) | Team > Project > User | Earlier source wins |
| Codex (AGENTS.md) | root-down concatenation | **Deeper wins**, by position |
| Gemini CLI | `.agents/skills/` > `.gemini/skills/` *within* a tier | Alias outranks native |

Claude Code's is the surprising one: a `deploy` skill in both `~/.claude/skills/` and the project's
`.claude/skills/` resolves to the **personal** one.

## 6. Symlinks: blessed here, banned there

Claude Code **officially supports** symlinked skill directories in the enterprise, personal, and project
tiers, and deduplicates a target reachable from several locations. Plugin skills are the exception — a
plugin symlink pointing outside the marketplace is "skipped for security".

So `scripts/install.sh` is doing a vendor-documented thing, and the bundle carve-out (install via
marketplace, never symlink) already sidesteps the strict path. Two residual hazards:

- A **stale personal symlink silently shadows** a corrected project skill. Worth a stale-link check.
- Gemini's `.agents/skills/` alias outranks `~/.gemini/skills/`, which is what the installer targets.
  Anything that ever populates `~/.agents/skills` shadows the terminology-pure port **with no warning**.

Note the opposite rule downstream: the Skill Registry **rejects a package containing symbolic links**.
Different surface — install-time vs package-time — so this is not a conflict, and nobody should "fix" it.

## 7. Where the other harnesses actually break

**Codex** is not a skill system at all — it's a positional instruction chain. Fixed filename allowlist
(`AGENTS.override.md`, `AGENTS.md`, then configured fallbacks, **default empty**), at most one file per
directory, concatenated root-down, hard-capped at `project_doc_max_bytes` (32 KiB) with overflow truncated
and then dropped. `CLAUDE.md` and `GEMINI.md` are **invisible to it by default**. Truncation warns to the
tracing log only — no user-facing error.

**Cursor** is the sharpest incompatibility. `.cursor/rules` accepts only `.mdc`; a plain `.md` there is
ignored outright. Org-level Team Rules are **dashboard entities, not version-controlled files** — org
governance simply cannot be authored in the same format as repo rules.

No primary sourcing was obtained for **Antigravity, Windsurf, or Amp**. A claim that Copilot reads
`CLAUDE.md`/`GEMINI.md` as first-class was **refuted**. Treat all four as unknown, not as supported.

**Convergence is real but shallow, and on two different things:** the SKILL.md folder convention
(structured, genuinely multi-vendor) and AGENTS.md (multi-vendor, but ungoverned prose with no
description, globs, or trigger metadata). There is no portable layer for triggering, permissions, or
packaging. Keep portable substance in the SKILL.md body; treat AGENTS.md as a thin router well under
Codex's 32 KiB budget.

## 8. How thin is this repo's port, actually?

Measured 2026-09-01, normalising provider names (`claude`→`AGENT`, `gemini`→`AGENT`) across all files:

| | Count |
|---|---|
| Skills present in both trees | 22 |
| **Byte-identical in every file** after normalisation | **11** |
| Identical `SKILL.md`, differing file list (plugin manifest, `node_modules`) | 2 |
| Genuinely divergent | 9 |

Total real divergence is `+158/-179` lines, concentrated in three skills: `adk` (+76/-50),
`writing-skills` (+23/-65), `paperbanana` (+20/-20). The remaining six differ by 3–12 lines each.

**Half the shared surface is mechanical duplication maintained by hand** — the same root cause as the
[documentation drift](documentation-drift.md) already fixed one layer up: a copy of structured data kept
in sync by diligence.

The honest counter-argument, and the reason this note stops short of recommending generation: the
`CLAUDE_TERMS` check is deliberately broad (`claude|anthropic`) because the expensive leaks were *prose*,
not paths. A generator would need a translation table for prose, and **no vendor publishes one**. So
hand-porting plus CI purity checking is a defensible choice rather than a workaround — but the 11
fully-identical skills are the subset where that argument does not apply, and they are the candidates for
mechanical derivation.

## 9. Gemini Enterprise Skill Registry

**Preview**, under Pre-GA terms. Documented at
[docs.cloud.google.com/gemini-enterprise-agent-platform/build/skill-registry](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/skill-registry).
(The broad web research found no primary source under this name; these facts come from the vendor docs
and the [official notebook](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/skill-registry/intro_skill_registry.ipynb) directly.)

**Model.** A mutable `Skill` (display name, labels, timestamps, default-revision pointer) over
**immutable revisions** — `projects/*/locations/*/skills/*/revisions/*`. Every update mints a revision.
That is real versioning and pinning, which git history alone does not give you.

**Discovery is semantic search over `description`** — `client.skills.retrieve(query=…, top_k=…)`, and
"agents use this exact retrieval mechanism at runtime". This is the second, independent justification for
the description discipline already enforced here: a vague description doesn't merely waste context, it
makes the skill **unfindable**. Same rule, unrelated reason.

**Constraints that bite this repo:**

| Rule | Status here |
|---|---|
| SKILL_ID **must not start with `gcp-`** (reserved for built-ins) | ❌ **11 directories** — 1 in `claude/`, 10 in `gemini/` |
| Package must not contain symlinks | ✅ zero |
| SKILL_ID 1–63 chars, `^[a-z][a-z0-9-]*[a-z0-9]$` | ✅ all 117 |
| zip ≤10 MB, unzipped ≤500 MB, ≤10,000 items, depth ≤8 | ✅ nothing close |
| `description` ≤1,024 chars | ✅ local <500 limit is stricter |

The sharp edge: the official notebook's batch-ingest helper does `skill_id = f"{name}-{timestamp}"`. Run
the vendor's own reference pattern against this repo and **it fails on all 11** — the documented way to
bulk-load a GitHub skills repo breaks on the naming convention Google's own published skills use. Any
registry push needs a SKILL_ID mapping layer, not the directory name.

Other operational facts: deleted IDs are **permanently reserved** (reusable after 24h only in the sense
that the ID is gone for good); create/update/delete are long-running operations; IAM is
`roles/aiplatform.viewer|user` plus `roles/serviceusage.serviceUsageConsumer`.

## 10. Testing non-deterministic artefacts

There is a documented method, and it is the one this repo already follows: measure **trigger accuracy**
and **output quality** separately, via with-skill/without-skill baseline runs **in fresh sessions**
("leftover context from authoring the skill will mask gaps in the written instructions"). The
`skill-creator` plugin automates it — `evals/evals.json`, per-case paired subagents, pass/fail grading, a
with/without benchmark of pass rate + tokens + time, and description tuning from 8–10 should-trigger and
8–10 should-not-trigger near-miss queries.

Two qualifications: the "blind A/B" is an LLM judge on unlabelled outputs, so treat it as a regression
signal, not evidence-grade measurement. And the should-not-trigger corpus is the **only** documented
control for false activation — no vendor doc verified here offers fleet-level "did this skill fire, and
did it help" telemetry.

Running ~117 evals per commit is not affordable. Per-group suites, run on skills a PR touches, is the fit.

## 11. Governance is the weakest-evidenced area

What is primary-sourced: Gemini extension pinning (`--ref`, `--auto-update`, `--pre-release`, `migratedTo`
for a moved repo), Claude Code plugin marketplaces with `plugin-name:skill-name` namespacing, Claude Code
enterprise managed settings as a skill location, and the Registry's revision model.

What could **not** be verified anywhere: a documented review/approval gate, signing, or provenance
attestation for skills in any harness.

Interim controls that don't depend on unshipped infrastructure:

- **Pin vendored content to a tag or commit.** A branch pin is not a pin.
- **Keep [`ATTRIBUTION.md`](../../ATTRIBUTION.md) as the provenance artefact** — no harness supplies one.
- **Repo-side CI is the approval gate.** The harness-side consent prompt is not one: Gemini's activation
  prompt is bypassed for built-in skills and by a persisted "always allow", and Claude Code has no
  activation consent step at all.

---

## Recommended actions, ranked

| # | Action | Why now | Size |
|---|---|---|---|
| 1 | ~~Fix the `when_to_use` rationale in `DISCOURAGED_KEYS`~~ **done 2026-09-02** | It was factually wrong — see below | 2 lines |
| 2 | ~~Add a per-group description-budget ceiling to CI~~ **done 2026-09-02** | The aggregate listing is the real constraint | small |
| 3 | Add a `.agents/skills/` shadowing check to the installer | Silent shadowing of the Gemini port, no warning from anywhere | small |
| 4 | Note in the rationale comments that 500 lines / 500 chars are convention, not measurement | Honest provenance; prevents false confidence | 2 comments |
| 5 | Reject non-spec top-level frontmatter keys as errors | Portability to the packaging path | small |
| 6 | Decide the shared-core question for the 11 identical skills | Half the shared surface is hand-maintained duplication | design |
| 7 | SKILL_ID mapping layer, if a Registry push is ever wanted | 11 skills cannot register under their own names | medium |

**On #1, as implemented.** The validator had said trigger conditions in `when_to_use` "are simply never
seen". Claude Code's docs contradict that verbatim: it is "Appended to `description` in the skill listing
and counts toward the 1,536-character cap." The rule stayed — the key is still rejected by
`package_skill.py`, the Skills API, and claude.ai upload — with the reason corrected to spec-path
portability.

It was **not** promoted to error, and the reason is a measurement taken while implementing it. Nothing in
either tree sets `when_to_use` or `tools`; earlier greps that suggested otherwise were matching body text
in examples and templates, not frontmatter. But **44 skills do carry other non-spec keys**:

| Key | Skills | Note |
|---|---|---|
| `type` | 32 | Vendored Trail of Bits bundle — **load-bearing**, the bundle validator requires it |
| `version` | 8 | |
| `languages` | 2 | |
| `user-invocable` | 2 | A documented Claude Code field, still outside the spec |

So erroring on a curated pair with zero offenders, while 44 skills carry unflagged non-spec keys, would
be arbitrary. Severity belongs to the general check (**action #5**) — which this measurement reprices: it
cannot be a flat rejection, because `type` is required by vendored content. It needs the
allowlist-with-a-written-reason pattern, not a ban.

**On #2, as implemented.** `budget_tokens` is declared per group in `groups.toml` and enforced by
`check_group_budgets`. A **global** ceiling was rejected: `gemini/gcp` costs ~3,180 tokens against a
next-largest group of ~509, so any ceiling it passed would bind on nothing, and any ceiling that bound on
it would force trimming 26 vendored Apache-2.0 Google descriptions — which
[decisions-not-taken.md](decisions-not-taken.md) already refused, since each such edit is paid again at
the next upstream re-sync. A group being large is not the defect; a group growing past what someone
signed off on, unnoticed, is. A budget more than 1.5× the real cost warns, so a ceiling cannot be set
high enough to never bind.

## Related

- [documentation-drift.md](documentation-drift.md) — the generate/validate/exempt split this note extends
  from prose to skill content
- [decisions-not-taken.md](decisions-not-taken.md) — includes the earlier decision *not* to trim the
  over-budget Google descriptions; §4 is new evidence bearing on it
- [vendored-content.md](vendored-content.md) — re-sync hazards, relevant to §11's pinning rule
