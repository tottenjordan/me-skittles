# Insights Report Template

Full section structure for NovaStorm GEPA pipeline insights reports. Based on 6 prior reports (including tuned 28-epoch cold start).

## Header Block

```markdown
# NovaStorm GEPA: {N}-Epoch {Variant} Report

**Pipeline:** `{pipeline_display_name}`
**Experiment:** `{experiment_name}`
**Run:** `{run_name}`
**Topic:** {nl_research_topic}
**Date:** {YYYY-MM-DD}
**Memory Bank:** {Cold start (wiped) | Warm start (retained)}
**Agent Engine ID:** `{agent_engine_id}`

> **Key result:** {One-sentence headline finding}
```

## Section 1: Executive Summary

### Comparison Table (required)

Always compare against all prior runs. Add new run as the rightmost column.

```markdown
| Metric | Tuned 28-Ep (Cold) | 25-Ep Asteroid | 30-Ep Supply Chain | 25-Ep H5 Cal | 25-Ep H5v2 | **This Run** |
|--------|--------------------|--------------|--------------------|-------------|-----------|------------|
| Start | Cold | Warm | Warm | Warm | Warm | **{value}** |
| Epochs | 28 | 25 | 30 | 25 | 25 | **{value}** |
| Scored | 1,096 | 215 | 248 | 237 | 395 | **{value}** |
| Persisted | — | 66 (30.7%) | 117 (47.2%) | 125 (52.7%) | 195 (49.4%) | **{value}** |
| Mean (NF) | 0.516 | 0.681 | 0.786 | 0.735 | 0.613 | **{value}** |
| Peak | 0.968 | 1.000 | 0.95 | — | 1.000 | **{value}** |
| Floor rate | ~15% | 11.2% | 19.4% | 21.5% | 6.1% | **{value}** |
| Trajectory | 0% | +16.6% | 0% | +1.1% | +8.5% | **{value}** |
| Insights/epoch | 39.1 | 8.6 | 8.3 | 9.5 | 15.8 | **{value}** |
```

### Key Findings (3-5 bullets)

Highlight what's new, surprising, or record-breaking about this run.

## Section 2: Methodology

### Configuration Changes Table

```markdown
| Parameter | Prior Run | This Run | Rationale |
|-----------|-----------|----------|-----------|
```

### Architecture Diagram

```markdown
![{N}-Epoch Pipeline Architecture](../images/{prefix}_architecture.png)
```

## Section 3: Score Trajectory

### Average Score Progression Table

Split epochs into bands (e.g., thirds for trajectory calculation):

```markdown
| Epoch Range | Avg Score (NF) | n (scored) | Floor Rate | Trend |
|-------------|----------------|------------|------------|-------|
| E0–E{a} (early) | {value} | {n} | {%} | — |
| E{a+1}–E{b} (mid) | {value} | {n} | {%} | {vs early} |
| E{b+1}–E{last} (late) | {value} | {n} | {%} | {vs early} |
```

### Trajectory Chart

```markdown
![Score Trajectory](../images/{prefix}_score_trajectory.png)
```

## Section 4: Score Distribution

### Floor Analysis

Document floor scores (<=0.10) — are they critic failures or legitimate low scores? Check for `"Critic scoring failed"` in logs.

### Per-Dimension Scores (if available)

```markdown
| Dimension | Mean | Interpretation |
|-----------|------|----------------|
| Novelty | {val} | |
| Relevance | {val} | |
| Impact | {val} | |
| Actionability | {val} | |
| Specificity | {val} | |
| Trace Audit | {val} | (if 6-dim scoring) |
```

## Section 5: Container Analysis

### Per-Container Performance Table

```markdown
| Container | Scored | Persisted | Persist % | Floors | Floor % | Mean (NF) | Peak | Trace Catches |
|-----------|--------|-----------|-----------|--------|---------|-----------|------|---------------|
```

### Per-Container Trajectory Table

```markdown
| Container | Early | Mid | Late | Trajectory | Pattern |
|-----------|-------|-----|------|------------|---------|
```

### Phase Distribution

```markdown
| Phase | Count | Share | Mean Score | Floor Rate |
|-------|-------|-------|------------|------------|
| Crossover | | | | |
| Mutation | | | | |
| Explore | | | | |
| Elitism | | | | |
| Random | | | | |
| Initial | | | | (cold start only) |
```

### Tool Usage

```markdown
| Tool | Calls | Share |
|------|-------|-------|
```

### Data Source Distribution

```markdown
| Source | References | Share |
|--------|-----------|-------|
| 1P | | |
| GDELT | | |
| Trends | | |
| Weather | | |
| Web | | |
```

