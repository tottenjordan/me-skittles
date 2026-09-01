# me-skittles

Agent skills for [Claude Code](https://claude.ai/code) and [Gemini CLI](https://github.com/google-gemini/gemini-cli) — reusable, prompt-based tools that teach a coding agent a specific capability, from ADK agent development to BigQuery analytics to browser automation.

**117 skills** across two trees: `claude/` (28) and `gemini/` (57), of which 24 exist in both. Every skill is validated in CI.

```bash
uv run scripts/validate-skills.py     # 117 skills, 0 errors
```

---

## Contents

- [How skills work](#how-skills-work)
- [Setup](#setup)
- [Skill catalogue](#skill-catalogue)
- [Context cost](#context-cost)
- [Repository layout](#repository-layout)
- [Validation](#validation)
- [Contributing a skill](#contributing-a-skill)
- [Provenance and licence](#provenance-and-licence)

---

## How skills work

A skill is a directory containing a `SKILL.md` with YAML frontmatter:

```yaml
---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---
```

The agent reads every skill's `description` and loads the body only when one matches the task at
hand. Two consequences drive everything in this repo:

1. **`description` is the trigger.** It must read as *when to use this*, not as a summary of what
   the skill does. A description written as a title never fires.
2. **`SKILL.md` is loaded in full.** Detail that belongs in `references/` costs context on every
   single use, which is why the body is capped at 500 lines and deeper material lives in sibling
   files the agent loads on demand.

Both rules are enforced by the validator, not left to reviewer discipline.

---

## Setup

### Claude Code

Claude Code discovers skills **by directory**, not via a config setting. Each skill must live at
`~/.claude/skills/<name>/SKILL.md` (available everywhere) or
`<project>/.claude/skills/<name>/SKILL.md` (that project only).

Install **by group** — a group is a coherent slice of the catalogue, and you only pay context for
what you install:

```bash
./scripts/install.sh --list                          # what's available, and its group
./scripts/install.sh --group agents --group workflow # install by group
./scripts/install.sh --tree gemini --group gcp       # the Google Cloud family
```

Groups are declared in [`groups.toml`](groups.toml) and are per-tree; every skill belongs to exactly
one group for its tree, which CI enforces, so nothing is unreachable via `--group`. See
[Context cost](#context-cost) for what each group costs per session.

Individual names and everything-at-once still work:

```bash
./scripts/install.sh writing-skills adk          # name skills directly; mixes with --group
./scripts/install.sh --all                       # install everything
./scripts/install.sh --all --dry-run             # preview first
./scripts/install.sh --uninstall --group agents  # remove; --all and bare names work too
```

The installer symlinks, so edits in this repo take effect immediately with no reinstall step. It
is idempotent, repairs broken links, and **only ever removes links it created** — a real directory,
or a symlink pointing outside this repo, is reported and left alone. Plugin bundles are skipped
with an explanation.

Skills auto-trigger from their `description`; user-invocable ones are also slash commands
(`/paperbanana`). Run `/doctor` to confirm they loaded.

> `property-based-testing` and `testing-handbook-skills` are **plugin bundles**, not single skills —
> their sub-skills live under `skills/`. Install those through the plugin marketplace mechanism
> rather than symlinking the bundle directory.

### Gemini CLI

Install the equivalents from `gemini/` into your Gemini CLI configuration directory. Consult the
[Gemini CLI docs](https://github.com/google-gemini/gemini-cli) for the current path and layout — its
extension mechanism differs from Claude Code's.

The 29 Google-published skills under `gemini/` came from a Gemini CLI skills bundle and are
Apache-2.0 (see [Provenance](#provenance-and-licence)). 26 of them install as `--group gcp`; the
other three are grouped by topic.

---

## Skill catalogue

### Agents — ADK, A2A, Agent Engine *(both trees)*

| Skill | What it covers |
|---|---|
| `adk` | Building agents with Google's Agent Development Kit — LLM agents, tools, workflow agents, and the 2.x Workflow Runtime |
| `a2a` | Multi-agent systems over the A2A protocol |
| `agent-engine` | Deploying and managing agents on Vertex AI Agent Engine |
| `agent-development` | Authoring agents and subagents: frontmatter, system prompts, triggering conditions |

### Development workflow *(both trees unless noted)*

| Skill | What it covers |
|---|---|
| `writing-plans` | Turning a spec into a step-by-step implementation plan |
| `executing-plans` | Working through a plan with review checkpoints |
| `subagent-driven-development` | Fresh subagent per task, with a two-stage spec-then-quality review |
| `requesting-code-review` | Dispatching a reviewer subagent before merging |
| `receiving-code-review` | Responding to review feedback with rigor rather than agreement |
| `finishing-a-development-branch` | Deciding how to integrate completed work — merge, PR, or clean up |
| `git-worktrees` | The full worktree lifecycle: select a location, verify it's ignored, create, merge, tear down |
| `ralph-wiggum` | An iterative trial-and-error loop for problems that resist planning |
| `modern-python` | Modern Python project setup — uv, ruff, pyproject *(Claude only)* |

### Testing *(both trees)*

| Skill | What it covers |
|---|---|
| `test-driven-development` | Write the failing test first |
| `testing-anti-patterns` | Never test mock behaviour; never add test-only methods to production classes |
| `condition-based-waiting` | Replacing arbitrary timeouts with condition polling in async tests |
| `testing-skills-with-subagents` | RED-GREEN-REFACTOR applied to skills themselves |
| `property-based-testing` | Property-based testing across languages *(bundle)* |
| `testing-handbook-skills` | 16 security-testing skills — fuzzing, sanitizers, static analysis *(bundle)* |

The `testing-handbook-skills` bundle covers `libfuzzer`, `aflpp`, `libafl`, `atheris`, `cargo-fuzz`,
`ruzzy`, `ossfuzz`, `harness-writing`, `fuzzing-dictionary`, `fuzzing-obstacles`,
`coverage-analysis`, `address-sanitizer`, `semgrep`, `codeql`, `wycheproof`, and
`constant-time-testing`, plus `testing-handbook-generator`, which produces new skills in the same
shape from handbook source material.

### Diagrams *(both trees)*

| Skill | What it covers |
|---|---|
| `paperbanana` | Diagrams, statistical plots, batch figures, and VLM-as-judge evaluation via the PaperBanana MCP pipeline |
| `gcp-diagram` | GCP-branded architecture diagrams via Vertex AI image generation, with an official icon overlay script |

These two use **different toolchains** and cross-link rather than compete: PaperBanana runs a
visualizer↔critic MCP pipeline; `gcp-diagram` calls Vertex AI directly and composites official
Google Cloud icon assets.

For UI design guidance, install the official `frontend-design` plugin from the Claude Code
marketplace — this repo previously carried a divergent, older copy, since removed.

### Tools and automation *(both trees unless noted)*

| Skill | What it covers |
|---|---|
| `browser-use` | AI-driven browser automation via the browser-use library |
| `playwright-skill` | Scripted browser automation with Playwright, including dev-server auto-detection |
| `gemini-enterprise` | Gemini Enterprise / Discovery Engine search and conversational AI |
| `inspect-vai-pipes` | Debugging Vertex AI Pipeline jobs — worker logs, 429s, stragglers *(Claude only)* |
| `insights-report` | Building pipeline insights reports *(Claude only)* |

### Meta — authoring skills and agent config

| Skill | Tree | What it covers |
|---|---|---|
| `writing-skills` | both | TDD-based methodology for creating skills |
| `claude-md-improver` | Claude | Auditing and improving `CLAUDE.md` files |
| `gemini-md-improver` | Gemini | Auditing and improving `GEMINI.md` files |
| `gemini-md-author` | Gemini | Authoring Gemini CLI configuration |
| `git-commit-formatter` | Gemini | Commit message formatting |
| `license-header-adder` | Gemini | Adding licence headers to source files |
| `skill-repair` | Gemini | Fixing and reinstalling skills that failed to install |

### Google Cloud and data *(Gemini only)*

Google-published, Apache-2.0. Start at **`gcp-data-pipelines`**, a router that directs you to the
right tool for a given job.

`./scripts/install.sh --tree gemini --group gcp` installs the 26 below. Three other Google-published
skills are grouped by what they do rather than who wrote them: `managing-python-dependencies` sits
in `workflow`, `ml-best-practices` in `data`, and `skill-repair` in `meta`.

| Area | Skills |
|---|---|
| BigQuery | `bigquery-sql`, `bigquery-graph`, `bigquery-ai-ml`, `bigquery-bigframes`, `bigquery-data-transfer-service` |
| Pipelines and orchestration | `gcp-data-pipelines` (router), `gcp-pipeline-orchestration`, `gcp-pipeline-resource-provisioning`, `gcp-dataflow`, `gcp-spark`, `dbt-bigquery`, `dataform-bigquery` |
| Managed Airflow / Composer | `gcp-managed-airflow-dag-authoring`, `gcp-managed-airflow-migrations`, `gcp-managed-airflow-recommendations`, `gcp-composer-troubleshooting` |
| Storage and discovery | `google-cloud-storage-basics`, `gcs-security-assessment`, `discovering-gcp-data-assets`, `federate-lakehouse-catalog` |
| Data quality and apps | `data-autocleaning`, `building-data-apps`, `notebook-guidance` |
| Governance and ops | `accidental-data-loss-prevention`, `enforcing-resource-attribution`, `gcloud-auth-verification` |

---

## Context cost

Every skill's `description` is loaded into context at the start of **every session**, whether or not
the skill fires. Bodies are loaded only on trigger. So the catalogue has a fixed cost that grows
with its size:

| | Skills | Description budget | When one fires |
|---|---|---|---|
| `claude/` | 26 top-level | ~1.8k tokens per session | +2.4k tokens median |
| `gemini/` | 55 top-level | ~5.2k tokens per session | +2.0k tokens median |

### What each group costs

Installing by group is how you pay for a slice rather than a whole tree. Standing cost per session,
by group:

| Group | `claude/` | `gemini/` |
|---|---|---|
| `agents` | 4 skills · ~390 tokens | 4 skills · ~380 tokens |
| `workflow` | 9 skills · ~470 tokens | 9 skills · ~510 tokens |
| `testing` | 6 skills · ~190 tokens | 6 skills · ~190 tokens |
| `diagrams` | 2 skills · ~240 tokens | 2 skills · ~240 tokens |
| `tools` | 5 skills · ~430 tokens | 3 skills · ~310 tokens |
| `meta` | 2 skills · ~110 tokens | 6 skills · ~290 tokens |
| `data` | — | 1 skill · ~140 tokens |
| `gcp` | — | 26 skills · ~3,180 tokens |
| **whole tree** | 28 skills · ~1.8k | 57 skills · ~5.2k |

**Method**, so the numbers can be re-derived rather than trusted: for each group in `groups.toml`,
sum the `description` field from every member skill's `SKILL.md` frontmatter and divide the
character count by 4. They move whenever a description does. The counts here are group membership,
which is why they run two ahead of the top-level counts above: the `testing` groups list six skills
but contribute four descriptions, because `property-based-testing` and `testing-handbook-skills` are
plugin bundles with no top-level `SKILL.md` and so cost nothing at session start.

`gcp` alone is **61% of the Gemini tree's standing cost** — the argument for installing it only when
the work is Google Cloud work. On the Claude side, `--group agents --group workflow` costs ~860
tokens against ~1.8k for `--all`.

Two practical consequences:

- **Install the groups you use.** `./scripts/install.sh --list` shows each skill's group and how much
  of each group is installed; `--group` then takes whole slices. Installing the whole Gemini tree
  costs ~5.2k tokens before you type anything.
- **Keep descriptions tight.** The validator warns above 500 characters. Ten skills currently exceed
  it, all vendored from Google — left at upstream's wording deliberately, since editing them
  complicates re-sync.

Bodies are capped at 500 lines for the same reason: `SKILL.md` loads in full, so detail belongs in
`references/`, which loads only when the agent follows the link.

## Repository layout

```
claude/                     28 skills for Claude Code
gemini/                     57 skills for Gemini CLI
groups.toml                 installable groups, per tree — drives `install.sh --group`
scripts/validate-skills.py  repo-wide validator (PEP 723; run with uv)
docs/plans/                 implementation plans for larger changes
.github/workflows/          CI
ATTRIBUTION.md              upstream source and licence per vendored skill
```

A skill directory:

```
skill-name/
├── SKILL.md          # frontmatter + body, under 500 lines
├── references/       # detail loaded on demand, one level deep
├── scripts/          # helper scripts, dependencies declared inline
├── examples/         # worked examples
└── assets/           # templates, icons
```

### The two trees

`gemini/` is a **port of** `claude/`, not a copy. Claude-specific terminology, `CLAUDE.md`
references, and `.claude-plugin/` manifests are replaced with their Gemini equivalents (`GEMINI.md`,
`.gemini-plugin/`). The validator fails on any Claude terminology under `gemini/` — with a small,
reasoned allowlist for legitimate third-party references, such as documenting Claude Desktop as an
MCP client.

**When editing a skill that exists in both trees, update both.** Never `cp` one over the other; that
undoes the port.

---

## Validation

```bash
uv run scripts/validate-skills.py              # everything
uv run scripts/validate-skills.py --tree gemini
uv run scripts/validate-skills.py --json       # machine-readable
```

Runs in CI on every push and pull request, alongside the bundle-specific validators for
`testing-handbook-skills` in both trees.

**Errors** — these fail the build:

| Check | Why |
|---|---|
| Frontmatter present, closed, valid YAML | A malformed header means the skill silently never loads |
| `name` lowercase-kebab and matching its directory | Required by the loader |
| `description` present and non-trivial | It's the sole trigger signal |
| `SKILL.md` under 500 lines | The body loads in full; detail belongs in `references/` |
| No retired model IDs | A dead model ID sends callers to an endpoint that 404s |
| No Claude terminology under `gemini/` | That tree is a port, not a copy |
| No dangling symlinks, no committed build artifacts | Both have shipped broken skills before |
| Correct plugin manifest per tree | `.claude-plugin/` vs `.gemini-plugin/` |
| `groups.toml` well-formed, complete, and disjoint | Every skill in exactly one group per tree, or `--group` and `--list` quietly omit it. The installer parses it with `scripts/parse-groups.awk`, so this runs that same file and requires its output to match `tomllib`'s — legal TOML the installer would read differently fails here rather than silently there |
| The catalogue names no skill absent from both trees | Readers install by name; a dangling row sends them after something that was deleted |

**Warnings** — surfaced, don't fail:

- `SKILL.md` over 450 lines, approaching the limit
- A `description` over 500 characters — it is paid for on every session
- Helper scripts importing undeclared third-party packages
- Frontmatter keys the harness ignores (`when_to_use`, `tools`)
- Relative links that don't resolve
- A skill that exists but the catalogue never mentions — undiscoverable, but nothing breaks
- Stale entries in the Gemini-purity allowlist, so exemptions don't outlive their reason

Run it before committing. It is also the guard against re-syncing upstream content that reintroduces
already-fixed defects — run `--tree gemini` after pulling from any upstream Gemini skills repo.

---

## Contributing a skill

1. **Write the description first**, as trigger conditions. `Use when <situation>` beats a summary.
2. **Keep `SKILL.md` under 500 lines.** Move detail into `references/` and link it — an unlinked
   reference file is invisible to the agent.
3. **Declare script dependencies inline** so `uv run script.py` works with no setup:
   ```python
   # /// script
   # requires-python = ">=3.11"
   # dependencies = ["pillow>=10.0"]
   # ///
   ```
4. **Add it to both trees** if it isn't tree-specific, porting rather than copying.
5. **Run the validator**, then use `/writing-skills` for methodology and
   `/testing-skills-with-subagents` to pressure-test before deployment.

Full authoring guidance lives in `claude/writing-skills/`, including a vendored copy of Anthropic's
skill-authoring best practices.

---

## Provenance and licence

Apache-2.0 — see [LICENSE](LICENSE).

This repo vendors substantial third-party content. [ATTRIBUTION.md](ATTRIBUTION.md) records the
upstream source, author, and licence for each piece:

| Source | Content |
|---|---|
| Google | 29 Apache-2.0 Google Cloud and BigQuery skills under `gemini/` |
| Trail of Bits | `testing-handbook-skills` (Paweł Płatek), `property-based-testing` (Henrik Brodin) |
| Anthropic | Skill-authoring best practices vendored into `writing-skills` |
| [jswortz/my-skills](https://github.com/jswortz/my-skills) | The Gemini ports of the shared skills |

The Trail of Bits skills were **reorganised** for progressive disclosure — content relocated into
`references/`, not edited. A future re-sync should re-apply that split rather than overwrite it.
