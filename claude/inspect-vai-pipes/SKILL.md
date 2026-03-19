---
name: inspect-vai-pipes
description: Use when debugging, inspecting, or analyzing Vertex AI Pipeline jobs - checking worker logs, diagnosing 429 errors, confirming parameters, analyzing scores, finding straggler tasks, or estimating completion time. Also use when pipeline runs fail, hang, or produce unexpected results.
---

# Inspect Vertex AI Pipelines

Debug and analyze Vertex AI Pipeline jobs using the SDK, Cloud Logging, and GCS artifacts.

## Required Inputs from User

- **Pipeline display name or run ID** (e.g., `novastorm-run-20260319-150709`)
- **GCP project ID** (e.g., `hybrid-vertex`)
- **Region** (e.g., `us-central1`)
- **GCS bucket** for pipeline artifacts (if checking evidence reports, logs, progress)

## Quick Reference

| Task             | Method                                                                   |
| ---------------- | ------------------------------------------------------------------------ |
| Find pipeline    | `aiplatform.PipelineJob.list()` + filter by display name                 |
| Get state        | `r.state` (see state codes below)                                        |
| Get parameters   | `r.gca_resource.runtime_config.parameter_values`                         |
| Get task details | `r.task_details` (list of tasks with state, name, execution metadata)    |
| Worker logs      | Cloud Logging: `resource.type="ml_job"`                                  |
| Pipeline events  | Cloud Logging: `resource.type="aiplatform.googleapis.com/PipelineJob"`   |
| GCS artifacts    | Check `evidence_reports/`, `progress.json`, log files in pipeline bucket |

## Pipeline State Codes

| Code | State      | Description            |
| ---- | ---------- | ---------------------- |
| 1    | QUEUED     | Waiting to start       |
| 2    | PENDING    | Being prepared         |
| 3    | RUNNING    | Actively executing     |
| 4    | SUCCEEDED  | Completed successfully |
| 5    | FAILED     | Terminated with error  |
| 6    | CANCELLING | Cancel in progress     |
| 7    | CANCELLED  | User cancelled         |
| 8    | PAUSED     | Paused                 |
| 9    | SKIPPED    | Skipped (caching)      |

## Task Execution State Codes

| Code | State            |
| ---- | ---------------- |
| 1    | PENDING          |
| 2    | RUNNING_DRIVER   |
| 3    | DRIVER_SUCCEEDED |
| 4    | RUNNING_EXECUTOR |
| 5    | SUCCEEDED        |
| 9    | FAILED           |

## Step 1: Find and Inspect the Pipeline

```python
from google.cloud import aiplatform
aiplatform.init(project='PROJECT_ID', location='REGION')

# Find by display name substring
runs = aiplatform.PipelineJob.list()
r = [r for r in runs if 'SEARCH_TERM' in (r.display_name or '')][0]

print(f'Display Name: {r.display_name}')
print(f'Resource Name: {r.resource_name}')
print(f'State: {r.state}')  # See state codes above
print(f'Created: {r.create_time}')

# Parameters
params = r.gca_resource.runtime_config.parameter_values
for k, v in sorted(params.items()):
    print(f'  {k}: {v}')

# Task details
for t in r.task_details:
    print(f'{t.task_name}: state={t.state}')
    if t.execution and t.execution.metadata:
        for k, v in t.execution.metadata.items():
            if k.startswith('input:'):
                print(f'  {k}: {str(v)[:100]}')
```

**Common gotcha:** `PipelineJob` objects lack `start_time` and `end_time` attributes. Use `create_time` and check Cloud Logging for actual start/end timestamps.

**Display name vs resource name:** The `display_name` and `resource_name` often differ slightly (e.g., `novastorm-pipeline-20260319-150709` vs `novastorm-run-20260319-150709`). Always search with a substring.

## Step 2: Query Worker Logs (Cloud Logging)

Worker container logs use `resource.type="ml_job"`. Pipeline orchestration events use `resource.type="aiplatform.googleapis.com/PipelineJob"`.

### Get pipeline task events (start/complete times)

```bash
gcloud logging read \
  'resource.type="aiplatform.googleapis.com/PipelineJob" AND "PIPELINE_RUN_ID"' \
  --project=PROJECT_ID --limit=50 --format=json --order=asc
```

Parse with: `e['jsonPayload']['payload']['taskName']`, `state`, `startTime`, `endTime`

### Get worker execution logs

```bash
# Key execution milestones (epochs, scores, errors, completions)
gcloud logging read \
  'resource.type="ml_job" AND
   (jsonPayload.message=~"EPOCH|Critic Score|completed|evidence|Error|429|ReadError" OR
    jsonPayload.levelname="ERROR") AND
   timestamp>="PIPELINE_START_TIME"' \
  --project=PROJECT_ID --limit=500 \
  --format="value(timestamp,jsonPayload.message)" --order=asc
```

**Log structure:** Worker logs are in `jsonPayload.message` (not `textPayload`). The `levelname` field contains `INFO`, `ERROR`, `WARNING`.

### Filter for specific issues

```bash
# 429 rate limit errors (Gemini API + Memory Bank)
jsonPayload.message=~"429|RESOURCE_EXHAUSTED"

# Critic scores
jsonPayload.message=~"Critic Score"

# Epoch transitions
jsonPayload.message=~"EPOCH.*Concurrency"

# Worker task assignments
jsonPayload.message=~"\\[Worker \\d+\\] Executing"

# Memory Bank writes
jsonPayload.message=~"Memory Bank|memory bank"

# GCS uploads (evidence reports, progress)
jsonPayload.message=~"Uploaded.*evidence|Uploaded.*progress"

# Pipeline completion
jsonPayload.message=~"fan_out_insights completed"
```

