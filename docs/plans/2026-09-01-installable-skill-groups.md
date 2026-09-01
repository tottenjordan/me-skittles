# Installable Skill Groups Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` skill to implement this plan task-by-task.

**Goal:** Let users install a coherent subset of skills — `./scripts/install.sh --group gcp` — so nobody pays context for skills they never use.

**Architecture:** A `groups.toml` manifest at the repo root maps `(tree, group) -> skills`. The installer resolves `--group`; the validator enforces that the manifest and the directory tree stay in agreement, and that the README names only skills that exist.

**Tech Stack:** TOML parsed with stdlib `tomllib` (no new dependency — `scripts/validate-skills.py` already requires Python ≥3.11), Bash installer, GitHub Actions.

---

## Context

Every skill's `description` loads at the start of **every session**, whether or not the skill fires;
only bodies are deferred. Measured across the current catalogue:

| Tree | Skills | Standing cost per session |
|---|---|---|
| `claude/` | 26 top-level | ~1.9k tokens |
| `gemini/` | 55 top-level | ~5.2k tokens |

The Gemini figure is dominated by the 29-skill Google Cloud family. Someone doing ADK work rarely
needs `gcs-security-assessment` loaded, but `install.sh --all` gives them no way to say so — the
installer takes `--all` or an explicit list of 30-odd names.

**Decisions taken** (confirmed with the user):

| Decision | Choice |
|---|---|
| Strategy | Grouping only — vendored Google descriptions stay untouched |
| Group source | `groups.toml` manifest, seeded from `metadata.publisher: google` |
| README catalogue | Stays hand-written; the validator prevents drift |

