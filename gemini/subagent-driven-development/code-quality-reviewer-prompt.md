# Code Quality Reviewer Prompt

Use ONLY after spec compliance is ✅. Dispatch: Agent tool, `subagent_type: "general-purpose"`
(READ-ONLY — report only, never edit), description "Review code quality for Task N".
This mirrors `requesting-code-review`'s `code-reviewer.md` template.

---
Verify the **Task N** implementation is well-built: clean, tested, maintainable.

## Inputs
- WHAT_WAS_IMPLEMENTED: <from the implementer's report>
- PLAN_OR_REQUIREMENTS: <task + plan reference>
- BASE_SHA: <commit before the task>
- HEAD_SHA: <current commit>
- DESCRIPTION: <one-line task summary>

## Review the diff (BASE_SHA..HEAD_SHA) for
- Naming clarity and accuracy
- Structure / duplication / magic numbers
- Test coverage and whether tests assert real behavior
- Adherence to existing codebase patterns and `CODE_STANDARDS.md`

## Output
- Strengths
- Issues, grouped Critical / Important / Minor (with `file:line`)
- Assessment: ✅ ready, or ❌ changes required
