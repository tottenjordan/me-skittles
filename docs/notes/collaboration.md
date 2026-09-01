# Collaboration conventions

How work gets done in this repository — the conventions that are not derivable from the code.

Binding rules live in [CODE_STANDARDS.md](../../CODE_STANDARDS.md); this note records the *reasoning*
and the history behind them.

Related: [tooling-gotchas.md](tooling-gotchas.md) · [decisions-not-taken.md](decisions-not-taken.md)

---

## Attribution: why it kept coming back

Commits and PR descriptions were repeatedly getting `Co-Authored-By: Claude …` trailers and
`🤖 Generated with Claude Code` footers, against the author's wishes.

**This was not carelessness, and understanding why matters.** Claude Code's own default instructions
direct the agent to append that trailer to every commit. Absent an explicit override, it recurs every
session — which is why writing the rule into a document alone was never going to hold: it would be
asking the agent to remember to break a standing instruction, every time.

Three layers now address it, and the order matters:

1. **Source** — `.claude/settings.json` sets `attribution.commit` and `attribution.pr` to `""`.
   Stops it being generated. Only covers Claude Code, and only from the next session onward.
2. **CI, commit messages** — fails any PR whose commits carry the trailer.
3. **CI, PR description** — fails any PR whose body carries the footer. Separate check, because the
   body is not in git.

**The CI layer is the one that actually holds**, because it is agent-agnostic: it inspects the
result, not the producer. That covers Gemini CLI, other tooling, and humans, none of which the
settings layer can reach.

Historical note: 16 commits already merged into `main` still carry the trailer. Rewriting shared
history to remove it was considered and declined — see
[decisions-not-taken.md](decisions-not-taken.md).

## Commits and PRs

- One commit per logical change; imperative subject; body explains **why**.
- Stage deliberately — read `git status` before `git add`.
- **Never push unless asked.** Pushing is the author's call, not the agent's.
- Rewriting unmerged branch history is fine (`--force-with-lease`); rewriting `main` is not.

## How larger work is structured

Plans go in [`docs/plans/`](../plans) as dated Markdown, written before implementation and committed
so the reasoning survives the session. Approved plans are executed **task by task**, each with:

1. A fresh implementer working only from the task text pasted inline — never pointed at the plan
   file, which invites wandering into adjacent tasks.
2. A **spec-compliance** review: did it build what was asked, nothing more?
3. A **code-quality** review, only after spec passes.

Reviewers are read-only and are told explicitly not to trust the implementer's report. This is not
ceremony — it has caught real problems, including a subagent that confidently reported `CLAUDE.md`
was stale when the content it described had been removed several merges earlier. **Verify subagent
claims against the tree before acting on them.**

Standing constraints have to be restated in *every* dispatch — tooling, commit conventions, what may
be staged, whether pushing is allowed. Subagents start with no context and will not infer them.

## Session notes

These notes exist for things that outlive a conversation and are **not recoverable** from the repo,
git history, `CLAUDE.md`, or existing docs. Before adding one:

- Check for an existing note on the topic and update it rather than creating a near-duplicate.
- Delete notes that turn out to be wrong or have gone stale.
- A note reflects what was true when written — if it names a file or flag, re-verify before acting.

Keep [README.md](README.md) under 200 lines: one line per note, with a hook.
