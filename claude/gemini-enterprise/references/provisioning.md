# Discovery Engine Provisioning Guide

Step-by-step guide for provisioning a complete Discovery Engine setup with data stores, document ingestion, and Model Armor.

## Prerequisites

- `gcloud` CLI authenticated (`gcloud auth login`)
- Sufficient IAM permissions (`roles/discoveryengine.admin`)
- A GCP project with billing enabled

## Step 1: Enable APIs

```bash
PROJECT_ID="your-project-id"

# Discovery Engine API (required)
gcloud services enable discoveryengine.googleapis.com --project="${PROJECT_ID}"

# Model Armor API (optional, for content safety)
gcloud services enable modelarmor.googleapis.com --project="${PROJECT_ID}"
```

## Step 2: Set Up Variables

```bash
LOCATION="global"
ENGINE_ID="my-engine"
GCS_BUCKET="${PROJECT_ID}-docs"
TOKEN=$(gcloud auth print-access-token)

# Build base URL
if [ "${LOCATION}" = "global" ]; then
  API_ENDPOINT="https://discoveryengine.googleapis.com"
else
  API_ENDPOINT="https://${LOCATION}-discoveryengine.googleapis.com"
fi

BASE_URL="${API_ENDPOINT}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection"
```

## Step 3: Upload Documents to GCS

```bash
# Create bucket
gsutil mb -p "${PROJECT_ID}" -l US "gs://${GCS_BUCKET}"

# Upload documents (example: PDFs)
gsutil -m cp ./docs/sops/*.pdf "gs://${GCS_BUCKET}/sops/"
gsutil -m cp ./docs/brand/*.pdf "gs://${GCS_BUCKET}/brand_guidelines/"
```

## Step 4: Create Data Stores

Create one data store per content type. Data stores must exist before the engine is created.

```bash
# SOP data store
curl -s -X POST \
  "${BASE_URL}/dataStores?dataStoreId=sop-store" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "Standard Operating Procedures",
    "industryVertical": "GENERIC",
    "contentConfig": "CONTENT_REQUIRED",
    "solutionTypes": ["SOLUTION_TYPE_CHAT"]
  }'

# Brand guidelines data store
curl -s -X POST \
  "${BASE_URL}/dataStores?dataStoreId=brand-guidelines-store" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "Brand Guidelines",
    "industryVertical": "GENERIC",
    "contentConfig": "CONTENT_REQUIRED",
    "solutionTypes": ["SOLUTION_TYPE_CHAT"]
  }'

echo "Waiting for data stores to initialize..."
sleep 10
```

## Step 5: Create JSONL Metadata (Optional)

JSONL metadata files provide structured metadata (title, category) alongside document URIs. Without metadata, documents are imported with auto-generated IDs.

```python
# generate_metadata.py
import json
import subprocess

bucket = "your-bucket"
prefix = "sops/"

uris = subprocess.check_output(
    ["gsutil", "ls", f"gs://{bucket}/{prefix}"],
    text=True
).strip().split("\n")

for i, uri in enumerate(uris):
    if uri.endswith(".pdf"):
        doc = {
            "id": f"sop-{i+1}",
            "content": {"mimeType": "application/pdf", "uri": uri},
            "structData": {
                "title": uri.split("/")[-1].replace(".pdf", ""),
                "category": "sop"
            }
        }
        print(json.dumps(doc))
```

```bash
python generate_metadata.py > /tmp/sop_metadata.jsonl
gsutil cp /tmp/sop_metadata.jsonl "gs://${GCS_BUCKET}/metadata/sop_metadata.jsonl"
```

## Step 6: Import Documents

```bash
# Import with JSONL metadata
curl -s -X POST \
  "${BASE_URL}/dataStores/sop-store/branches/default_branch/documents:import" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "gcsSource": {
      "inputUris": ["gs://'"${GCS_BUCKET}"'/metadata/sop_metadata.jsonl"],
      "dataSchema": "document"
    },
    "reconciliationMode": "FULL"
  }'

# Import with wildcard (no metadata)
curl -s -X POST \
  "${BASE_URL}/dataStores/brand-guidelines-store/branches/default_branch/documents:import" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "gcsSource": {
      "inputUris": ["gs://'"${GCS_BUCKET}"'/brand_guidelines/*"]
    },
    "reconciliationMode": "FULL"
  }'

echo "Waiting for document import and indexing (this may take several minutes)..."
sleep 90
```

**Important:** Document import is a long-running operation. The documents are not searchable until indexing completes. Check the operation status in the GCP console or via the LRO endpoint.

