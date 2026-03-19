# Discovery Engine REST API Reference

## Base URL

```
# Global location
https://discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/global/collections/default_collection

# Regional location
https://{LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection
```

**API version:** `v1alpha` (required for streamAssist and assistant features). Use `v1` for Model Armor assistant updates.

## Authentication Headers

All requests require:

```
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/json
X-Goog-User-Project: {PROJECT_ID}
```

**Get token:** `gcloud auth print-access-token`

**Python ADC:**
```python
import google.auth
from google.auth.transport.requests import Request

credentials, _ = google.auth.default()
if not credentials.valid:
    credentials.refresh(Request())
token = credentials.token
```

## Resource Path Patterns

```
# Engine
projects/{project}/locations/{location}/collections/default_collection/engines/{engine_id}

# Data Store
projects/{project}/locations/{location}/collections/default_collection/dataStores/{data_store_id}

# Document Branch
.../dataStores/{data_store_id}/branches/default_branch

# Assistant
.../engines/{engine_id}/assistants/default_assistant

# Session
.../engines/{engine_id}/sessions/{session_id}

# Session (auto-session, no explicit create)
.../engines/{engine_id}/sessions/-

# Serving Config (for SearchService)
.../engines/{engine_id}/servingConfigs/default_config

# Agent (registered on assistant)
.../engines/{engine_id}/assistants/default_assistant/agents/{agent_id}
```

---

## Endpoints

### Create Engine

```
POST {BASE_URL}/engines?engineId={ENGINE_ID}
```

**Payload:**
```json
{
  "displayName": "my-engine",
  "solutionType": "SOLUTION_TYPE_SEARCH",
  "dataStoreIds": ["store-1", "store-2"],
  "searchEngineConfig": {
    "searchTier": "SEARCH_TIER_ENTERPRISE",
    "searchAddOns": ["SEARCH_ADD_ON_LLM"]
  },
  "industryVertical": "GENERIC",
  "appType": "APP_TYPE_INTRANET"
}
```

**Key fields:**
- `solutionType`: `SOLUTION_TYPE_SEARCH` or `SOLUTION_TYPE_CHAT`
- `searchTier`: `SEARCH_TIER_ENTERPRISE` (required for LLM features)
- `appType`: `APP_TYPE_INTRANET` (private docs) or `APP_TYPE_PUBLIC` (public website)

**Response:** Long-running operation (LRO). Poll until complete.

---

### Create Data Store

```
POST {BASE_URL}/dataStores?dataStoreId={DATA_STORE_ID}
```

**Payload (unstructured/GCS):**
```json
{
  "displayName": "My Documents",
  "industryVertical": "GENERIC",
  "contentConfig": "CONTENT_REQUIRED",
  "solutionTypes": ["SOLUTION_TYPE_CHAT"]
}
```

**`contentConfig` values:**
| Value | Use Case |
|-------|----------|
| `CONTENT_REQUIRED` | Unstructured documents (PDFs, HTML) |
| `NO_CONTENT` | Structured data (metadata only) |
| `PUBLIC_WEBSITE` | Website crawling |

---

### Import Documents

```
POST {BASE_URL}/dataStores/{DATA_STORE_ID}/branches/default_branch/documents:import
```

**Payload (GCS with JSONL metadata):**
```json
{
  "gcsSource": {
    "inputUris": ["gs://bucket/metadata/docs_metadata.jsonl"],
    "dataSchema": "document"
  },
  "reconciliationMode": "FULL"
}
```

**Payload (GCS wildcard, no metadata):**
```json
{
  "gcsSource": {
    "inputUris": ["gs://bucket/docs/*"]
  },
  "reconciliationMode": "FULL"
}
```

**JSONL metadata format** (one JSON object per line):
```json
{"id": "doc-1", "content": {"mimeType": "application/pdf", "uri": "gs://bucket/docs/file.pdf"}, "structData": {"title": "My Document", "category": "sop"}}
```

**`reconciliationMode`:**
- `FULL` — Replace all existing documents
- `INCREMENTAL` — Add/update without removing existing

**Response:** LRO. Document indexing can take several minutes after import completes.

---

### Create Session

```
POST {BASE_URL}/engines/{ENGINE_ID}/sessions
```

**Payload:**
```json
{
  "displayName": "MySession"
}
```

**Response:**
```json
{
  "name": "projects/{project}/locations/{location}/collections/default_collection/engines/{engine}/sessions/{session_id}",
  "displayName": "MySession",
  "state": "IN_PROGRESS"
}
```

**Auto-session:** Use `sessions/-` as the session name in streamAssist queries to skip explicit session creation. The system creates a session automatically.

---

### Query StreamAssist

```
POST {BASE_URL}/engines/{ENGINE_ID}/assistants/default_assistant:streamAssist
```

**Payload:**
```json
{
  "session": "projects/{project}/locations/{location}/collections/default_collection/engines/{engine}/sessions/{session_id}",
  "query": {
    "text": "What are the closing procedures?"
  }
}
```

**Payload with agent routing:**
```json
{
  "session": "...",
  "query": {"text": "..."},
  "agentsSpec": {
    "agentSpecs": [{"agentId": "agent-id-123"}]
  }
}
```

**Response (array of chunks):**
```json
[
  {
    "answer": {
      "state": "SUCCEEDED",
      "replies": [
        {
          "groundedContent": {
            "content": {
              "text": "Thinking about the question...",
              "role": "model",
              "thought": true
            }
          }
        },
        {
          "groundedContent": {
            "content": {
              "text": "The closing procedures require...",
              "role": "model",
              "thought": false
            }
          }
        }
      ]
    }
  },
  {
    "sessionInfo": {
      "name": "projects/{project}/.../sessions/{session_id}"
    }
  }
]
```

