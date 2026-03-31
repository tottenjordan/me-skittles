# me-skittles

A collection of skills (slash commands) for [Claude Code](https://claude.ai/code) and [Gemini CLI](https://github.com/google-gemini/gemini-cli). Skills are reusable, prompt-based tools that extend coding agents with specialized capabilities.

## Setup

### Claude Code

Add this repo's `claude/` directory to your Claude Code skills path:

```json
// ~/.claude/settings.json
{
  "skills": ["path/to/me-skittles/claude"]
}
```

Skills are then available as slash commands (e.g., `/adk`, `/writing-skills`).

### Gemini CLI

Add the `gemini/` directory to your Gemini CLI configuration.

## Skills

### ADK & Agents
| Skill | Description |
|-------|-------------|
| `adk` | Build AI agents with Google's Agent Development Kit |
| `adk-dev-guide` | ADK development lifecycle and coding guidelines |
| `adk-eval-guide` | ADK evaluation methodology and metrics |
| `adk-observability-guide` | Cloud Trace, logging, and agent analytics |
| `adk-scaffold` | Scaffold new ADK agent projects |
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
| `gemini_md_author` | Gemini CLI configuration authoring |
| `git_commit_formatter` | Git commit message formatting |
| `license_header_adder` | Add license headers to source files |

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
