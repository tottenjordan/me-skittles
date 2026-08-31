# PaperBanana CLI, Python API, and pipeline internals

Fallback for when the MCP server is unavailable, plus the details that do not belong in the main
workflow. The MCP tools in `SKILL.md` are the preferred path.

> **Model policy still applies.** Several defaults below predate the current policy — notably
> `gemini-2.0-flash` (VLM) and `gemini-3-pro-image-preview` (image). Override them to
> `gemini-3.5-flash` and `gemini-3.1-flash-image`. Never use a `*-pro-image` model.

## Quick reference

| Command | What it does |
|---|---|
| `paperbanana generate -i file.txt -c "caption"` | Generate methodology diagram |
| `paperbanana plot -d data.csv --intent "description"` | Generate statistical plot |
| `paperbanana batch -m manifest.yaml` | Batch generate multiple diagrams |
| `paperbanana evaluate -g out.png -r ref.png --context method.txt -c "caption"` | Evaluate diagram quality |
| `paperbanana generate --continue --feedback "fix colors"` | Refine latest run |
| `paperbanana studio` | Launch local Gradio web UI |
| `paperbanana setup` | Interactive first-time config wizard |

## Provider setup (Gemini)

```bash
export GOOGLE_API_KEY=your-key   # or run: paperbanana setup
```

Override the shipped defaults to match the required model policy:

```bash
export GOOGLE_VLM_MODEL=gemini-3.5-flash
export GOOGLE_IMAGE_MODEL=gemini-3.1-flash-image
export GOOGLE_BASE_URL=https://custom-endpoint.example.com  # optional proxy
```

Select the provider explicitly on the command line:

```bash
paperbanana generate -i method.txt -c "Overview" \
  --vlm-provider gemini --image-provider google_imagen
```

## Generating diagrams

```bash
# Basic
paperbanana generate -i method.txt -c "Overview of our framework"

# With input optimization + auto-refine (best quality)
paperbanana generate -i method.txt -c "Overview" --optimize --auto

# From PDF (requires: pip install 'paperbanana[pdf]')
paperbanana generate -i paper.pdf -c "System architecture" --pdf-pages "3-8"

# Custom iterations
paperbanana generate -i method.txt -c "Overview" -n 5
```

Key flags: `--optimize` (preprocess inputs), `--auto` (loop until the critic is satisfied),
`--format png|jpeg|webp`, `--verbose` (show agent progress).

Output lands in `outputs/run_<timestamp>/final_output.png`, alongside every iteration and its
metadata.

## Continuing and refining runs

```bash
# Continue the latest run with feedback
paperbanana generate --continue --feedback "Make arrows thicker, colors more distinct"

# Continue a specific run
paperbanana generate --continue-run run_20260218_125448_e7b876 --iterations 3
```

## Statistical plots

```bash
paperbanana plot -d results.csv --intent "Bar chart comparing model accuracy across benchmarks"
```

## Batch generation

```bash
paperbanana batch -m manifest.yaml --optimize
```

Manifest format (YAML). Paths are relative to the manifest file's own directory:

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

Batch reports:

```bash
paperbanana batch-report --batch-dir outputs/batch_<id> --format markdown
paperbanana batch-report --batch-id batch_<id> --format html --output report.html
```

## Evaluating diagrams

VLM-as-Judge scoring on four dimensions — Faithfulness, Readability, Conciseness, Aesthetics:

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
    vlm_model="gemini-3.5-flash",
    image_provider="google_imagen",
    image_model="gemini-3.1-flash-image",
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

`generate()` accepts a `progress_callback` receiving `PipelineProgressEvent` objects
(stage, message, seconds, iteration).

## MCP server registration

```json
{
  "mcpServers": {
    "paperbanana": {
      "command": "uvx",
      "args": ["--from", "paperbanana[mcp]", "paperbanana-mcp"],
      "env": {
        "GOOGLE_API_KEY": "your-key",
        "IMAGE_MODEL": "gemini-3.1-flash-image",
        "VLM_MODEL": "gemini-3.5-flash"
      }
    }
  }
}
```

Setting `IMAGE_MODEL` and `VLM_MODEL` here is what lets the single-figure tools run without model
arguments.

## Pipeline architecture

Seven specialized agents across two phases:

- **Phase 0** (optional, `--optimize`): Input Optimizer — Context Enricher and Caption Sharpener in parallel
- **Phase 1** (Planning): Retriever → Planner → Stylist
- **Phase 2** (Iterative): Visualizer → Critic → repeat, three iterations by default

## CLI troubleshooting

| Problem | Fix |
|---|---|
| No API key configured | Run `paperbanana setup` or set `GOOGLE_API_KEY` |
| Low quality output | Add `--optimize --auto` |
| Wrong provider used | Pass `--vlm-provider gemini --image-provider google_imagen` |
| PDF input fails | `pip install 'paperbanana[pdf]'` |
| Studio will not start | `pip install 'paperbanana[studio]'` |
| Batch paths wrong | Manifest paths resolve relative to the manifest file's directory |
