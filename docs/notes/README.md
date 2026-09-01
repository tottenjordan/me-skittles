# Session notes

Knowledge that outlives a single session and is **not recoverable** from the code, git history,
`CLAUDE.md`, `GEMINI.md`, or the other docs. Decisions and their reasoning, dead ends already
explored, and environment traps already sprung.

If something is derivable by reading the repo, it does not belong here — it belongs in the repo.

---

## Notes

| Note | What it saves you |
|---|---|
| [decisions-not-taken.md](decisions-not-taken.md) | Five investigations that concluded **"don't"** — deduplicating `gcp-diagram`'s 1.8 MB of assets, trimming the over-budget Google descriptions, splitting oversized skills, pre-commit hooks, rewriting `main`. Read before "optimising" any of them. |
| [vendored-content.md](vendored-content.md) | When to edit third-party content and when to leave it, the precedents already set, and the re-sync hazard that reintroduces fixed defects. |
| [collaboration.md](collaboration.md) | Why agent attribution kept reappearing and how it is now prevented; commit and PR conventions; how plans are executed and reviewed. |
| [documentation-drift.md](documentation-drift.md) | Why the docs are both generated *and* validated — the three drift incidents, what a checker can and cannot catch, and the trap that generation protects only the marked region while the paragraph beside it rots. Read before simplifying that machinery, or before hand-writing a number into a live doc. |
| [tooling-gotchas.md](tooling-gotchas.md) | Environment failures with silent or misleading symptoms — shallow CI clones, JS-rendered docs, `set -u` and `local`, unset git identity, stacked-PR ordering. |
| [multi-harness-skills.md](multi-harness-skills.md) | What actually ports between Claude Code, Gemini CLI, Codex and Cursor (six frontmatter fields — less than you'd think), why Claude Code's 1% listing budget makes `--all` an anti-pattern, how thin this repo's Gemini port measurably is, and the Skill Registry rules that 11 of our skills break. Read before adding a harness, a frontmatter key, or a bulk install. |

## Related

- [`docs/plans/`](../plans) — implementation plans, written before the work and kept afterward
- [`CODE_STANDARDS.md`](../../CODE_STANDARDS.md) — the binding rules these notes explain
- [`ATTRIBUTION.md`](../../ATTRIBUTION.md) — what is vendored, from where, under which licence

## Adding a note

One topic per file; link related notes rather than repeating them. Add a row above with a hook that
says what the note *saves the reader*, not just what it is about.

Check for an existing note first and update it rather than spawning a near-duplicate. Delete notes
that turn out wrong or go stale — a confidently wrong note is worse than none.

A note reflects what was true when written. If one names a file, flag, or command, re-verify it
still exists before acting on it.

**Notes are point-in-time and are deliberately not validated.** `scripts/validate-skills.py` checks
stated counts only in the four live documents listed in its `LIVE_DOCS` constant — `README.md`,
`CLAUDE.md`, `GEMINI.md`, `ATTRIBUTION.md` — and `scripts/sync-docs.py` generates into none of the
files here. A figure in a note is the measurement that justified a decision, so refreshing it to
today's number would delete the evidence. Leave stale numbers alone; if one misleads, date it or
say what has changed since, rather than overwriting it.

Keep this index **under 200 lines**.
