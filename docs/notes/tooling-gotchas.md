# Tooling gotchas

Environment and tooling failures hit in this repository that cost real time to diagnose. Each one
looked like something else at first.

Related: [collaboration.md](collaboration.md) · [decisions-not-taken.md](decisions-not-taken.md)

---

## `actions/checkout` defaults to a shallow clone

`actions/checkout@v4` uses `fetch-depth: 1` unless told otherwise. A CI step that inspects a commit
*range* — `git log origin/main..HEAD` — cannot resolve the base ref in a shallow clone.

**The failure mode is silent.** The range resolves to nothing, the check finds no offenders, and the
step passes. You get a green tick from a check that examined zero commits.

Any range-based check in `.github/workflows/` must set:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

When adding such a check, verify it **fails on bad input** before trusting a pass.

---

## A PR description is not in git

Obvious in hindsight, easy to miss: a commit-message check never sees the pull request body. They
are separate surfaces and need separate checks. The body has to be read through the API:

```bash
gh api "repos/$OWNER/$REPO/pulls/$PR" --jq '.body // ""'
```

---

## `attribution.commit` is a string, not a boolean

Claude Code's `attribution` settings take **strings**; an **empty string** hides the attribution.
`false` is a type error that silently does nothing — the config still loads, and the trailer keeps
appearing.

```json
{ "attribution": { "commit": "", "pr": "", "sessionUrl": false } }
```

(`sessionUrl` *is* a boolean. Only `commit` and `pr` are strings.) `includeCoAuthoredBy` is
deprecated; do not use it.

**How to find this out:** the published docs page is JS-rendered, so WebFetch returns only anchor
stubs — the detail sections are unreachable that way. The authoritative source is the JSON schema
shipped with the IDE extension:

```
~/.codeoss-*/extensions/anthropic.claude-code-*/claude-code-settings.schema.json
```

Validate any settings change against it before committing:

```bash
uv run --with jsonschema python -c "..."   # Draft7Validator against that schema
```

---

## A settings change cannot affect the session that makes it

Instructions are loaded into a session at its start. Writing `.claude/settings.json` mid-session
does not retroactively change that session's behaviour — it applies from the next one.

Practical consequence: you cannot verify an attribution setting by making a commit in the same
session that added it. Verify against the schema, and rely on CI for the current session's output.

---

## `local a="$1" b="$2$a"` breaks under `set -u`

Bash's `local` declares **all** its names before assigning **any** of them. So this fails with
`a: unbound variable`:

```bash
set -u
f() { local name="$1" link="$DEST/$name"; }   # BROKEN
```

Split the declaration:

```bash
f() { local name="$1"; local link="$DEST/$name"; }   # fine
```

Hit while writing `scripts/install.sh`; the error points at the `local` line and looks like the
caller passed nothing.

---

## Git identity was unset on this machine

`git commit` failed with *"Author identity unknown"*. There was no global `user.name` / `user.email`.
It is now set **repository-locally** rather than globally, so other repos are unaffected — meaning a
fresh clone elsewhere will hit the same wall.

Note the address in use is not a verified GitHub email, so commits may show as unattributed rather
than linked to the account. That is deliberate; see [collaboration.md](collaboration.md).

---

## Stacked PRs: retarget the child before deleting the parent branch

With PR B based on PR A's branch, after merging A:

1. **First** `gh pr edit B --base main`
2. **Then** delete A's branch

Doing it the other way leaves B pointing at a branch that no longer exists. GitHub usually
auto-retargets, but relying on that when the explicit order is free is a bad trade.

After retargeting, confirm the diff did **not** balloon — B should still show only its own commits.
If A's commits appear in B, the retarget resolved against the wrong base.

---

## `uv` needs `--no-project` inside this repo

Running a standalone PEP 723 script from within a directory that has its own project metadata can
make `uv` try to resolve the project instead of the script's inline dependencies. `uv run --no-project
script.py` forces the script's own metadata to win.