Trimming those descriptions was considered and **explicitly declined** to keep upstream re-sync
clean. The analysis is preserved in [Appendix A](#appendix-a--the-trimming-option-not-scheduled) so
the option stays available; nothing in this plan implements it.

---

## Task 1: Add `groups.toml`

**File:** Create `groups.toml` (repo root)

Array-of-tables, one entry per `(tree, group)`, so each carries its own prose:

```toml
# Installable groups. ./scripts/install.sh --group <name> installs a whole group.
#
# Every skill directory must appear in exactly one group for its tree; the
# validator fails otherwise, so this file cannot silently drift from the tree.

[[group]]
name = "gcp"
tree = "gemini"
description = "Google Cloud and BigQuery — 29 Google-published skills. Start at gcp-data-pipelines."
skills = ["accidental-data-loss-prevention", "bigquery-ai-ml", ...]
```

Both partitions are already verified complete and disjoint:

| Group | `claude/` | `gemini/` |
|---|---:|---:|
| `agents` | 4 | 4 |
| `workflow` | 9 | 8 |
| `testing` | 6 | 6 |
| `diagrams` | 2 | 2 |
| `tools` | 5 | 3 |
| `meta` | 2 | 5 |
| `gcp` | — | 29 |
| **total** | **28** | **57** |

Seed the `gcp` group by selecting on `metadata.publisher: google`, which matches exactly those 29
and cleanly excludes the other four Gemini-only skills (`gemini-md-author`, `gemini-md-improver`,
`git-commit-formatter`, `license-header-adder`). Do not derive it at runtime — the manifest is the
source of truth, and the metadata is only how the initial list is generated.

## Task 2: Teach the installer about groups

**File:** Modify `scripts/install.sh`

Add `--group <name>` (repeatable), resolving to that group's skills for the active `--tree`. Reuse
the existing `AVAILABLE` / `status_of` / `owned_by_repo` machinery — every safety property already
verified stays intact: idempotent, repairs broken links, and never removes a link it did not create.

`--list` gains a `GROUP` column and a per-group summary:

```
  SKILL                                    GROUP      STATUS
  adk                                      agents     installed
  bigquery-sql                             gcp        -
  ...
  gcp        29 skills   0 installed
  agents      4 skills   4 installed
```

Parsing: keep the installer dependency-free by extracting the group's `skills` list with `awk`
rather than adding a TOML parser to Bash. The manifest's shape is fixed and validated by Task 3, so
a narrow parser is safe here — but it must **fail loudly** on an unknown group name rather than
silently installing nothing.

Also add `--group` to the usage block, which `--help` prints from the file header.

## Task 3: Validate the manifest

**File:** Modify `scripts/validate-skills.py`

Add `check_groups(repo, report)`, following the shape of the existing `check_plugin_manifests`:

```python
import tomllib   # stdlib on 3.11+; no new dependency
```

Errors:

- `groups.toml` missing or unparseable
- A group names a skill that does not exist in its tree
- A skill directory belongs to **no** group, or to **more than one**, in its tree
- A group entry is missing `name`, `tree`, `description`, or `skills`

This is what makes the manifest safe to trust: adding a skill without grouping it fails CI, so the
manifest cannot rot the way the README did.

## Task 4: Validate the README against reality

**File:** Modify `scripts/validate-skills.py`

Extend the same check to compare the README's catalogue against the tree:

- **Error** if the README names a skill in backticks that exists in neither tree — this is the
  defect class that shipped four dangling `adk-*` entries originally.
- **Warning** if a skill exists but the README never mentions it.

Scope the scan to the catalogue section so incidental prose mentions do not trip it. Two known
intentional exceptions must not fire: `frontend-design` (named as a pointer to the official plugin)
and skill names inside the bundle listing.

## Task 5: Document

**Files:** Modify `README.md`, `CLAUDE.md`

In the README's **Setup** and **Context cost** sections, lead with group install as the default
recommendation:

```bash
./scripts/install.sh --group agents --group workflow    # ~1.2k tokens
./scripts/install.sh --tree gemini --group gcp          # the 29-skill family, on demand
```

State the per-group token cost so the trade is visible at the point of decision. In `CLAUDE.md`, add
one line under Conventions: a new skill must be added to `groups.toml`, or CI fails.

---

## Files that change

- **New:** `groups.toml`
- **Modified:** `scripts/install.sh` (`--group`, `GROUP` column), `scripts/validate-skills.py`
  (`check_groups`, README cross-check), `README.md`, `CLAUDE.md`

## Verification

1. **Manifest is complete and disjoint** — the validator's own check is the test:
   `uv run scripts/validate-skills.py` → 117 skills, 0 errors.
2. **Negative tests, both new checks.** Remove a skill from `groups.toml` → expect a "belongs to no
   group" error. Add it to a second group → expect "more than one group". Add a fake skill name to
   the README catalogue → expect an error. Revert each and confirm clean.
3. **Group install against a scratch destination**, never `~/.claude/skills`:
   ```bash
   T=$(mktemp -d)
   ./scripts/install.sh --dest "$T" --group agents        # expect 4 links
   ./scripts/install.sh --dest "$T" --group agents        # expect 0 changed (idempotent)
   ./scripts/install.sh --tree gemini --dest "$T" --group gcp   # expect 29
   ./scripts/install.sh --dest "$T" --group nonesuch      # expect a clear failure, not silence
   ./scripts/install.sh --dest "$T" --uninstall --group agents  # expect 4 removed
   ```
4. **Safety properties still hold** — re-run the existing checks: a real directory and a symlink
   pointing outside the repo must both survive `--group` install *and* `--uninstall`.
5. **Token accounting is honest** — recompute the per-group description totals quoted in the README
   rather than copying the numbers from this plan.
6. **CI green.**

## Out of scope

- Trimming any description (Appendix A) — declined; upstream text stays as-is.
- Generating the README catalogue from the manifest — declined; it stays hand-written, validated.
- Nested or overlapping groups. Exactly-one-group is what makes the completeness check meaningful;
  revisit only if a real skill genuinely belongs in two.
- Deduplicating `gcp-diagram`'s 1.8M of cross-tree assets. Already investigated: `overlay_icons.py`
  resolves `ASSETS_DIR` relative to its own file, so skill directories must stay self-contained.

---

## Appendix A — the trimming option (not scheduled)

Ten Gemini descriptions exceed the 500-character budget, together costing **7,830 chars (~1,957
tokens) every session**. Recorded here because the analysis is done and the option remains open —
**this plan does not implement it.**

### Per-skill verdict

Length alone is a poor signal. What matters is whether the characters are doing work: enumerating
trigger surface (**load-bearing**) or restating and scaffolding (**waste**). Measured per skill:

| Skill | Chars | Waste | Verdict |
|---|---:|---|---|
| `building-data-apps` | 989 | 55 scaffold, 6 enumerated conditions | **Trim** → ~315 |
| `gcp-dataflow` | 984 | 46 scaffold, capabilities stated **twice** | **Trim** → ~343 |
| `notebook-guidance` | 1002 | 55 scaffold, 114 negatives, plus a body-grade instruction | **Trim** → ~366 |
| `gcp-pipeline-resource-provisioning` | 950 | **381 chars — 40% — is one "Do not use when" clause** | **Trim** → ~400 |
| `discovering-gcp-data-assets` | 651 | 55 scaffold, 49 negatives, 4 enumerated | **Trim** → ~380 |
| `google-cloud-storage-basics` | 952 | none — 12 genuine capability areas | **Trim lightly** → ~523, still over |
| `federate-lakehouse-catalog` | 603 | none | **Leave** |
| `accidental-data-loss-prevention` | 599 | none | **Leave** |
| `managing-python-dependencies` | 572 | 48 scaffold | **Leave** |
| `ml-best-practices` | 528 | none | **Leave** |

**Six worth trimming, four to leave alone.** Reasoning for the four:

- **`accidental-data-loss-prevention`** — the description enumerates the exact commands that must
  halt execution (`DROP TABLE`, `gsutil rm`, `gcloud projects delete`, KMS destruction). That
  enumeration *is* the trigger mechanism, and the body is only 31 lines: the description carries
  more of this skill than the body does. Under-triggering a data-loss guard costs far more than 600
  characters. **Do not touch this one even if the others are trimmed.**
- **`managing-python-dependencies`** — six enumerated situations, each a distinct moment the skill
  must fire (about to run `pip install`, creating a notebook, writing an `import`). Same argument at
  lower stakes: a discipline skill that fails to fire is inert.
- **`federate-lakehouse-catalog`** and **`ml-best-practices`** — zero scaffolding, zero negatives,
  and only 103 and 28 characters over budget. Nothing to remove without losing meaning.

Correcting an earlier estimate: extrapolating all ten at the drafted ratio suggested ~1,200
tokens/session. Excluding the four that should be left alone, the realistic saving is **~3,200 chars
(~800 tokens/session)** — still a ~15% cut to the Gemini tree's standing cost, but not the larger
figure.

### Where would the trimmed text go?

**Nowhere. No new files, no subdirectory.** This is a different operation from the over-length
*body* split, where content genuinely moved into `references/*.md` and needed a link left behind.

A `description` is frontmatter metadata, not prose with a home. Everything a trim removes falls into
one of three buckets, and none of them needs relocating — verified against the actual bodies:

| Bucket | Example | Destination |
|---|---|---|
| Scaffolding | `Relevant when any of the following conditions are true: 1. …` | **Deleted** — carries no information |
| Restated capabilities | `gcp-dataflow` names Java/Python/Go setup, Cloud Build and diagnostics twice | **Deleted** — its body already covers them 17, 18 and 18 times respectively |
| Body-grade instruction | `notebook-guidance`: "DO NOT use the Python BigQuery client library; use `%%bqsql`" | **Already in the body** — `%%bqsql` appears there 10 times |

So the trim is purely subtractive. If a future case *did* surface genuinely new information living
only in a description, it would move into the `SKILL.md` body — not a reference file — and there is
room: the six trim candidates run 157–400 lines against the 500-line cap.

The verification step for any such work is therefore an equality check, not a link check: confirm
every concept named in the old description still appears in the body, then diff the frontmatter
alone.

### Should any be split?

Assessed and **rejected in every case**, for two reasons.

The only skill with a genuine structural case is **`gcp-dataflow`** — 400-line body, 6 H2 sections,
and a description spanning two distinct jobs (authoring pipelines vs. diagnosing running ones),
which would divide cleanly into `gcp-dataflow` and `gcp-dataflow-diagnostics`. But splitting a
vendored skill is a *larger* divergence from upstream than trimming its description, and trimming
was already declined on exactly that ground.

**`google-cloud-storage-basics`** looks like a split candidate — its description names roughly twelve
capability areas — but its body is only 187 lines across 3 sections. The breadth lives in the
description, not the content; splitting would yield several skills with almost no body. It is
functionally an overview, and should stay one.

### Is any of it redundant?

**No.** Every one of the ten was checked for description overlap against all 55 Gemini skills. The
highest score for any of them is **0.14** (`ml-best-practices` ↔ `bigquery-ai-ml`, and
`gcp-pipeline-resource-provisioning` ↔ `gcp-data-pipelines`) — far below the level that would
indicate duplication or competing triggers. None is a candidate for deletion or merging.

The nearest thing to redundancy is cross-tree: `managing-python-dependencies` (Gemini) covers
similar ground to `modern-python` (Claude). They were deliberately kept in separate trees during the
import precisely so they never compete for the same trigger.

### Bloat patterns, for future authors

Three patterns account for nearly all the recoverable characters, and are worth stating in
`writing-skills` regardless of whether these ten are ever trimmed:

1. **Enumerated scaffolding** — `Relevant when any of the following conditions are true: 1. … 2. …`
   costs ~55 characters before the first real trigger word.
2. **Restated capabilities** — `gcp-dataflow` lists Java/Python/Go setup, Cloud Build, and
   diagnostics, then lists them again under "Key capabilities".
3. **Body-grade instructions in the trigger field** — `notebook-guidance` ends with "DO NOT use the
   Python BigQuery client library; instead, you MUST use `%%bqsql`". That is an instruction for
   after the skill fires, and every session pays for it.

Negative clauses (`Do NOT use when…`) are the judgement call. They genuinely prevent mis-firing, but
`gcp-pipeline-resource-provisioning` spends 381 characters — 40% of its budget — ruling out
Terraform, multi-cloud, VMs, networks, Kubernetes and IAM. Two clauses would do the same work.

Worked examples, drafted and measured:

**`gcp-dataflow`** — 984 → 343 chars

> Use when creating, packaging, running, debugging, or tuning Apache Beam pipelines on Dataflow,
> including Flex Templates. Covers Java/Python/Go project setup, Cloud Build integration, and
> diagnostics for streaming job health, bottlenecks, and autoscaling. Not for non-Dataflow GCP
> resources or pipeline technologies other than Beam on Dataflow.

**`notebook-guidance`** — 1002 → 366 chars

> Use when a data analysis, exploration, or visualization task needs multiple steps, queries, or
> charts; when the user asks for a notebook (.ipynb); when creating, editing, or executing notebook
> cells; or when querying BigQuery from a notebook. Covers execution and validation, library
> installation, notebook structure, data cleaning, plotting, and the %%bqsql magics.

**`building-data-apps`** — 989 → 315 chars

> Use when building a data dashboard, data application, or visualization UI backed by a GCP data
> source (BigQuery by default), or when adding a Gemini Data Analytics "chat with your data"
> experience. Covers React + Vite and Streamlit. Not for backend-only services, CLI scripts, or web
> apps that are not data-centric.

Every trim would edit vendored Apache-2.0 Google content, which would need recording in
`ATTRIBUTION.md` under the same precedent as the Trail of Bits reorganisation.