## Step 7: Create Engine

The engine references data stores by ID. All referenced data stores must already exist.

```bash
curl -s -X POST \
  "${BASE_URL}/engines?engineId=${ENGINE_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "'"${ENGINE_ID}"'",
    "solutionType": "SOLUTION_TYPE_SEARCH",
    "dataStoreIds": ["sop-store", "brand-guidelines-store"],
    "searchEngineConfig": {
      "searchTier": "SEARCH_TIER_ENTERPRISE",
      "searchAddOns": ["SEARCH_ADD_ON_LLM"]
    },
    "industryVertical": "GENERIC",
    "appType": "APP_TYPE_INTRANET"
  }'
```

## Step 8: Create Default Assistant

The assistant enables the `streamAssist` conversational endpoint.

```bash
curl -s -X POST \
  "${BASE_URL}/engines/${ENGINE_ID}/assistants?assistantId=default_assistant" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "Default Assistant"
  }'
```

## Step 9: Configure Model Armor (Optional)

### 9a: Create Model Armor Template

```bash
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')
ARMOR_LOCATION="us"  # Use 'us' multi-region for global engines
TEMPLATE_ID="my-armor-template"

curl -s -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://modelarmor.${ARMOR_LOCATION}.rep.googleapis.com/v1/projects/${PROJECT_NUMBER}/locations/${ARMOR_LOCATION}/templates?templateId=${TEMPLATE_ID}" \
  -d '{
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
        "basicConfig": {"filterEnforcement": "ENABLED"}
      },
      "maliciousUriFilterSettings": {
        "filterEnforcement": "ENABLED"
      }
    }
  }'
```

**Required IAM:** `roles/modelarmor.admin`

**Location note:** Use `us` multi-region for global Discovery Engine instances. Regional endpoints (e.g., `us-central1`) cannot be applied to global assistants.

### 9b: Apply Model Armor to Assistant

```bash
TEMPLATE_PATH="projects/${PROJECT_NUMBER}/locations/${ARMOR_LOCATION}/templates/${TEMPLATE_ID}"

curl -s -X PATCH \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines/${ENGINE_ID}/assistants/default_assistant?update_mask=customerPolicy" \
  -d "{
    \"customerPolicy\": {
      \"modelArmorConfig\": {
        \"userPromptTemplate\": \"${TEMPLATE_PATH}\",
        \"responseTemplate\": \"${TEMPLATE_PATH}\",
        \"failureMode\": \"FAIL_OPEN\"
      }
    }
  }"
```

## Step 10: Register External Agent (Optional)

Register an A2A or Cloud Run agent to handle specific queries via StreamAssist.

```bash
AGENT_ENDPOINT="https://my-agent-abc123-uc.a.run.app"

curl -s -X POST \
  "${BASE_URL}/engines/${ENGINE_ID}/assistants/default_assistant/agents?agentId=my-external-agent" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "My External Agent",
    "agentEndpoint": {
      "endpointUri": "'"${AGENT_ENDPOINT}"'"
    }
  }'
```

## Verification

After provisioning, verify the setup:

```bash
# Check data stores
curl -s "${BASE_URL}/dataStores" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" | python3 -m json.tool

# Check engine
curl -s "${BASE_URL}/engines/${ENGINE_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" | python3 -m json.tool

# Test search
curl -s -X POST \
  "${BASE_URL}/engines/${ENGINE_ID}/servingConfigs/default_config:search" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{"query": "test query", "pageSize": 3}' | python3 -m json.tool

# Test StreamAssist (auto-session)
curl -s -X POST \
  "${BASE_URL}/engines/${ENGINE_ID}/assistants/default_assistant:streamAssist" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "session": "projects/'"${PROJECT_ID}"'/locations/'"${LOCATION}"'/collections/default_collection/engines/'"${ENGINE_ID}"'/sessions/-",
    "query": {"text": "Hello, what can you help me with?"}
  }' | python3 -m json.tool
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Engine creation fails | Data stores don't exist yet | Create data stores first |
| Documents not searchable | Indexing still in progress | Wait for import LRO to complete |
| `PERMISSION_DENIED` | Missing IAM role | Grant `roles/discoveryengine.admin` |
| Model Armor template fails | Org policy blocks location | Update `constraints/gcp.resourceLocations` |
| StreamAssist returns empty | No assistant created | Create `default_assistant` on the engine |
| 403 on workspace data store | Service account can't access user data | Use user OAuth or exclude from `data_store_specs` |
