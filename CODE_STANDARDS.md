# Code standards

Consult this before writing code or changing the environment in this repository. It is short on
purpose — each rule states *why*, so it survives contact with someone who disagrees.

Referenced from [CLAUDE.md](CLAUDE.md) and [GEMINI.md](GEMINI.md).

---

## Attribution

**Never add agent attribution to commits or pull requests.** No `Co-Authored-By: Claude` (or any
other agent) trailer, no "Generated with …" footer, no session links.

This applies to **every contributor and every agent**, not just Claude Code. The commits and PRs in
this repository are the author's work; tooling provenance belongs in the tooling, not the history.

Three layers enforce it, deliberately:

| Layer | Covers | Limitation |
|---|---|---|
| `.claude/settings.json` → `attribution` | Claude Code, at the source | Only Claude Code. Only new sessions — a running session already has its instructions loaded |
| CI check on commit messages | Any commit reaching a PR | Cannot see PR descriptions |
| CI check on the PR description | The PR body | Only fires on `pull_request` events |

The CI layer is the one that actually holds, because it is **agent-agnostic** — it inspects the
result, not the producer, so it covers Gemini CLI, other tools, and humans alike.

> The `attribution.commit` and `attribution.pr` settings are **strings**, and an **empty string
> hides** the attribution. `false` is a type error that silently does nothing. `includeCoAuthoredBy`
> is deprecated — do not use it.

## Python

**`uv` for everything.** Never bare `pip` or `python`.

```bash
uv run script.py          # execute
uv add <pkg>              # project dependency
uv run --with <pkg> ...   # one-off, no project change
```

Standalone scripts declare their own dependencies with [PEP 723](https://peps.python.org/pep-0723/)
inline metadata, so `uv run script.py` works with no setup:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
```

CI enforces this: a script importing an undeclared third-party package warns. Imports guarded by
`except ImportError` are exempt, since a script whose job is to detect a missing package must not
declare it.

**Lint and format with `ruff`.** Never `black` or `flake8`.

```bash
uvx ruff check .
uvx ruff format .
```

**Type-check with `ty`** (Astral's checker) and **test with `pytest`**.

The detailed reference is the `modern-python` skill — [`claude/modern-python/SKILL.md`](claude/modern-python/SKILL.md).
It already mandates this exact stack; follow it rather than re-deriving conventions here.

> **Current reality:** this repo has no `pytest` suite. `scripts/validate-skills.py` is its de facto
> test. `pytest` applies to new Python code; there is no expectation of backfilling.

## Skills

Both trees are validated in CI. These fail the build:

- `SKILL.md` under **500 lines** — the body loads in full on every trigger, so detail belongs in
  `references/` and gets linked. An unlinked reference file is invisible to the agent.
- `description` present, under **500 characters**, written as *trigger conditions* rather than a
  summary. Descriptions load **every session** whether or not the skill fires, so length is a
  standing context cost.
- `name` lowercase-kebab and matching its directory.
- No retired model IDs outside text that discusses their retirement.
- No Claude terminology under `gemini/` — that tree is a **port**, not a copy. Never `cp` a skill
  across; it undoes the port.
- Correct plugin manifest per tree: `.claude-plugin/` under `claude/`, `.gemini-plugin/` under
  `gemini/`.

Run before committing:

```bash
uv run scripts/validate-skills.py
```

## Documentation

**A derived fact in a live document is generated or validated, never hand-maintained** — counts,
token budgets and group membership in `README.md`, `CLAUDE.md`, `GEMINI.md` and `ATTRIBUTION.md`
are copies of what the tree and `groups.toml` already say, and copies drift.
`uv run scripts/sync-docs.py` writes the generated tables (`--check` in CI), and
`scripts/validate-skills.py` checks the rest.
`docs/notes/` and `docs/plans/` are exempt: they record what was true when written. Why both
mechanisms, and why not just generate everything —
[docs/notes/documentation-drift.md](docs/notes/documentation-drift.md).

## Git

- **One commit per logical change.** Short imperative subject; body explaining *why*, not *what*.
- **Stage deliberately.** Never `git add -A` without reading `git status` first.
- **Never force-push shared history.** Rewriting unmerged branch commits is fine with
  `--force-with-lease`; rewriting `main` is not.
- **Stacked PRs: retarget the child before deleting the parent branch.** Deleting first can strand
  or auto-close the child.
- **Never push unless asked.**

## Vendored content

Much of this repository is third-party — see [ATTRIBUTION.md](ATTRIBUTION.md). The default is to
**leave upstream content as it is**, because every local edit is a cost paid again at the next
re-sync.

Edit it only when leaving it breaks something, and record the divergence in `ATTRIBUTION.md` with
enough detail that a future re-sync knows to re-apply rather than overwrite. See
[docs/notes/vendored-content.md](docs/notes/vendored-content.md) for the decision rule and the
precedents already set.
