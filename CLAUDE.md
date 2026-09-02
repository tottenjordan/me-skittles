# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Before writing code or changing the environment, read [CODE_STANDARDS.md](CODE_STANDARDS.md).**
> It is short, and it is binding — tooling, attribution, git conventions, and the rules CI enforces.

## Repository Purpose

**me-skittles** is a collection of Claude Code skills (slash commands) and their Gemini CLI equivalents. Skills are reusable prompt-based tools that extend Claude Code and Gemini CLI with specialized capabilities — from ADK agent development to browser automation to diagram generation.

## Architecture

### Directory Layout

- `claude/` — Skills for Claude Code (SKILL.md-based, loaded via Claude Code's skill system)
- `gemini/` — Parallel skills for Gemini CLI, ported (not copied) from `claude/`: Claude-specific
  terminology, `CLAUDE.md` references, and `.claude-plugin/` manifests are replaced with their
  Gemini equivalents (`GEMINI.md`, `.gemini-plugin/`). Plus Gemini-specific additions:
  `gemini-md-author`, `gemini-md-improver`, `git-commit-formatter`, `license-header-adder`.

Most skills exist in both directories. Claude-only skills: `claude-md-improver`, `insights-report`,
`inspect-vai-pipes`, `modern-python`.

When editing a skill that exists in both trees, update both. The Gemini copy is a port, not a
mirror — do not copy Claude-specific wording across.

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
| ADK/Agents | `adk`, `a2a`, `agent-engine`, `agent-development` |
| Development workflow | `writing-skills`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `requesting-code-review`, `receiving-code-review`, `finishing-a-development-branch`, `ralph-wiggum`, `modern-python` (Claude) |
| Testing | `test-driven-development`, `testing-anti-patterns`, `testing-skills-with-subagents`, `condition-based-waiting`, `property-based-testing`, `testing-handbook-skills` |
| Tools/Automation | `browser-use`, `playwright-skill`, `git-worktrees`, `inspect-vai-pipes` |
| Diagrams | `paperbanana`, `gcp-diagram` |
| Google Cloud/Data (Gemini only) | 29 Google-published skills: `bigquery-*`, `gcp-*`, `dbt-bigquery`, `dataform-bigquery`, `notebook-guidance`, … — routed from `gcp-data-pipelines` |
| Other | `claude-md-improver` (Claude), `gemini-md-improver` (Gemini), `gemini-enterprise`, `insights-report` |

### Multi-skill Bundles

`testing-handbook-skills` and `property-based-testing` are plugin-style bundles containing multiple sub-skills under a `skills/` directory, with validation scripts and a manifest directory matching their tree — `.claude-plugin/` under `claude/`, `.gemini-plugin/` under `gemini/`.

## Validation

`uv run scripts/validate-skills.py` checks every `SKILL.md` in both trees and runs in CI on every push and PR. It enforces:

- Frontmatter present, closed, and parsing as YAML
- `name` present, lowercase-kebab, and matching its directory
- `description` present and non-trivial (skills auto-trigger from it)
- No dangling symlinks or committed build artifacts
- No Claude terminology under `gemini/` — that tree is a port, not a copy
- Plugin bundles using the manifest directory for their tree
- `SKILL.md` under 500 lines (warns at 450) — the standard documented in
  `writing-skills/anthropic-best-practices.md`; move detail into `references/` and link it
- No retired model IDs (see `DEPRECATED_MODELS`) outside deprecation notes
- No frontmatter keys outside the Agent Skills spec, e.g. `when_to_use` — Claude Code reads them,
  but packaging and upload reject them, so they are a portability trap rather than a dead letter
- Helper scripts declare third-party dependencies via PEP 723 inline metadata, so `uv run <script>`
  works with no setup (imports guarded by `except ImportError` are exempt)
- `description` under 500 characters — descriptions load every session, so length is a standing
  context cost, not a per-use one
- `groups.toml` parses, carries every required key (`name`, `tree`, `description`, `budget_tokens`,
  `skills`), and places each skill directory in exactly one group for its tree — adding a skill
  without grouping it fails the build. It also keeps the file in the flat shape
  `scripts/install.sh`'s awk parser needs: no inline arrays, no multi-line strings
- Each group stays inside the `budget_tokens` it declares. Descriptions are a per-session cost that
  scales with what you install, and Claude Code meters the always-loaded listing at 1% of the
  context window — on overflow it drops descriptions starting with the *least-invoked* skills, so
  an over-large tree silently strips trigger keywords instead of failing. `--group` is the unit
  people install, so it is the unit budgeted. Budgets are declared per group rather than capped
  globally: `gemini/gcp` is legitimately large, and a global ceiling would force edits to vendored
  Google descriptions that [`docs/notes/decisions-not-taken.md`](docs/notes/decisions-not-taken.md)
  rejected. A budget far above actual cost warns, so it cannot be set high enough to never bind
- The README skill catalogue names no skill absent from both trees (a skill the catalogue omits is
  a warning). Only table cells that are pure name lists count as catalogue entries, so prose — such
  as the pointer to the official `frontend-design` plugin — is not scanned
- Each catalogue row sits under the section for the group that installs it. Headings map to groups
  explicitly in `CATALOGUE_SECTION_GROUPS`; an unmapped section is skipped rather than guessed at.
  This is the check that would have caught `ml-best-practices` still listed under **Google Cloud
  and data** after it moved to the `data` group — a table that was internally consistent and still
  told the reader to run a `--group gcp` that would never install it
- Counts stated in prose agree with `scripts/repo_facts.py`, which derives every number the docs
  are allowed to quote. Only recognised phrases are checked, each bound to one fact, so an
  unattributable number is left alone rather than guessed at

Prose counts are checked only in the four live documents — `README.md`, `CLAUDE.md`, `GEMINI.md`
and `ATTRIBUTION.md` (the `LIVE_DOCS` constant). [`docs/notes/`](docs/notes/README.md) and
[`docs/plans/`](docs/plans) are point-in-time records: their numbers were true when written, and
are evidence for a decision rather than a description of the repo today. They are deliberately
neither validated nor regenerated.

`uv run scripts/sync-docs.py` regenerates the README's two cost tables from the same module;
`--check` fails without writing, and runs in CI.

## Installing skills locally

`./scripts/install.sh --list | --all | <names> | --uninstall | --dry-run`, with `--tree gemini` for
the other tree. Symlinks rather than copies, and never touches a path it did not create.

Run it before committing any skill change. It is the guard against re-syncing
upstream content that reintroduces fixed defects — run `--tree gemini` after
pulling from an upstream Gemini skills repo.

## Conventions

- **[CODE_STANDARDS.md](CODE_STANDARDS.md) governs tooling, attribution, and git.** Read it first.
- Install skills with `./scripts/install.sh` — `--list`, `--all`, or named skills
- A new skill must be added to [`groups.toml`](groups.toml), or CI fails — every skill belongs
  to exactly one group per tree, and `./scripts/install.sh --group` installs by group
- Session notes live in [`docs/notes/`](docs/notes/README.md); plans in [`docs/plans/`](docs/plans)
- Skills follow a TDD-inspired methodology: write pressure-test scenarios, baseline without the skill, write the skill, verify compliance (see `writing-skills/SKILL.md`)
- When creating or modifying skills, use the `/writing-skills` skill for guidance
- Test skills with `/testing-skills-with-subagents` before deployment
- The `playwright-skill` directory contains a Node.js package (`package.json`, `run.js`) — run `npm install` there if working on browser automation
- Repo-wide validation: `uv run scripts/validate-skills.py` (see Validation above) — run before committing
- Bundle-specific validation for testing-handbook skills: `uv run scripts/validate-skills.py` from `claude/testing-handbook-skills/` (required per-type sections, Hugo shortcodes); runs in CI for both trees
