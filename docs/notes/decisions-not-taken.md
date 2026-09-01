# Decisions not taken

Investigations that concluded **"don't"**. Each looked like an obvious improvement, was measured,
and turned out to be wrong or not worth it. Recorded so the next person does not spend the same
effort reaching the same answer.

Related: [vendored-content.md](vendored-content.md) · [tooling-gotchas.md](tooling-gotchas.md)

---

## Do not deduplicate `gcp-diagram`'s icon assets

**Looks like:** 1.8 MB of icon assets, byte-identical between `claude/gcp-diagram/assets/` and
`gemini/gcp-diagram/assets/` — 160 files each, together roughly **22% of the whole repository**. An
obvious candidate for a shared top-level `assets/` directory.

**Why not:** `overlay_icons.py` resolves its asset path relative to its own file:

```python
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
```

A skill directory therefore has to be **self-contained**. Moving the assets to a shared location
breaks `gcp-diagram` for anyone who copies the skill directory rather than symlinking it — and
copying is a perfectly reasonable way to install a skill.

**Verdict:** the duplication is a correctness requirement, not waste. Leave it.

---

## Do not trim the over-budget Google descriptions

**Looks like:** ten Gemini skill descriptions exceed the 500-character budget, together costing
~1,957 tokens of context on **every session**. Trimming is pure subtraction — the material is
scaffolding, restated capability lists, or instructions the body already contains.

**Why not:** every one of them is vendored Apache-2.0 Google content, and each edit is a cost paid
again at the next upstream re-sync. The decision was to solve the same problem with **installable
groups** instead — don't install what you don't need — which needs no upstream divergence at all.

**If it is ever revisited**, two things matter:

- The realistic saving is **~800 tokens/session**, not the ~1,200 an early estimate suggested. Four
  of the ten must be left alone: their length is load-bearing trigger surface, not padding.
- **`accidental-data-loss-prevention` must not be touched under any circumstances.** Its 600-character
  description enumerates the exact commands that must halt execution — `DROP TABLE`, `gsutil rm`,
  `gcloud projects delete`, KMS destruction. That enumeration *is* the trigger mechanism, and the
  body is only 31 lines. Under-triggering a data-loss guard costs far more than 600 characters.

Full per-skill analysis, with worked examples: Appendix A of
[`docs/plans/2026-09-01-installable-skill-groups.md`](../plans/2026-09-01-installable-skill-groups.md).

---

## Do not split `gcp-dataflow` or `google-cloud-storage-basics`

**Looks like:** both have very long descriptions spanning several distinct jobs — `gcp-dataflow`
covers authoring pipelines *and* diagnosing running ones; `google-cloud-storage-basics` names about
twelve capability areas.

**Why not:**

- `gcp-dataflow` has a genuine structural case (400-line body, 6 sections, cleanly divisible into
  authoring and diagnostics) — but splitting a vendored skill is a *larger* upstream divergence than
  trimming its description, which was already declined on exactly that ground.
- `google-cloud-storage-basics` looks divisible until you read the body: **187 lines across 3
  sections**. The breadth is in the description, not the content. Splitting would yield several
  skills with almost no body. It is functionally an overview and should stay one.

---

## Do not add a local pre-commit hook

**Looks like:** the fastest way to stop unwanted commit trailers — block them at creation.

**Why not:** `.git/hooks/` is not version-controlled, so a fresh clone silently has no protection.
You end up with a rule that appears enforced and isn't. CI catches the same thing at PR time,
needs no local setup, and is agent-agnostic.

---

## Do not rewrite `main` to strip attribution

**Looks like:** 16 merged commits carry a `Co-Authored-By: Claude` trailer. `git filter-repo` would
produce a clean log.

**Why not:** rewriting shared history invalidates every existing SHA, rewrites five merge commits,
and breaks any existing clone — to remove a text trailer. The unmerged commits were cleaned and PR
descriptions were edited (non-destructive, works retroactively); merged history was left as a
historical artifact.

See [collaboration.md](collaboration.md) for the attribution rules now in force.
