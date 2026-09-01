#!/usr/bin/env bash
#
# Install skills from this repo into an agent's skills directory by symlinking,
# so edits here take effect immediately with no re-install step.
#
#   ./scripts/install.sh --list                  what's available and what's installed
#   ./scripts/install.sh --all                   install every claude/ skill
#   ./scripts/install.sh writing-skills adk      install just these
#   ./scripts/install.sh --group agents          install a group from groups.toml
#   ./scripts/install.sh --group agents --group testing   groups compose, and mix
#                                                with bare skill names
#   ./scripts/install.sh --tree gemini --all     install the Gemini tree instead
#   ./scripts/install.sh --uninstall --all       remove links this repo owns
#   ./scripts/install.sh --all --dry-run         show what would happen
#
# --list names each skill's group and summarises how much of each group is
# installed. Groups are per-tree: --tree gemini has groups claude does not.
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
GROUP_ARGS=()
GROUPS_TOML="$REPO/groups.toml"
GROUPS_PARSER="$REPO/scripts/parse-groups.awk"

# Plugin bundles hold sub-skills under skills/ and are installed through the
# marketplace, not by symlinking the bundle directory.
BUNDLES="property-based-testing testing-handbook-skills"

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

# The header comment above is the help text: print it from line 2 up to the
# first line that is not a comment, so adding usage lines needs no bookkeeping.
usage() {
  awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "${BASH_SOURCE[0]}"
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --tree)      TREE="${2:-}"; shift 2 ;;
    --dest)      DEST="${2:-}"; shift 2 ;;
    --group)     [ $# -ge 2 ] || die "--group needs a group name (try --list)"
                 GROUP_ARGS+=("$2"); shift 2 ;;
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

# --- groups -----------------------------------------------------------------
#
# groups.toml is read by scripts/parse-groups.awk, which flattens it to
# tree/group/skill triples so this script needs no TOML library. That program
# lives in its own file because scripts/validate-skills.py runs the *same* file
# in CI and diffs its output against Python's tomllib. So the guarantee here is
# not "the manifest is written in some blessed shape" but the stronger and
# simpler one: this parser and a real TOML parser agree about what the file
# says. Anything either one sees differently fails the build.
parse_groups() {
  [ -f "$GROUPS_TOML" ] || return 0
  awk -f "$GROUPS_PARSER" "$GROUPS_TOML"
}

# Checked here rather than inside parse_groups: that runs in a subshell under
# the process substitution below, where die() could not stop the script — a
# missing parser would just look like a manifest with no groups.
if [ -f "$GROUPS_TOML" ] && [ ! -f "$GROUPS_PARSER" ]; then
  die "missing $GROUPS_PARSER, needed to read $GROUPS_TOML"
fi

# Group membership for $TREE only. GROUP_ORDER keeps groups.toml's order so
# --list reads the same way the file does.
declare -A GROUP_OF=()        # skill  -> group
declare -A GROUP_SKILLS=()    # group  -> newline-separated skills
GROUP_ORDER=()
while IFS=$'\t' read -r _tree _group _skill; do
  [ "$_tree" = "$TREE" ] || continue
  [ -n "${GROUP_SKILLS[$_group]+x}" ] || GROUP_ORDER+=("$_group")
  GROUP_OF["$_skill"]="$_group"
  GROUP_SKILLS["$_group"]="${GROUP_SKILLS[$_group]:-}$_skill"$'\n'
done < <(parse_groups)

# Why a --group name did not resolve. "available: none" is ambiguous between
# three different fixes, so say which one applies: there is no manifest, the
# manifest has nothing for this tree, or the name is simply a typo.
groups_available() {
  if [ ! -f "$GROUPS_TOML" ]; then
    printf 'no groups are defined: %s does not exist' "$GROUPS_TOML"
  elif [ "${#GROUP_ORDER[@]}" -eq 0 ]; then
    printf '%s defines no groups for tree %s' "$GROUPS_TOML" "$TREE"
  else
    printf 'available: %s' "${GROUP_ORDER[*]}"
  fi
}

if [ "$MODE" = "list" ]; then
  printf '%s -> %s\n\n' "$SRC" "$DEST"
  printf '  %-40s %-10s %s\n' "SKILL" "GROUP" "STATUS"
  for s in "${AVAILABLE[@]}"; do
    st="$(status_of "$s")"
    is_bundle "$s" && st="$st (bundle: install via marketplace)"
    printf '  %-40s %-10s %s\n' "$s" "${GROUP_OF[$s]:--}" "$st"
  done
  printf '\n  %s available, %s installed\n' "${#AVAILABLE[@]}" \
    "$(for s in "${AVAILABLE[@]}"; do status_of "$s"; done | grep -c '^installed$' || true)"

  if [ "${#GROUP_ORDER[@]}" -gt 0 ]; then
    printf '\n'
    for g in "${GROUP_ORDER[@]}"; do
      mapfile -t gskills <<< "${GROUP_SKILLS[$g]}"
      # Bundles are never symlinked, so counting them in the total makes a
      # fully installed group read as partial (4 of 6) forever, inviting a
      # pointless re-run. Report them separately instead of hiding them.
      total=0 have=0 bundled=0
      for s in "${gskills[@]}"; do
        [ -n "$s" ] || continue
        if is_bundle "$s"; then bundled=$((bundled+1)); continue; fi
        total=$((total+1))
        if [ "$(status_of "$s")" = "installed" ]; then have=$((have+1)); fi
      done
      via=""
      if [ "$bundled" -gt 0 ]; then via=" (+$bundled via marketplace)"; fi
      printf '  %-10s %2s skills %3s installed%s\n' "$g" "$total" "$have" "$via"
    done
  fi
  exit 0
fi

# Resolve the working set
if [ "$ALL" -eq 1 ]; then
  TARGETS=("${AVAILABLE[@]}")
elif [ "${#GROUP_ARGS[@]}" -gt 0 ] || [ "${#SELECTED[@]}" -gt 0 ]; then
  TARGETS=()
  for g in "${GROUP_ARGS[@]:-}"; do
    [ -n "$g" ] || continue
    # An unknown group must be loud: installing nothing would look like success.
    [ -n "${GROUP_SKILLS[$g]+x}" ] ||
      die "no group '$g' for tree '$TREE' — $(groups_available)"
    while read -r s; do
      [ -n "$s" ] || continue
      [ -d "$SRC/$s" ] || die "group '$g' lists a skill missing from $TREE/: $s"
      TARGETS+=("$s")
    done <<< "${GROUP_SKILLS[$g]}"
  done
  for s in "${SELECTED[@]:-}"; do
    [ -n "$s" ] || continue
    [ -d "$SRC/$s" ] || die "no such skill in $TREE/: $s"
    TARGETS+=("$s")
  done
  [ "${#TARGETS[@]}" -gt 0 ] || die "nothing to install from those arguments"
  # Groups can overlap each other or a named skill; process each skill once.
  mapfile -t TARGETS < <(printf '%s\n' "${TARGETS[@]}" | awk '!seen[$0]++')
else
  die "name at least one skill, or pass --all, --group (try --list)"
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