## Step 3: Check GCS Artifacts

```python
from google.cloud import storage
client = storage.Client(project='PROJECT_ID')
bucket = client.bucket('BUCKET_NAME')

# Evidence reports (per-epoch summaries)
for b in client.list_blobs(bucket, prefix='pipeline_root/evidence_reports/'):
    print(f'{b.name} ({b.size} bytes, updated {b.updated})')

# Progress file (live status)
blob = bucket.blob('pipeline_root/evidence_reports/progress.json')
if blob.exists():
    import json
    print(json.loads(blob.download_as_text()))

# Main log file
blob = bucket.blob('pipeline_root/evidence_reports/react_loop_fanout_log.json')
if blob.exists():
    print(f'Log size: {blob.size} bytes')
```

**Artifact paths may vary.** Some pipelines write to `pipeline_root/evidence_reports/`, others to `self-evolve/pipeline_root/evidence_reports/`. Check both.

## Step 4: Analyze Scores

Extract and analyze critic scores from logs:

```python
import re
from collections import Counter

scores, novelty_scores = [], []
persisted, not_persisted = 0, 0

for line in log_lines:
    score_m = re.search(r'Critic Score:\s*([\d.]+)', line)
    novelty_m = re.search(r'Novelty:\s*([\d.]+)', line)
    persist_m = re.search(r'Persist:\s*(True|False)', line)
    if score_m:
        scores.append(float(score_m.group(1)))
        if novelty_m: novelty_scores.append(float(novelty_m.group(1)))
        if persist_m: (persisted if persist_m.group(1) == 'True' else not_persisted) + 1

print(f'Total: {len(scores)}, Persisted: {persisted}, Rate: {persisted/len(scores)*100:.1f}%')
print(f'Mean: {sum(scores)/len(scores):.3f}, Max: {max(scores):.3f}, Min: {min(scores):.3f}')
```

**Watch for floor scores:** A score of exactly `0.10` typically means the critic scoring failed (429 error during scoring). Many 0.10 scores indicate rate limiting problems.

## Common Issues

### Massive 429 Errors

**Symptom:** Logs flooded with `HTTP/1.1 429 Too Many Requests` or `RESOURCE_EXHAUSTED`

**Root cause:** `concurrency` param too high. Effective parallelism = `concurrency × num_datasets`. At concurrency=100 with 5 datasets = 500 simultaneous API calls.

**Fix:** Reduce concurrency to 20-30 per dataset.

### Memory Bank RESOURCE_EXHAUSTED

**Symptom:** `Quota exceeded for quota metric 'Memory Bank write requests'`

**Root cause:** Memory Bank write quota is 100 writes/min/region. High concurrency overwhelms the rate limiter.

**Fix:** Lower concurrency, or increase semaphore delay in `react_loop_fanout.py`.

### Straggler Workers

**Symptom:** Pipeline running long after most workers complete. One or two tasks still in state 2/4.

**Diagnosis:** Check which `for-loop-1-worker-N` tasks are still running. Cross-reference with `dataset_item` in task execution metadata to identify the slow dataset.

**Common causes:** Large tables triggering slow Dataplex scans, workers stuck in retry loops from persistent 429s.

### Pipeline State SKIPPED (9)

**Cause:** Vertex AI pipeline caching. If inputs match a previous run, tasks may be skipped entirely.

**Fix:** Change a parameter value or disable caching in the pipeline definition.

### Epoch Regression (Epoch 2 worse than Epoch 1)

**Symptom:** Mean scores decrease across epochs instead of improving.

**Common causes:** 429 errors during epoch 1 corrupted skill evolution feedback; floor scores (0.10) polluting aggregate metrics used for skill selection.

## Cross-Validating Source Code

When logs show unexpected behavior, check the source:

| Concern                        | File to Check                                                      |
| ------------------------------ | ------------------------------------------------------------------ |
| Pipeline parameters & defaults | `deploy_vertex_pipeline.py` (argparse block + `deploy_pipeline()`) |
| Worker execution logic         | `react_loop_fanout.py` (`fan_out_insights()`)                      |
| Concurrency / rate limiting    | `react_loop_fanout.py` (semaphore, delay constants)                |
| Critic scoring                 | `src/prompts/critic_scoring.md`                                    |
| Skill evolution                | `src/swarm_manager.py`                                             |
| API endpoint defaults          | `backend/main.py`                                                  |
| Dataplex data scans            | `src/dataplex_client.py`                                           |

## Estimating Completion Time

1. Check how many `for-loop-1-worker-N` tasks have completed vs still running
2. Note the wall-clock time of completed workers (from Cloud Logging task events)
3. Workers processing larger tables or hitting more 429s take proportionally longer
4. A 2-epoch run with concurrency 30 on 5 tables typically takes 1-2 hours
5. A 2-epoch run with concurrency 100 on 5 tables can take 2-3+ hours (due to 429 backoff)

## Google Cloud Console

Pipeline runs can also be inspected in the console at:

```
https://console.cloud.google.com/vertex-ai/pipelines/locations/REGION/runs/PIPELINE_RUN_ID?project=PROJECT_ID
```

The console shows the DAG visualization, task states, logs, and parameter values.
