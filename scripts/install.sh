#!/usr/bin/env bash
#
# Install skills from this repo into an agent's skills directory by symlinking,
# so edits here take effect immediately with no re-install step.
#
#   ./scripts/install.sh --list                  what's available and what's installed
#   ./scripts/install.sh --all                   install every claude/ skill
#   ./scripts/install.sh writing-skills adk      install just these
#   ./scripts/install.sh --tree gemini --all     install the Gemini tree instead
#   ./scripts/install.sh --uninstall --all       remove links this repo owns
#   ./scripts/install.sh --all --dry-run         show what would happen
#
# Only links this script created are ever removed: a target that is a real
# directory, or a symlink pointing outside this repo, is left untouched.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TREE="claude"
DEST=""
MODE="install"
DRY=0
ALL=0
SELECTED=()

# Plugin bundles hold sub-skills under skills/ and are installed through the
# marketplace, not by symlinking the bundle directory.
BUNDLES="property-based-testing testing-handbook-skills"

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

usage() { sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0; }

while [ $# -gt 0 ]; do
  case "$1" in
    --tree)      TREE="${2:-}"; shift 2 ;;
    --dest)      DEST="${2:-}"; shift 2 ;;
    --all)       ALL=1; shift ;;
    --list|-l)   MODE="list"; shift ;;
    --uninstall) MODE="uninstall"; shift ;;
    --dry-run|-n) DRY=1; shift ;;
    -h|--help)   usage ;;
    -*)          die "unknown flag: $1 (try --help)" ;;
    *)           SELECTED+=("$1"); shift ;;
  esac
done

case "$TREE" in
  claude) DEFAULT_DEST="$HOME/.claude/skills" ;;
  gemini) DEFAULT_DEST="$HOME/.gemini/skills" ;;
  *) die "--tree must be 'claude' or 'gemini' (got '$TREE')" ;;
esac
DEST="${DEST:-$DEFAULT_DEST}"
SRC="$REPO/$TREE"
[ -d "$SRC" ] || die "no such tree: $SRC"

is_bundle() { case " $BUNDLES " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

# Does $DEST/$1 point into this repo? (i.e. is it ours to manage)
owned_by_repo() {
  local link="$DEST/$1" target
  [ -L "$link" ] || return 1
  target="$(cd "$(dirname "$link")" && readlink "$link")"
  case "$target" in "$REPO"/*) return 0 ;; *) return 1 ;; esac
}

status_of() {
  # Declared separately: `local a=$1 b=$a` declares both before assigning, so
  # `$a` is unset when `$b` is evaluated — fatal under `set -u`.
  local name="$1"
  local link="$DEST/$name"
  if   [ ! -e "$link" ] && [ ! -L "$link" ]; then echo "-"
  elif [ -L "$link" ] && [ ! -e "$link" ];  then echo "broken"
  elif owned_by_repo "$name";               then echo "installed"
  elif [ -L "$link" ];                      then echo "other-link"
  else                                            echo "real-dir"
  fi
}

mapfile -t AVAILABLE < <(cd "$SRC" && find . -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort)

if [ "$MODE" = "list" ]; then
  printf '%s -> %s\n\n' "$SRC" "$DEST"
  printf '  %-40s %s\n' "SKILL" "STATUS"
  for s in "${AVAILABLE[@]}"; do
    st="$(status_of "$s")"
    is_bundle "$s" && st="$st (bundle: install via marketplace)"
    printf '  %-40s %s\n' "$s" "$st"
  done
  printf '\n  %s available, %s installed\n' "${#AVAILABLE[@]}" \
    "$(for s in "${AVAILABLE[@]}"; do status_of "$s"; done | grep -c '^installed$' || true)"
  exit 0
fi

# Resolve the working set
if [ "$ALL" -eq 1 ]; then
  TARGETS=("${AVAILABLE[@]}")
elif [ "${#SELECTED[@]}" -gt 0 ]; then
  TARGETS=("${SELECTED[@]}")
  for s in "${TARGETS[@]}"; do
    [ -d "$SRC/$s" ] || die "no such skill in $TREE/: $s"
  done
else
  die "name at least one skill, or pass --all (try --list)"
fi

[ "$DRY" -eq 1 ] && printf '(dry run — nothing will change)\n\n'
[ "$DRY" -eq 0 ] && mkdir -p "$DEST"

changed=0 skipped=0
for s in "${TARGETS[@]}"; do
  link="$DEST/$s"
  st="$(status_of "$s")"

  if [ "$MODE" = "uninstall" ]; then
    case "$st" in
      installed|broken)
        printf '  remove   %s\n' "$s"
        [ "$DRY" -eq 0 ] && rm -f "$link"
        changed=$((changed+1)) ;;
      -) skipped=$((skipped+1)) ;;
      *) printf '  SKIP     %s (%s — not created by this script)\n' "$s" "$st"
         skipped=$((skipped+1)) ;;
    esac
    continue
  fi

  if is_bundle "$s"; then
    printf '  SKIP     %s (plugin bundle — install via the marketplace)\n' "$s"
    skipped=$((skipped+1)); continue
  fi

  case "$st" in
    installed) skipped=$((skipped+1)) ;;                       # already correct
    -|broken)
      printf '  link     %s\n' "$s"
      [ "$DRY" -eq 0 ] && ln -sfn "$SRC/$s" "$link"
      changed=$((changed+1)) ;;
    *)
      printf '  SKIP     %s (%s already at %s)\n' "$s" "$st" "$link"
      skipped=$((skipped+1)) ;;
  esac
done

printf '\n  %s changed, %s unchanged\n' "$changed" "$skipped"
if [ "$MODE" = "install" ] && [ "$DRY" -eq 0 ] && [ "$TREE" = "claude" ]; then
  printf '  Run /doctor in Claude Code to confirm they loaded.\n'
fi
