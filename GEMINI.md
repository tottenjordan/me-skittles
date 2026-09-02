# GEMINI.md

This file provides guidance to Gemini CLI when working with code in this repository.

> **Before writing code or changing the environment, read [CODE_STANDARDS.md](CODE_STANDARDS.md).**
> It is short, and it is binding — tooling, attribution, git conventions, and the rules CI enforces.

## Repository Purpose

**me-skittles** is a collection of agent skills for Gemini CLI and Claude Code. Skills are reusable
prompt-based tools that extend an agent with specialized capabilities — from Google Cloud and
BigQuery work to ADK agent development, browser automation, and diagram generation.

The `gemini/` tree is the larger of the two: **57 skills**, including 29 Google-published skills
covering BigQuery, Dataflow, Composer, and Cloud Storage.

## Architecture

### Directory Layout

- `gemini/` — Skills for Gemini CLI (SKILL.md-based), 57 directories
- `claude/` — Parallel skills for Claude Code, 28 directories

Most skills exist in both trees. Gemini-only skills include `gemini-md-author`, `gemini-md-improver`,
`git-commit-formatter`, `license-header-adder`, and the 29-skill Google Cloud family.

**The two trees are ports of one another, not copies.** Agent-specific terminology, `GEMINI.md` vs
`CLAUDE.md` references, and the `.gemini-plugin/` vs `.claude-plugin/` manifest directories differ
by design. When editing a skill present in both, update both — but adapt the wording rather than
copying it across. Copying undoes the port, and CI fails on it.

### Skill Structure

Each skill is a directory containing:

- `SKILL.md` — Entry point with YAML frontmatter (`name`, `description`) and instructions
- `references/` — Supporting docs loaded on demand
- `scripts/` — Helper scripts
- `assets/` — Templates, icons, static resources
- `examples/` — Example files

### Skill Frontmatter

```yaml
---
name: skill-name
description: Trigger conditions and when to use this skill
---
```

`description` controls when the skill is auto-triggered. Write it as **trigger conditions, not a
summary** — a description phrased as a title never fires.

It is also a standing cost: every skill's description is loaded at the start of **every session**,
whether or not the skill fires. Only bodies are deferred. The `gemini/` tree currently costs roughly
5.2k tokens per session in descriptions alone, which is why they are capped at 500 characters and
bodies at 500 lines.

### Skill Categories

| Category | Skills |
|----------|--------|
| Google Cloud / Data | 29 Google-published skills: `bigquery-*`, `gcp-*`, `dbt-bigquery`, `dataform-bigquery`, `notebook-guidance`, … — start at `gcp-data-pipelines`, which routes to the right one |
| ADK / Agents | `adk`, `a2a`, `agent-engine`, `agent-development` |
| Development workflow | `writing-skills`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `requesting-code-review`, `receiving-code-review`, `finishing-a-development-branch`, `git-worktrees`, `ralph-wiggum`, `managing-python-dependencies` |
| Testing | `test-driven-development`, `testing-anti-patterns`, `testing-skills-with-subagents`, `condition-based-waiting`, `property-based-testing`, `testing-handbook-skills` |
| Tools / Automation | `browser-use`, `playwright-skill`, `gemini-enterprise` |
| Diagrams | `paperbanana`, `gcp-diagram` |
| Meta | `gemini-md-author`, `gemini-md-improver`, `git-commit-formatter`, `license-header-adder`, `skill-repair` |

Installable groupings are defined in [`groups.toml`](groups.toml).

### Multi-skill Bundles

`testing-handbook-skills` and `property-based-testing` are plugin-style bundles holding multiple
sub-skills under `skills/`, with their own validation scripts and a `.gemini-plugin/` manifest
directory.

## Validation

`uv run scripts/validate-skills.py` checks every `SKILL.md` in both trees and runs in CI on every
push and PR. It enforces:

- Frontmatter present, closed, and parsing as YAML
- `name` present, lowercase-kebab, matching its directory
- `description` present, non-trivial, and under 500 characters
- `SKILL.md` under 500 lines (warns at 450) — move detail into `references/` and link it
- No dangling symlinks, no committed build artifacts
- No Claude terminology under `gemini/` — that tree is a port, not a copy
- Plugin bundles using the manifest directory for their tree
- No retired model IDs outside text discussing their retirement
- No frontmatter keys outside the Agent Skills spec, such as `when_to_use` — a harness may well read
  them, but packaging and upload reject them, so they are a portability trap rather than a dead letter
- Helper scripts declaring third-party dependencies via PEP 723, so `uv run <script>` needs no setup
- `groups.toml` parsing, carrying every required key (including `budget_tokens`), and putting each
  skill directory in exactly one group for its tree — so adding a skill without grouping it fails
  the build. Also the flat shape the installer's awk parser needs: no inline arrays, no multi-line
  strings
- Each group staying inside the `budget_tokens` it declares. Descriptions load every session for
  every installed skill, so the binding constraint is the sum per group, not the length of any one
  description. Budgets are declared per group rather than capped globally, because a global ceiling
  would force edits to vendored Google descriptions that the notes already rejected
- The README skill catalogue naming no skill that is absent from both trees (a skill the catalogue
  omits is a warning)
- Each catalogue row sitting under the section for the group that installs it. Headings map to
  groups explicitly in `CATALOGUE_SECTION_GROUPS`; an unmapped section is skipped rather than
  guessed at. This is what catches a skill left listed under **Google Cloud and data** after it
  moved to another group, where `--group gcp` would never install it
- Counts stated in prose agreeing with `scripts/repo_facts.py`, the module that derives every
  number the docs may quote. Only recognised phrases are checked, each bound to one fact, so an
  unattributable number is left alone rather than guessed at

Run it before committing any skill change. It is also the guard against re-syncing upstream content
that reintroduces already-fixed defects — run `--tree gemini` after pulling from any upstream skills
repository.

Prose counts are checked in the four live documents only — `README.md`, `CLAUDE.md`, `GEMINI.md`
and `ATTRIBUTION.md` (the `LIVE_DOCS` constant). [`docs/notes/`](docs/notes/README.md) and
[`docs/plans/`](docs/plans) are point-in-time records: their figures were true when written and are
evidence for a decision, not a description of the repo today. They are deliberately neither
validated nor regenerated.

`uv run scripts/sync-docs.py` regenerates the README's two cost tables from the same module;
`--check` fails without writing, and runs in CI.

## Conventions

- **[CODE_STANDARDS.md](CODE_STANDARDS.md) governs tooling, attribution, and git.** Read it first.
- Skills follow a TDD-inspired methodology: write pressure-test scenarios, baseline without the
  skill, write the skill addressing observed failures, verify compliance (see `writing-skills/`)
- Use the `writing-skills` skill when creating or modifying skills
- Test with `testing-skills-with-subagents` before deployment
- Install skills with `./scripts/install.sh` — `--list`, `--all`, or named skills, with
  `--tree gemini` for this tree
- A new skill must be added to [`groups.toml`](groups.toml), or CI fails — every skill belongs
  to exactly one group per tree, and `./scripts/install.sh --group` installs by group
- The `playwright-skill` directory is a Node.js package — run `npm install` there if working on
  browser automation
- Bundle-specific validation: `uv run scripts/validate-skills.py` from `gemini/testing-handbook-skills/`
- Session notes live in [`docs/notes/`](docs/notes/README.md); plans in [`docs/plans/`](docs/plans)
