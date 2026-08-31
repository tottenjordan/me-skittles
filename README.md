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
| `subagent-driven-development` | Parallel task execution with subagents |
| `ralph-wiggum` | Iterative trial-and-error development loop |

### Testing
| Skill | Description |
|-------|-------------|
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
| `git-worktrees` | Git worktree lifecycle management |
| `using-git-worktrees` | Create isolated worktrees for feature work |
| `inspect-vai-pipes` | Debug and inspect Vertex AI Pipeline jobs |

### Diagrams & Frontend
| Skill | Description |
|-------|-------------|
| `generate-diagram` | Generate diagrams from descriptions |
| `evaluate-diagram` | Evaluate generated diagrams |
| `gcp-diagram` | GCP-branded architecture diagrams |
| `paperbanana` | Academic diagrams and statistical plots |
| `frontend-design` | Production-grade frontend interfaces |

### Other
| Skill | Description |
|-------|-------------|
| `claude-md-improver` | Audit and improve CLAUDE.md files |
| `gemini-enterprise` | Gemini Enterprise (Discovery Engine) search |
| `insights-report` | Pipeline insights reports |

### Gemini-only Skills
| Skill | Description |
|-------|-------------|
| `gemini-md-author` | Gemini CLI configuration authoring |
| `git-commit-formatter` | Git commit message formatting |
| `license-header-adder` | Add license headers to source files |

## Skill Structure

Each skill is a directory with a `SKILL.md` entry point:

```
skill-name/
├── SKILL.md          # Main instructions (YAML frontmatter + markdown)
├── references/       # Supporting docs
├── scripts/          # Helper scripts
└── assets/           # Templates, icons, etc.
```

## Creating Skills

Use the `/writing-skills` slash command for guidance. Skills follow a TDD-inspired process:

1. Write pressure-test scenarios
2. Baseline agent behavior without the skill
3. Write the skill addressing observed failures
4. Verify compliance, iterate to close loopholes

Test with `/testing-skills-with-subagents` before deployment.
