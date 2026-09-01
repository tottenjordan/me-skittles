# Flatten groups.toml into tab-separated tree/group/skill triples.
#
# This file is the single definition of how groups.toml is read. Two callers run
# it:
#
#   scripts/install.sh          so the installer needs no TOML library
#   scripts/validate-skills.py  which runs this exact file and diffs its output
#                               against tomllib's
#
# That diff is what CI enforces. Not a hand-copied list of shape rules that can
# drift from this program, but agreement between this parser and a real TOML
# parser: if any legal-TOML construct makes this program see something
# different, the build fails and names the entries the two disagree about.
#
# The subset understood here: one [[group]] table per (tree, name), with `name`
# and `tree` as double-quoted strings, and `skills = [` opening an array with one
# double-quoted name per line until a line beginning with `]`. Every other line
# is ignored.

function qval(line) {
  return match(line, /"[^"]*"/) ? substr(line, RSTART + 1, RLENGTH - 2) : ""
}

/^[[:space:]]*\[\[group\]\]/       { name = ""; tree = ""; in_skills = 0; next }
/^[[:space:]]*name[[:space:]]*=/   { name = qval($0); next }
/^[[:space:]]*tree[[:space:]]*=/   { tree = qval($0); next }
/^[[:space:]]*skills[[:space:]]*=/ { in_skills = 1; next }
!in_skills                         { next }
/^[[:space:]]*\]/                  { in_skills = 0; next }
{
  skill = qval($0)
  if (tree != "" && name != "" && skill != "")
    printf "%s\t%s\t%s\n", tree, name, skill
}