## Section 6: Adaptive Threshold Analysis (if FITNESS_SCALING_FACTOR changed)

Include when the run uses a different `FITNESS_SCALING_FACTOR` than the prior run, or when threshold behavior is a key finding.

### Threshold Trajectory

```markdown
| Metric | Prior Run (SCALING={x}) | This Run (SCALING={y}) |
|--------|------------------------|----------------------|
| Threshold at epoch 1 | {value} | {value} |
| Threshold at epoch N/4 | {value} | {value} |
| Threshold at epoch N/2 | {value} | {value} |
| Threshold at epoch N | {value} | {value} |
| Maximum threshold | {value} | {value} |
```

### Headroom Analysis

Document the gap between population mean score and adaptive threshold. Healthy headroom is >0.15. If headroom is negative (threshold > mean), the system is in a death spiral.

Formula: `threshold = min(0.95, base + log1p(avg_fitness) * FITNESS_SCALING_FACTOR)`

## Section 7: Concurrency Analysis (if concurrency issues observed)

Include when timeout rates are high, concurrency collapse occurred, or when comparing throughput across runs.

### Three Bottleneck Model

```markdown
| Bottleneck | Formula | At C={c} | Limit | Status |
|------------|---------|----------|-------|--------|
| Memory Bank Writes | C * tables * 2 | {value}/epoch | 100/min | {Safe/Warning/Critical} |
| Memory Bank Reads | C * tables * 3 | {value}/epoch | 300/min | {Safe/Warning/Critical} |
| Gemini API | semaphore * tables | {value} concurrent | 60+ | {Safe/Warning/Critical} |
```

### Effective Throughput

```
effective_throughput = min(concurrency * tables, write_quota / 2)
```

### Duration Analysis

```markdown
| Metric | Value |
|--------|-------|
| Epochs completed | {n} of {total} |
| Total duration | {hours} |
| Average epoch duration | {minutes} |
| Insights per minute | {value} |
| Timeout rate | {%} |
```

### Recommended Configuration by Run Length

```markdown
| Run Length | Concurrency | Insights/Epoch | Expected Duration | Bottleneck |
|------------|-------------|----------------|-------------------|------------|
```

## Section 8: Feature Assessment (if applicable)

For each new feature being tested in this run, document:
- **Status:** Active / Disabled / Partial
- **Mechanism:** How it works
- **Evidence:** Quantitative impact
- **Verdict:** Keep / Modify / Remove

## Section 9: Cross-Run Comparison

### Full Comparison Table

Same as Executive Summary table but with more detail (per-container breakdowns, phase distributions).

### Controlled Pairwise Comparison

Find the closest "control" run (same topic, same dataset, fewest parameter differences) and do a detailed delta analysis.

```markdown
| Parameter | Control Run | This Run | Delta |
|-----------|------------|----------|-------|
```

## Section 10: Discussion

Address:
- Why trajectory is positive/negative/flat
- Cold vs warm start effects
- Which evolutionary phases drove quality (mutation typically highest mean, crossover drives recombination)
- Any concurrency collapse patterns
- Novelty saturation (if novelty dimension < 0.40 — insights becoming repetitive)
- Late-epoch quality dips (evolutionary exhaustion, threshold ratcheting, smaller sample sizes)
- Container divergence (why some containers learn faster than others)

## Section 11: Recommendations

### Next Run Configuration Table

```markdown
| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
```

### Immediate Actions and Future Work (bullet lists)

## Section 12: Appendix

### A. Per-Epoch Detail

```markdown
| Epoch | n | Mean (NF) | Floors | Max |
|-------|---|-----------|--------|-----|
```

### B. Pipeline Parameters

Full YAML or .env dump from the pipeline run.

### C. GCS Artifact Paths

```
gs://{bucket}/{experiment}/{run}/pipeline_root/evidence_reports/{table}/react_loop_fanout_log.json
gs://{bucket}/{experiment}/{run}/pipeline_root/evidence_reports/{table}/progress.json
```

### D. Diagrams

List all generated diagrams with generation method:
```markdown
| Diagram | File | Method |
|---------|------|--------|
| Architecture | {prefix}_architecture.png | gcp-diagram skill |
| Score Trajectory | {prefix}_score_trajectory.png | generate-diagram (PaperBanana) or matplotlib |
| Cross-Run Comparison | {prefix}_cross_run.png | generate-diagram (PaperBanana) or matplotlib |
| Container Performance | {prefix}_containers.png | generate-diagram (PaperBanana) or matplotlib |
| Container Trajectories | {prefix}_container_trajectories.png | generate-diagram (PaperBanana) or matplotlib |
| Feature Assessment | {prefix}_features.png | generate-diagram (PaperBanana) or matplotlib |
```