**Parsing logic:**
1. Iterate chunks looking for `answer` and `sessionInfo` keys
2. Within `answer`, iterate `replies[]`
3. Each reply: `reply.groundedContent.content.{text, role, thought}`
4. `thought=true` replies are model reasoning; `thought=false` are final answers
5. `sessionInfo.name` provides the session ID for follow-up queries

**Answer states:** `SUCCEEDED`, `FAILED`, `IN_PROGRESS`

---

### Search (via REST)

```
POST {BASE_URL}/engines/{ENGINE_ID}/servingConfigs/default_config:search
```

**Payload:**
```json
{
  "query": "closing procedures",
  "pageSize": 10,
  "dataStoreSpecs": [
    {
      "dataStore": "projects/{project}/locations/{location}/collections/default_collection/dataStores/{store_id}"
    }
  ]
}
```

**Python SDK equivalent:**
```python
from google.cloud import discoveryengine_v1beta as discoveryengine

client = discoveryengine.SearchServiceClient()
request = discoveryengine.SearchRequest(
    serving_config="...servingConfigs/default_config",
    query="closing procedures",
    page_size=10,
    data_store_specs=[
        discoveryengine.SearchRequest.DataStoreSpec(
            data_store="...dataStores/sop-store"
        )
    ],
)
response = client.search(request)
```

---

### Create Assistant

```
POST {BASE_URL}/engines/{ENGINE_ID}/assistants?assistantId=default_assistant
```

**Payload:**
```json
{
  "displayName": "Default Assistant"
}
```

---

### Update Assistant (Model Armor)

```
PATCH {BASE_URL_V1}/engines/{ENGINE_ID}/assistants/default_assistant?update_mask=customerPolicy
```

Note: Use `v1` (not `v1alpha`) for this endpoint.

**Payload:**
```json
{
  "customerPolicy": {
    "modelArmorConfig": {
      "userPromptTemplate": "projects/{project_number}/locations/{armor_location}/templates/{template_id}",
      "responseTemplate": "projects/{project_number}/locations/{armor_location}/templates/{template_id}",
      "failureMode": "FAIL_OPEN"
    }
  }
}
```

---

### Register External Agent

```
POST {BASE_URL}/engines/{ENGINE_ID}/assistants/default_assistant/agents?agentId={AGENT_ID}
```

**Payload:**
```json
{
  "displayName": "My External Agent",
  "agentEndpoint": {
    "endpointUri": "https://my-agent-abc123-uc.a.run.app"
  }
}
```

---

## Model Armor API

**Base URL:** `https://modelarmor.{LOCATION}.rep.googleapis.com/v1`

### Create Template

```
POST https://modelarmor.{LOCATION}.rep.googleapis.com/v1/projects/{PROJECT_NUMBER}/locations/{LOCATION}/templates?templateId={TEMPLATE_ID}
```

**Payload:**
```json
{
  "filterConfig": {
    "raiSettings": {
      "raiFilters": [
        {"filterType": "HATE_SPEECH", "confidenceLevel": "MEDIUM_AND_ABOVE"},
        {"filterType": "SEXUALLY_EXPLICIT", "confidenceLevel": "MEDIUM_AND_ABOVE"},
        {"filterType": "HARASSMENT", "confidenceLevel": "MEDIUM_AND_ABOVE"},
        {"filterType": "DANGEROUS", "confidenceLevel": "MEDIUM_AND_ABOVE"}
      ]
    },
    "piAndJailbreakFilterSettings": {
      "filterEnforcement": "ENABLED",
      "confidenceLevel": "MEDIUM_AND_ABOVE"
    },
    "sdpSettings": {
      "basicConfig": {
        "filterEnforcement": "ENABLED"
      }
    },
    "maliciousUriFilterSettings": {
      "filterEnforcement": "ENABLED"
    }
  }
}
```

**Location:** Use `us` multi-region for global Discovery Engine instances. The Model Armor template location must be compatible with the engine location.

**Confidence levels:** `LOW_AND_ABOVE`, `MEDIUM_AND_ABOVE`, `HIGH`

### Get Template

```
GET https://modelarmor.{LOCATION}.rep.googleapis.com/v1/projects/{PROJECT_NUMBER}/locations/{LOCATION}/templates/{TEMPLATE_ID}
```

---

## Error Codes

| HTTP Status | Error | Retryable | Action |
|-------------|-------|-----------|--------|
| 200/201 | Success | N/A | Parse response |
| 400 | `FAILED_PRECONDITION` | No | Fix agent config or data store |
| 400 | Other | Yes | Retry with backoff |
| 403 | `PERMISSION_DENIED` | No | Check IAM roles, OAuth, `X-Goog-User-Project` |
| 404 | `NOT_FOUND` | No | Verify resource path |
| 409 | `ALREADY_EXISTS` | No | Safe to ignore on create |
| 429 | `RESOURCE_EXHAUSTED` | Yes | Exponential backoff (min 4s, max 120s) |
| 500 | `INTERNAL` | Yes | Retry with backoff |
| 502 | `BAD_GATEWAY` | Yes | Retry with backoff |
| 503 | `UNAVAILABLE` | Yes | Retry with backoff |
| 504 | `DEADLINE_EXCEEDED` | Yes | Retry with backoff |

**Recommended retry config:** 10 attempts, exponential backoff (multiplier=2, min=4s, max=120s).
