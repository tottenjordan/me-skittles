---
name: paperbanana
description: Use when generating academic diagrams, statistical plots, or illustrations from text descriptions or data files. Use when the user mentions PaperBanana, methodology diagrams, figure generation, batch diagram generation, or evaluating generated diagrams against references. Also use when configuring Gemini as an image generation provider.
---

# PaperBanana

Agentic framework for generating publication-quality academic diagrams and statistical plots from text descriptions. Multi-agent pipeline with iterative refinement.

## Quick Reference

| Command                                                                        | What it does                         |
| ------------------------------------------------------------------------------ | ------------------------------------ |
| `paperbanana generate -i file.txt -c "caption"`                                | Generate methodology diagram         |
| `paperbanana plot -d data.csv --intent "description"`                          | Generate statistical plot            |
| `paperbanana batch -m manifest.yaml`                                           | Batch generate multiple diagrams     |
| `paperbanana evaluate -g out.png -r ref.png --context method.txt -c "caption"` | Evaluate diagram quality             |
| `paperbanana generate --continue --feedback "fix colors"`                      | Refine latest run                    |
| `paperbanana studio`                                                           | Launch local Gradio web UI           |
| `paperbanana setup`                                                            | Interactive first-time config wizard |

## Provider Setup (Gemini)

```bash
# Set in .env or environment
export GOOGLE_API_KEY=your-key

# Or run the setup wizard
paperbanana setup
```

Gemini uses `gemini-2.0-flash` (VLM) and `gemini-3-pro-image-preview` (image gen) by default. Override with:

```bash
export GOOGLE_VLM_MODEL=gemini-2.5-flash
export GOOGLE_IMAGE_MODEL=gemini-3-pro-image-preview
export GOOGLE_BASE_URL=https://custom-endpoint.example.com  # optional proxy
```

Use Gemini provider via CLI:

```bash
paperbanana generate -i method.txt -c "Overview" \
  --vlm-provider gemini --image-provider google_imagen
```

## Generating Diagrams

```bash
# Basic
paperbanana generate -i method.txt -c "Overview of our framework"

# With input optimization + auto-refine (best quality)
paperbanana generate -i method.txt -c "Overview" --optimize --auto

# From PDF (requires pip install 'paperbanana[pdf]')
paperbanana generate -i paper.pdf -c "System architecture" --pdf-pages "3-8"

# Custom iterations
paperbanana generate -i method.txt -c "Overview" -n 5
```

Key flags: `--optimize` (preprocess inputs), `--auto` (loop until critic satisfied), `--format png|jpeg|webp`, `--verbose` (show agent progress).

Output: `outputs/run_<timestamp>/final_output.png` plus all iterations and metadata.

## Continuing / Refining Runs

```bash
# Continue latest run with feedback
paperbanana generate --continue --feedback "Make arrows thicker, colors more distinct"

# Continue specific run
paperbanana generate --continue-run run_20260218_125448_e7b876 --iterations 3
```

## Statistical Plots

```bash
paperbanana plot -d results.csv --intent "Bar chart comparing model accuracy across benchmarks"
```

## Batch Generation

Generate multiple diagrams from a manifest file:

```bash
paperbanana batch -m manifest.yaml --optimize
```

Manifest format (YAML):

```yaml
items:
  - input: path/to/method1.txt
    caption: "Encoder-decoder overview"
    id: fig1
  - input: paper.pdf
    caption: "Training pipeline"
    id: fig2
    pdf_pages: "4-9"
```

Generate batch report:

```bash
paperbanana batch-report --batch-dir outputs/batch_<id> --format markdown
paperbanana batch-report --batch-id batch_<id> --format html --output report.html
```

## Evaluating Diagrams

VLM-as-Judge scoring on 4 dimensions: Faithfulness, Readability, Conciseness, Aesthetics.

```bash
paperbanana evaluate \
  -g generated.png \
  -r human_reference.png \
  --context method.txt \
  -c "Overview of our framework"
```

## Python API

```python
import asyncio
from paperbanana import PaperBananaPipeline, GenerationInput, DiagramType
from paperbanana.core.config import Settings

settings = Settings(
    vlm_provider="gemini",
    vlm_model="gemini-2.0-flash",
    image_provider="google_imagen",
    image_model="gemini-3-pro-image-preview",
    optimize_inputs=True,
    auto_refine=True,
)

pipeline = PaperBananaPipeline(settings=settings)

result = asyncio.run(pipeline.generate(
    GenerationInput(
        source_context="Our framework consists of...",
        communicative_intent="Overview of the proposed method.",
        diagram_type=DiagramType.METHODOLOGY,
    )
))
print(f"Output: {result.image_path}")
```

Continue a previous run:

```python
from paperbanana.core.resume import load_resume_state

state = load_resume_state("outputs", "run_20260218_125448_e7b876")
result = asyncio.run(pipeline.continue_run(
    resume_state=state,
    additional_iterations=3,
    user_feedback="Make the encoder block more prominent",
))
```

Progress callbacks: `generate()` accepts `progress_callback` with `PipelineProgressEvent` objects (stage, message, seconds, iteration).

## MCP Server

Add to MCP config for Claude Code / Cursor:

```json
{
  "mcpServers": {
    "paperbanana": {
      "command": "uvx",
      "args": ["--from", "paperbanana[mcp]", "paperbanana-mcp"],
      "env": { "GOOGLE_API_KEY": "your-key" }
    }
  }
}
```

Exposes 3 tools: `generate_diagram`, `generate_plot`, `evaluate_diagram`.

## Pipeline Architecture

7 specialized agents in 2 phases:

**Phase 0 (optional, `--optimize`):** Input Optimizer (Context Enricher + Caption Sharpener in parallel)

**Phase 1 (Planning):** Retriever → Planner → Stylist

**Phase 2 (Iterative):** Visualizer → Critic → repeat (default 3 iterations)

## Common Mistakes

| Mistake               | Fix                                                                    |
| --------------------- | ---------------------------------------------------------------------- |
| No API key configured | Run `paperbanana setup` or set `GOOGLE_API_KEY`                        |
| Low quality output    | Add `--optimize --auto` flags                                          |
| Wrong provider used   | Explicitly pass `--vlm-provider gemini --image-provider google_imagen` |
| PDF input fails       | Install PDF extra: `pip install 'paperbanana[pdf]'`                    |
| Studio won't start    | Install studio extra: `pip install 'paperbanana[studio]'`              |
| Batch paths wrong     | Manifest paths are relative to the manifest file's directory           |
