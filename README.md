# me-skittles

A collection of skills (slash commands) for [Claude Code](https://claude.ai/code) and [Gemini CLI](https://github.com/google-gemini/gemini-cli). Skills are reusable, prompt-based tools that extend coding agents with specialized capabilities.

## Setup

### Claude Code

Claude Code discovers skills by directory, not by a config path setting. Each skill must live at
`~/.claude/skills/<skill-name>/SKILL.md` (available everywhere) or
`<project>/.claude/skills/<skill-name>/SKILL.md` (that project only).

Symlink the skills you want:

```bash
REPO="$(pwd)"          # run from the repo root
mkdir -p ~/.claude/skills

# One skill
ln -s "$REPO/claude/writing-skills" ~/.claude/skills/writing-skills

# All of them
for d in "$REPO"/claude/*/; do
  ln -s "$d" ~/.claude/skills/"$(basename "$d")"
done
```

Skills auto-trigger from their `description`, and user-invocable ones are also available as slash
commands (e.g. `/writing-skills`). Run `/doctor` to confirm they loaded.

Note that `property-based-testing` and `testing-handbook-skills` are plugin bundles, not single
skills — their sub-skills live under `skills/`. Install those via the plugin marketplace mechanism
rather than symlinking the bundle directory.

### Gemini CLI

Install the equivalents from `gemini/` into your Gemini CLI configuration directory. Consult the
[Gemini CLI docs](https://github.com/google-gemini/gemini-cli) for the current path and layout, as
its extension mechanism differs from Claude Code's.

## Skills

### ADK & Agents
| Skill | Description |
|-------|-------------|
| `adk` | Build AI agents with Google's Agent Development Kit |
| `a2a` | Multi-agent systems using A2A protocol |
| `agent-engine` | Deploy agents on Vertex AI Agent Engine |
| `agent-development` | Claude Code agent/subagent authoring |

### Development Workflow
| Skill | Description |
|-------|-------------|
| `writing-skills` | TDD-based methodology for creating new skills |
| `writing-plans` | Design implementation plans before coding |
| `executing-plans` | Execute plans with review checkpoints |
| `subagent-driven-development` | Fresh subagent per task with two-stage review |
| `requesting-code-review` | Dispatch a reviewer subagent before merging |
| `receiving-code-review` | Respond to review feedback with rigor, not agreement |
| `finishing-a-development-branch` | Merge, PR, or clean up completed work |
| `ralph-wiggum` | Iterative trial-and-error development loop |
| `modern-python` | Modern Python project setup (uv, ruff, pyproject) — Claude only |

### Testing
| Skill | Description |
|-------|-------------|
| `test-driven-development` | Write the failing test first |
| `testing-anti-patterns` | Avoid common testing mistakes (mock abuse, test-only methods) |
| `testing-skills-with-subagents` | Red-green-refactor for validating skills |
| `condition-based-waiting` | Replace arbitrary timeouts with condition polling |
| `property-based-testing` | Property-based testing patterns and strategies |
| `testing-handbook-skills` | Generated skills from Trail of Bits testing handbook |

### Tools & Automation
| Skill | Description |
|-------|-------------|
| `browser-use` | AI-powered browser automation |
| `playwright-skill` | Browser automation with Playwright |
| `git-worktrees` | Full worktree lifecycle: create, verify, merge, tear down |
| `inspect-vai-pipes` | Debug and inspect Vertex AI Pipeline jobs |

### Diagrams & Frontend
| Skill | Description |
|-------|-------------|
| `paperbanana` | Diagrams, plots, batch figures, and evaluation via the PaperBanana MCP pipeline |
| `gcp-diagram` | GCP-branded architecture diagrams via Vertex AI + official icon overlay |
| `frontend-design` | Production-grade frontend interfaces |

### Other
| Skill | Description |
|-------|-------------|
| `claude-md-improver` | Audit and improve CLAUDE.md files (Claude only) |
| `gemini-enterprise` | Gemini Enterprise (Discovery Engine) search |
| `insights-report` | Pipeline insights reports |

### Gemini-only Skills
| Skill | Description |
|-------|-------------|
| `gemini-md-author` | Gemini CLI configuration authoring |
| `gemini-md-improver` | Audit and improve GEMINI.md files |
| `git-commit-formatter` | Git commit message formatting |
| `license-header-adder` | Add license headers to source files |

### Google Cloud & Data (Gemini only)

29 Google-published skills covering BigQuery, data pipelines, and GCP platform work. Apache-2.0;
see [ATTRIBUTION.md](ATTRIBUTION.md). Start at `gcp-data-pipelines`, which routes to the right
tool for a given job.

| Area | Skills |
|------|--------|
| BigQuery | `bigquery-sql`, `bigquery-graph`, `bigquery-ai-ml`, `bigquery-bigframes`, `bigquery-data-transfer-service` |
| Pipelines & orchestration | `gcp-data-pipelines` (router), `gcp-pipeline-orchestration`, `gcp-pipeline-resource-provisioning`, `gcp-dataflow`, `gcp-spark`, `dbt-bigquery`, `dataform-bigquery` |
| Managed Airflow / Composer | `gcp-managed-airflow-dag-authoring`, `gcp-managed-airflow-migrations`, `gcp-managed-airflow-recommendations`, `gcp-composer-troubleshooting` |
| Storage & discovery | `google-cloud-storage-basics`, `gcs-security-assessment`, `discovering-gcp-data-assets`, `federate-lakehouse-catalog` |
| Data quality & apps | `data-autocleaning`, `building-data-apps`, `notebook-guidance`, `ml-best-practices` |
| Governance & ops | `accidental-data-loss-prevention`, `enforcing-resource-attribution`, `gcloud-auth-verification`, `managing-python-dependencies`, `skill-repair` |

## Skill Structure

Each skill is a directory with a `SKILL.md` entry point:

```
skill-name/
├── SKILL.md          # Main instructions (YAML frontmatter + markdown)
├── references/       # Supporting docs
├── scripts/          # Helper scripts
└── assets/           # Templates, icons, etc.
```

## Validation

```bash
uv run scripts/validate-skills.py           # all skills, both trees
uv run scripts/validate-skills.py --tree gemini
uv run scripts/validate-skills.py --json    # machine-readable
```

Checks that every `SKILL.md` has valid frontmatter (`name` lowercase-kebab and matching its
directory, `description` present so the skill can auto-trigger), that no symlinks dangle, that no
build artifacts are committed, and that `gemini/` stays free of Claude terminology. Runs in CI on
every push and pull request.

## Creating Skills

Use the `/writing-skills` slash command for guidance. Skills follow a TDD-inspired process:

1. Write pressure-test scenarios
2. Baseline agent behavior without the skill
3. Write the skill addressing observed failures
4. Verify compliance, iterate to close loopholes

Test with `/testing-skills-with-subagents` before deployment.

## License

Apache-2.0 — see [LICENSE](LICENSE). This repo vendors skills from Google, Trail of Bits,
Anthropic, and others; per-skill provenance and upstream licenses are recorded in
[ATTRIBUTION.md](ATTRIBUTION.md).
