#!/usr/bin/env bash
# Clean up a git worktree and its paired tmx2 session.
# Handles the error-prone sequence: kill session → remove worktree → prune → delete branch.
#
# Usage:
#   wt_cleanup.sh <worktree-name> [--delete-branch]
#
# Examples:
#   wt_cleanup.sh frontend              # remove worktree + session, keep branch
#   wt_cleanup.sh frontend --delete-branch  # also delete the wt/frontend branch

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
REPO_NAME="$(basename "$REPO_ROOT")"
WT_BASE="$(dirname "$REPO_ROOT")/${REPO_NAME%%_*}_worktrees"

NAME="${1:?Usage: wt_cleanup.sh <worktree-name> [--delete-branch]}"
DELETE_BRANCH="${2:-}"

WT_DIR="${WT_BASE}/${NAME}"
SESSION_NAME="ge_${NAME}"
BRANCH_NAME="wt/${NAME}"

# 1. Kill tmx2 session
if tmx2 has-session -t "$SESSION_NAME" 2>/dev/null; then
  tmx2 kill-session -t "$SESSION_NAME"
  echo "Killed session: $SESSION_NAME"
else
  echo "No session: $SESSION_NAME"
fi

# 2. Remove worktree (force to handle untracked files)
if git worktree list | grep -q "$WT_DIR"; then
  git worktree remove --force "$WT_DIR" 2>/dev/null || true
  echo "Removed worktree: $WT_DIR"
else
  echo "No worktree at: $WT_DIR"
fi

# 3. Clean stale directory if left behind
if [ -d "$WT_DIR" ]; then
  rm -rf "$WT_DIR"
  echo "Cleaned stale directory: $WT_DIR"
fi

# 4. Prune worktree metadata
git worktree prune
echo "Pruned worktree metadata"

# 5. Optionally delete branch
if [ "$DELETE_BRANCH" = "--delete-branch" ]; then
  if git branch --list "$BRANCH_NAME" | grep -q .; then
    git branch -D "$BRANCH_NAME"
    echo "Deleted branch: $BRANCH_NAME"
  else
    echo "No branch: $BRANCH_NAME"
  fi
fi

echo "Done."
