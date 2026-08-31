# Attribution

This repository is licensed under Apache-2.0 (see [LICENSE](LICENSE)). Much of its content is
vendored from upstream projects, listed below with their original authors and licenses. Upstream
license terms govern the vendored material; where an upstream file declares its own license in
frontmatter, that declaration is authoritative for that file.

## Google — Google Cloud & Data skills (Gemini tree)

29 skills under `gemini/`, each declaring `license: Apache-2.0` and `publisher: google` in its own
frontmatter:

`accidental-data-loss-prevention`, `bigquery-ai-ml`, `bigquery-bigframes`,
`bigquery-data-transfer-service`, `bigquery-graph`, `bigquery-sql`, `building-data-apps`,
`data-autocleaning`, `dataform-bigquery`, `dbt-bigquery`, `discovering-gcp-data-assets`,
`enforcing-resource-attribution`, `federate-lakehouse-catalog`, `gcloud-auth-verification`,
`gcp-composer-troubleshooting`, `gcp-data-pipelines`, `gcp-dataflow`,
`gcp-managed-airflow-dag-authoring`, `gcp-managed-airflow-migrations`,
`gcp-managed-airflow-recommendations`, `gcp-pipeline-orchestration`,
`gcp-pipeline-resource-provisioning`, `gcp-spark`, `gcs-security-assessment`,
`google-cloud-storage-basics`, `managing-python-dependencies`, `ml-best-practices`,
`notebook-guidance`, `skill-repair`

- **Author:** Google
- **License:** Apache-2.0
- **Imported from:** a local Gemini CLI skills installation (`~/.gemini/skills/`)

## Trail of Bits — testing and security skills

| Path | Upstream author | License |
|---|---|---|
| `{claude,gemini}/testing-handbook-skills/` | Paweł Płatek, [Trail of Bits](https://github.com/trailofbits) | See upstream |
| `{claude,gemini}/property-based-testing/` | Henrik Brodin, [Trail of Bits](https://github.com/trailofbits) | See upstream |

Derived from the [Trail of Bits Application Security Testing Handbook](https://appsec.guide).
Author attribution is recorded in each bundle's `plugin.json`.

**Local modification — reorganised for progressive disclosure.** Ten skills in
`testing-handbook-skills` exceeded the 500-line `SKILL.md` ceiling that the bundle's own validator
enforces (`scripts/validate-skills.py`, `MAX_LINES = 500`), failing 10 of 16 checks as vendored.
Detail was moved from each `SKILL.md` into sibling `references/*.md` files, leaving a linked stub:
`libfuzzer`, `aflpp`, `libafl`, `harness-writing`, `coverage-analysis`, `semgrep`, `codeql`,
`wycheproof`, `atheris`, `constant-time-testing`.

**Content was relocated, not edited**, and the H2 sections each skill's `type` requires stayed in
`SKILL.md`. A future re-sync from upstream should re-apply this split rather than overwrite it —
otherwise the bundle validator starts failing again.

## Anthropic

| Path | Description |
|---|---|
| `claude/writing-skills/anthropic-best-practices.md` | Copy of Anthropic's Agent Skills authoring guidance |
| `claude/frontend-design/` | Derived from the official `frontend-design` Claude Code plugin |

The Gemini tree carries an adapted equivalent at `gemini/writing-skills/gemini-best-practices.md`.

## jswortz/my-skills

The Gemini ports of the shared skills — the terminology adaptation that makes `gemini/` a port
rather than a copy of `claude/` — were adopted from
[jswortz/my-skills](https://github.com/jswortz/my-skills), along with
`adk/references/state_management.md` and `gemini-enterprise/references/browser_automation.md`.

## PaperBanana

`{claude,gemini}/paperbanana/` documents the third-party [PaperBanana](https://pypi.org/project/paperbanana/)
tool and its MCP server. It contains usage guidance only, not PaperBanana source.

## Everything else

Original to this repository and covered by [LICENSE](LICENSE).

---

**Adding vendored content?** Record it here in the same pass — upstream source, author, and
license. An entry here is the only durable record of where a skill came from.
