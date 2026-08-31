---
name: paperbanana
description: Use when creating architecture, methodology, system, data-flow, deployment, or schema diagrams, statistical plots or charts, or multi-figure publication packages via PaperBanana - including GCP-branded Google Cloud architecture diagrams - or when iterating on, refining, or evaluating generated figures against a reference. Also use when the user mentions PaperBanana, figure generation, batch diagram generation, or configuring Gemini as an image generation provider.
user-invocable: true
allowed-tools:
  - mcp__paperbanana__generate_diagram
  - mcp__paperbanana__generate_plot
  - mcp__paperbanana__continue_diagram
  - mcp__paperbanana__continue_plot
  - mcp__paperbanana__batch_diagrams
  - mcp__paperbanana__batch_plots
  - mcp__paperbanana__orchestrate_figures
  - mcp__paperbanana__evaluate_diagram
  - mcp__paperbanana__evaluate_plot
  - mcp__paperbanana__download_references
  - Read
  - "Bash(paperbanana *)"
---

# PaperBanana

Generate publication-quality diagrams and statistical plots through the **PaperBanana MCP server** —
a visualizer↔critic pipeline that plans, renders, and self-critiques figures.

Prefer the MCP tools. They are faster than the CLI, keep run state for cheap refinement, and are
what this skill is built around. The CLI, Python API, and pipeline internals are in
[references/cli.md](references/cli.md).

For GCP-branded architecture diagrams built by **direct Vertex AI image generation with official
icon overlay** — a different toolchain from PaperBanana — use the `gcp-diagram` skill instead.

## Model policy (REQUIRED)

| Task | Model |
|---|---|
| Image generation (diagrams, plots, visuals) | `gemini-3.1-flash-image` |
| Text / VLM (planning, captions, critique, evaluation) | `gemini-3.5-flash` |

- The MCP server is **preconfigured** with these via `IMAGE_MODEL` / `VLM_MODEL`, so
  **single-figure tools need no model args** — do not override them.
- **Batch / orchestrate / continue tools default to their own models** — always pass explicitly:
  `image_model="gemini-3.1-flash-image"`, `vlm_model="gemini-3.5-flash"` (and `*_provider="gemini"`).
- Never substitute `gemini-2.5-*` or any `*-pro-*` / `*-pro-image` model. The pro and preview image
  models burn far more of a small quota. Older docs listing `gemini-3-pro-image-preview` as the
  default are superseded by this table.

## Tools

| Tool | Use for | Pass models? |
|---|---|---|
| `generate_diagram` | one methodology / architecture / system / data-flow diagram from text | no (server env) |
| `generate_plot` | one statistical plot / chart from JSON data | no (server env) |
| `continue_diagram` / `continue_plot` | refine an existing run by `run_id` (skips retrieval + planning) | **yes** |
| `batch_diagrams` / `batch_plots` | many figures from a YAML/JSON manifest | **yes** |
| `orchestrate_figures` | plan + generate a full figure package from a paper | **yes** |
| `evaluate_diagram` / `evaluate_plot` | score a figure against a reference (4 dimensions) | no |
| `download_references` | one-time: fetch reference set for better in-context examples | no |

All are `mcp__paperbanana__*`. If the MCP server is unavailable, fall back to the CLI —
see [references/cli.md](references/cli.md).

## Workflow

1. **Gather** — for a diagram: components and services, connections with protocols and direction,
   logical groupings, and diagram type (system overview, agent hierarchy, data flow, schema,
   deployment). For a plot: the data plus the communicative intent — what the reader should
   conclude.
2. **Generate** — call the matching tool:
   - `generate_diagram(source_context=..., caption=...)`
   - `generate_plot(data_json=..., intent=...)`
   - Keep `auto_refine=false` (or `iterations` low) under the 2 RPM image cap.
3. **Verify** — run the branding and spelling checklist in
   [references/gcp-brand.md](references/gcp-brand.md). For GCP diagrams, `source_context` and
   `caption` must carry the brand phrases and color conventions from that file.
4. **Refine cheaply** — do not regenerate from scratch. Call
   `continue_diagram(run_id=..., feedback=..., image_model="gemini-3.1-flash-image", vlm_model="gemini-3.5-flash")`;
   it reuses retrieval and planning.

## Evaluation

`evaluate_diagram` / `evaluate_plot` score a generated figure against a human reference on four
dimensions: **Faithfulness, Conciseness, Readability, Aesthetics**. Supply the generated image, the
reference image, the source context, and the caption.

## Quota — a separate pool from Vertex

PaperBanana authenticates with `GOOGLE_API_KEY` against the **Gemini Developer API**
(`generativelanguage.googleapis.com`), which is a **separate quota pool** from the **Vertex AI**
project quota. It does **not** contend with a Vertex 2 RPM image cap — verified 2026-07-13 by
generating two diagrams during a live batch with zero failures on either side.

Caveats that still apply:

- The Developer API has its own rate limits (free-tier RPM per key). Under bursty use expect `429` /
  `ClientError`. `auto_refine=true` loops visualizer→critic and issues many image calls, so prefer
  `auto_refine=false` with `iterations=1–2` unless you need refinement. Batches serialize best with
  `concurrency=1`.
- The key must be a valid **Gemini Developer API** key (it lists models at `/v1beta/models?key=…`).

## Common mistakes

| Mistake | Fix |
|---|---|
| Passing `image_model`/`vlm_model` to `generate_diagram`/`generate_plot` | Unsupported — they read the server env; omit. |
| Letting `batch_*` / `orchestrate_*` pick default models | Always pass `image_model="gemini-3.1-flash-image"`, `vlm_model="gemini-3.5-flash"`. |
| Regenerating just to tweak a figure | Use `continue_*` with the `run_id`. |
| Assuming PaperBanana eats the Vertex 2 RPM cap | It bills the separate Gemini Developer API pool. |
| Reaching for a `*-pro-image` model | Forbidden by the model policy above — it burns quota for no gain here. |
| Trademarked GCP logos render wrong | Expected — generative models approximate icons. Keep every text label spelling-accurate (table in gcp-brand.md). |
| Low-quality CLI output | Add `--optimize --auto`; see [references/cli.md](references/cli.md). |

## References

- [references/cli.md](references/cli.md) — CLI commands, provider setup, batch manifests, Python API, pipeline architecture
- [references/gcp-brand.md](references/gcp-brand.md) — brand colors, spelling table, verification checklist
- GCP icon gallery: https://cloud.google.com/icons
