---
name: git-worktrees
description: "Manage git worktree lifecycle with paired tmx2 sessions. Use when creating, listing, cleaning up, or merging worktree branches. Covers: (1) Creating a worktree with a paired tmx2 session, (2) Listing worktrees and their session status, (3) Cleaning up stale worktrees (removing dirs, pruning, killing sessions, deleting branches), (4) Merging worktree branches back to main with conflict resolution, (5) Resetting worktree branches to main after merge. Triggers on: 'create a worktree', 'git worktree', 'clean up worktrees', 'merge worktree branches', 'tmx2 session for worktree', 'spawn worktree sessions'."
---

# Git Worktrees with tmx2 Sessions

Manage parallel development via git worktrees paired with tmx2 sessions.

## Conventions

- **Branch prefix:** `wt/<name>` (e.g., `wt/frontend`, `wt/agent-backend`)
- **Session prefix:** `ge_<name>` (e.g., `ge_frontend`, `ge_agent_backend`)
- **Worktree base:** Sibling directory `../<repo>_worktrees/` auto-detected from repo root. For a repo at `/home/user/my_project`, worktrees go in `/home/user/my_project_worktrees/`.

Detect paths:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
REPO_NAME="$(basename "$REPO_ROOT")"
WT_BASE="$(dirname "$REPO_ROOT")/${REPO_NAME}_worktrees"
```

## Create Worktree + Session

```bash
# New branch from main
git worktree add "${WT_BASE}/<name>" -b "wt/<name>" main

# Or existing branch
git worktree add "${WT_BASE}/<name>" "wt/<name>"

# Pair with tmx2 session
tmx2 new-session -d -s "ge_<name>" -c "${WT_BASE}/<name>"
```

Report: `Worktree ready. Attach: tmx2 attach -t ge_<name>`

## List Status

```bash
git worktree list          # all worktrees
tmx2 ls                    # all tmx2 sessions
```

Cross-reference to identify orphaned sessions (session exists, worktree gone) or unpaired worktrees (worktree exists, no session).

## Cleanup

Use `scripts/wt_cleanup.sh` for reliable cleanup. The sequence is error-prone when done manually (stale dirs, leftover metadata, force-remove needed for untracked files).

```bash
# Keep branch (for re-creation later)
bash scripts/wt_cleanup.sh <name>

# Delete branch too (after merge)
bash scripts/wt_cleanup.sh <name> --delete-branch
```

Manual sequence if script unavailable:

1. `tmx2 kill-session -t ge_<name>`
2. `git worktree remove --force "${WT_BASE}/<name>"` (force needed if untracked files)
3. `rm -rf "${WT_BASE}/<name>"` (if stale dir remains)
4. `git worktree prune`
5. `git branch -D wt/<name>` (optional, only if merged)

## Merge Worktree Branch to Main

```bash
# From main branch
git checkout main
git merge wt/<name> --no-edit
```

**If conflicts:** Resolve by reading both sides, keeping all non-overlapping changes. For `docs/` files where branches touch different sections, combine both sides in the conflict markers.

**After merge:** Either clean up with `--delete-branch`, or reset the worktree to continue fresh work:

```bash
git -C "${WT_BASE}/<name>" reset --hard main
```

## Batch Operations

Generate a spawn script for multiple worktrees:

```bash
#!/usr/bin/env bash
SESSIONS=("ge_main:${REPO_ROOT}" "ge_frontend:${WT_BASE}/frontend" ...)
for entry in "${SESSIONS[@]}"; do
  name="${entry%%:*}"; dir="${entry#*:}"
  tmx2 has-session -t "$name" 2>/dev/null && continue
  tmx2 new-session -d -s "$name" -c "$dir"
done
```

## Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `already exists` on worktree add | Stale dir from previous removal | `rm -rf` the dir, `git worktree prune`, retry |
| `branch already exists` on `-b` | Branch survived cleanup | `git branch -D wt/<name>`, retry |
| `contains modified or untracked files` | Normal — worktrees accumulate artifacts | Use `--force` on `git worktree remove` |
| tmx2 session missing after worktree remove | Removing the dir kills the session's cwd | Recreate: `tmx2 new-session -d -s ge_<name> -c <dir>` |
