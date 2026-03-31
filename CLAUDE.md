# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

**me-skittles** is a collection of Claude Code skills (slash commands) and their Gemini CLI equivalents. Skills are reusable prompt-based tools that extend Claude Code and Gemini CLI with specialized capabilities — from ADK agent development to browser automation to diagram generation.

## Architecture

### Directory Layout

- `claude/` — Skills for Claude Code (SKILL.md-based, loaded via Claude Code's skill system)
- `gemini/` — Parallel skills for Gemini CLI (mostly mirrored from `claude/`, with some Gemini-specific additions like `gemini_md_author`, `git_commit_formatter`, `license_header_adder`)

Most skills exist in both directories. Claude-only skills include: `adk-dev-guide`, `adk-eval-guide`, `adk-observability-guide`, `adk-scaffold`, `frontend-design`, `insights-report`, `inspect-vai-pipes`, `paperbanana`.

### Skill Structure

Each skill is a directory containing:
- `SKILL.md` — Entry point with YAML frontmatter (`name`, `description`) and the skill's instructions
- `references/` — Supporting reference docs loaded on demand
- `scripts/` — Helper scripts (validation, automation)
- `assets/` — Templates, icons, or other static resources
- `examples/` — Example files for the skill

### Skill Frontmatter

```yaml
---
name: skill-name
description: Trigger conditions and when to use this skill
---
```

The `description` field controls when the skill is auto-triggered. Write it as trigger conditions, not a summary.

### Skill Categories

| Category | Skills |
|----------|--------|
| ADK/Agents | `adk`, `adk-dev-guide`, `adk-eval-guide`, `adk-observability-guide`, `adk-scaffold`, `a2a`, `agent-engine`, `agent-development` |
| Development workflow | `writing-skills`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `ralph-wiggum` |
| Testing | `testing-anti-patterns`, `testing-skills-with-subagents`, `condition-based-waiting`, `property-based-testing`, `testing-handbook-skills` |
| Tools/Automation | `browser-use`, `playwright-skill`, `git-worktrees`, `using-git-worktrees`, `inspect-vai-pipes` |
| Diagrams/Frontend | `generate-diagram`, `evaluate-diagram`, `gcp-diagram`, `paperbanana`, `frontend-design` |
| Other | `claude-md-improver`, `gemini-enterprise`, `insights-report` |

### Multi-skill Bundles

`testing-handbook-skills` and `property-based-testing` are plugin-style bundles containing multiple sub-skills under a `skills/` directory, with `.claude-plugin/` configuration and validation scripts.

## Conventions

- Skills follow a TDD-inspired methodology: write pressure-test scenarios, baseline without the skill, write the skill, verify compliance (see `writing-skills/SKILL.md`)
- When creating or modifying skills, use the `/writing-skills` skill for guidance
- Test skills with `/testing-skills-with-subagents` before deployment
- The `playwright-skill` directory contains a Node.js package (`package.json`, `run.js`) — run `npm install` there if working on browser automation
- Validation for testing-handbook skills: `uv run scripts/validate-skills.py` from `claude/testing-handbook-skills/`
