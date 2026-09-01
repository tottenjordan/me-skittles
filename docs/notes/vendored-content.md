# Vendored content: when to edit, when to leave

Most of this repository is third-party. [ATTRIBUTION.md](../../ATTRIBUTION.md) records *what* is
vendored and under which licence; this note records the **decision rule** for changing it, and the
precedents already set.

Related: [decisions-not-taken.md](decisions-not-taken.md) · [collaboration.md](collaboration.md)

---

## The rule

**Default to leaving upstream content exactly as it is.** Every local edit is a cost paid again at
the next re-sync: either the edit is silently overwritten, or someone has to re-apply it by hand
having first noticed it was there.

Edit only when leaving it **breaks something**. Cosmetic improvement, house-style alignment, and
"while I'm here" tidying do not qualify.

When you do edit, record the divergence in `ATTRIBUTION.md` with enough detail that a future re-sync
knows to **re-apply rather than overwrite**.

## Precedents

| Content | Decision | Why |
|---|---|---|
| Trail of Bits testing-handbook skills | **Edited** — reorganised for progressive disclosure | Ten skills exceeded the 500-line cap that the bundle's *own* validator enforces, failing 10 of 16 checks as vendored. Content was relocated into `references/`, not rewritten. Recorded in `ATTRIBUTION.md`. |
| Google Cloud skill descriptions | **Left alone** | Ten exceed the 500-character budget, costing ~800 tokens/session. Real, but not breakage. Solved instead with installable groups — don't install what you don't need. |
| Google skills with non-cloud subject matter | **Regrouped, not edited** | `skill-repair`, `managing-python-dependencies`, `ml-best-practices` moved to other groups in `groups.toml`. Group membership is ours; the skill content is not. |
| `gcp-diagram` duplicated icon assets | **Left alone** | Required for correctness, not waste. See [decisions-not-taken.md](decisions-not-taken.md). |

The pattern: **change our own metadata freely, change upstream content only under duress.**

## The re-sync hazard

The Gemini tree's ports were adopted from
[jswortz/my-skills](https://github.com/jswortz/my-skills). That upstream **still carries the
frontmatter defects fixed here** — title-cased `name` fields with spaces, and empty `name` on two
diagram skills. A naive re-sync reintroduces every one of them.

This is not hypothetical. It already happened once mid-session: adopting the upstream ports
overwrote six frontmatter fixes, which had to be re-applied on top.

**`scripts/validate-skills.py` is the guard.** After pulling from any upstream skills repository:

```bash
uv run scripts/validate-skills.py --tree gemini
```

It fails on invalid `name` fields, missing descriptions, and Claude terminology under `gemini/` —
precisely the defect classes a re-sync reintroduces.

A related trap from the same episode: restoring a *file* is not the same as restoring its *link*.
A 197-line reference doc was correctly re-copied after an overwrite, but the `SKILL.md` section
linking it was not — leaving the content present and unreachable. Unlinked reference files are
invisible to the agent. Sweep for orphans after any bulk content operation.

## The two trees are ports, not copies

`gemini/` is a **port** of `claude/`: agent terminology, `GEMINI.md` vs `CLAUDE.md`, and
`.gemini-plugin/` vs `.claude-plugin/` differ deliberately.

**Never `cp` a skill from one tree to the other.** It undoes the port, and CI fails on it. Edit both,
adapting the wording.

The validator's Claude-terminology check keeps a small allowlist for legitimate third-party
references — documenting Claude Desktop as an MCP client, or `claude` as an attribution *label
value*. Each entry requires a stated reason, so exemptions are a visible decision rather than a
silent weakening.
