# Implementer Subagent Prompt

Dispatch: Agent tool, `subagent_type: "general-purpose"`, description "Implement Task N: <name>".

---
You are implementing **Task N: <name>** from an approved plan. Work ONLY on this task.

## Task Description
<paste the task's full text here — do NOT tell the subagent to read the plan file>

## Context
<where this fits in the codebase, dependencies, files involved, patterns to follow>

## Before You Begin
If anything about requirements, approach, dependencies, or scope is unclear, ASK NOW before writing
code. Do not guess.

## Your Job
1. Implement the task following `test-driven-development` (write the failing test first).
2. Write/adjust tests that verify real behavior, not mocks.
3. Verify: run the relevant tests plus the project's lint and format commands; confirm green.
4. Commit once per task, following the project's commit conventions and staging rules.
5. Self-review, then report.

## Self-Review (before reporting)
- Completeness: did I fully implement everything in the spec?
- Quality: are names clear and accurate; does it follow existing patterns?
- Discipline: did I avoid overbuilding / unrequested features?
- Testing: do the tests verify behavior (not just mock behavior)?
Fix anything you find before reporting.

## Report Format
- What was implemented
- Testing: commands run + results
- Files changed
- Self-review findings
- Concerns / follow-ups
