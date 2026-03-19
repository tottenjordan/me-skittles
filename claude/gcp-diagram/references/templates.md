# GCP Diagram Prompt Templates

Pre-built prompts for common GCP architecture diagram types. Each template produces a clean, professional diagram in the style of official Google Cloud documentation.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Multi-Agent Architecture](#multi-agent-architecture)
3. [Data Flow / Request Processing](#data-flow)
4. [Database Schema (Star/Snowflake)](#database-schema)
5. [MCP / Tool Integration](#tool-integration)
6. [Deployment Architecture](#deployment-architecture)
7. [Security / Safety Layer](#security-layer)
8. [Microservices Architecture](#microservices)

---

## System Architecture

High-level overview showing all major components and their interactions.

```
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.

Title: "{TITLE}"

The diagram should show these components connected by clean arrows:

TOP ROW (Entry Points):
{LIST_ENTRY_POINTS}

MIDDLE ROW (Core Platform):
{LIST_CORE_SERVICES}

BOTTOM ROW (Backend Services):
{LIST_BACKEND_SERVICES}

Use Google Cloud product icon style. Clean lines, no 3D effects, modern flat
design. Landscape orientation. Include the Google Cloud logo watermark at
bottom left.
```

**Customization points**: Replace `{TITLE}`, `{LIST_ENTRY_POINTS}`, `{LIST_CORE_SERVICES}`, `{LIST_BACKEND_SERVICES}` with your architecture's components.

---

## Multi-Agent Architecture

Shows agent hierarchy with tool routing and sub-agent delegation.

```
Generate a professional architecture diagram in Google Cloud Platform
documentation style. Clean white background, GCP brand colors.

Title: "{TITLE}"
Subtitle: "{SUBTITLE}"

Show a hierarchical agent architecture:

TOP: "User Query" (red ellipse)

CENTER: "{ROOT_AGENT_NAME}" (large blue box, labeled "Root Agent / LlmAgent"):
- Model: {MODEL_NAME}
- Tools: {ROOT_TOOLS}

{FOR_EACH_SUB_AGENT}
BRANCH: "{SUB_AGENT_NAME}" ({COLOR} box, labeled "Sub-Agent"):
  - Model: {MODEL_NAME}
  - Tool: {TOOL_NAME} (FunctionTool)
  - Connects to: {BACKEND_SERVICE}
{END_FOR_EACH}

Show transfer_to_agent arrows between root and sub-agents (bold arrows).
Show return arrows (dashed) for results flowing back.

Clean flat design, Google Cloud product icons. Landscape orientation.
```

---

## Data Flow

Step-by-step request processing from user input to grounded response.

```
Generate a professional data flow diagram in Google Cloud Platform
documentation style. Clean white background, GCP brand colors.

Title: "{TITLE}"
Subtitle: "From {INPUT} Through {PROCESSING} to {OUTPUT}"

Show a top-to-bottom flow with numbered steps:

Step 1: "{INPUT_DESCRIPTION}" (red ellipse at top)

Step 2: "Request Entry Points" (gray box):
{LIST_ENTRY_POINTS}

Step 3: "Processing / Orchestration" (green box):
{PROCESSING_DESCRIPTION}

Step 4 (parallel paths, color-coded):
{FOR_EACH_PATH}
- Path {N}: {PATH_NAME} ({COLOR}): {PATH_STEPS}
{END_FOR_EACH}

Step 5: "Response Assembly" (green box)

Step 6: "{OUTPUT_DESCRIPTION}" (red ellipse at bottom)

Clean flowchart style with color-coded paths. Google Cloud aesthetic.
```

---

## Database Schema

Star schema, snowflake, or relational database diagrams.

```
Generate a professional database schema diagram in Google Cloud Platform
documentation style. Clean white background with orange (#F9AB00) accents.

Title: "{TITLE}"
Subtitle: "{DATASET_PATH}"

Show a {SCHEMA_TYPE} schema with:

CENTER: "{FACT_TABLE}" (large orange box with bold border):
- {ROW_COUNT} rows
- Columns: {COLUMN_LIST}

SURROUNDING DIMENSIONS (connected by FK arrows):
{FOR_EACH_DIMENSION}
- "{DIM_TABLE}" ({ROW_COUNT} rows):
  Columns: {COLUMN_LIST}
  {OPTIONAL_NOTES}
{END_FOR_EACH}

Show FK arrows with column names. BigQuery icon at top.
Clean, professional database diagram style.
```

---

## Tool Integration

Shows how an agent connects to external tools/APIs via MCP or other protocols.

```
Generate a professional architecture diagram in Google Cloud Platform
documentation style. Clean white background, GCP brand colors.

Title: "{TITLE}"
Subtitle: "{SUBTITLE}"

Show a LEFT-TO-RIGHT flow:

LEFT: "Agent" (green box):
- {AGENT_NAME}
- {MODEL_NAME}
- {AGENT_DESCRIPTION}

CENTER: "{MIDDLEWARE}" (blue box):
- {MIDDLEWARE_DESCRIPTION}
- Tools: {TOOL_LIST}

RIGHT: "{BACKEND}" (orange cylinder):
- {BACKEND_DESCRIPTION}

Connections:
- Agent to Middleware: "{PROTOCOL}" (bold blue arrow)
- Middleware to Backend: "{API_TYPE}" (bold orange arrow)

Clean horizontal flow. Google Cloud product icons.
```

---

## Deployment Architecture

Shows deployment targets, regions, and service mesh.

```
Generate a professional deployment architecture diagram in Google Cloud
Platform documentation style. Clean white background, GCP brand colors.

Title: "Deployment Architecture"
Subtitle: "{SUBTITLE}"

Show:

TOP: "Client" — {CLIENT_DESCRIPTION}

MIDDLE ROW (deployment targets):
{FOR_EACH_TARGET}
{N}. "{SERVICE_NAME}" ({COLOR} box, {REGION}):
   {SERVICE_DETAILS}
{END_FOR_EACH}

BOTTOM ROW (backend services):
{LIST_BACKENDS}

Show connections between all components.
Clean flat design, Google Cloud icons. Landscape orientation.
```

---

## Security Layer

Shows content safety, auth, or security architecture.

```
Generate a professional architecture diagram in Google Cloud Platform
documentation style. Clean white background.

Title: "{TITLE}"
Subtitle: "{SUBTITLE}"

Show the security/safety flow:

INPUT: "{INPUT}" with user request

SCREENING LAYER: "{SCREEN_NAME}" (red-themed):
- {FILTER_1}
- {FILTER_2}
- {FILTER_N}
- Failure Mode: {FAIL_MODE}

PROCESSING: "{PROCESSOR}" (blue/green themed)

OUTPUT SCREENING: Same filters applied to response

OUTPUT: Filtered response to user

Show bidirectional screening flow. Professional GCP documentation style.
```

---

## Microservices

Cloud Run / GKE microservices with service mesh.

```
Generate a professional microservices architecture diagram in Google Cloud
Platform documentation style. Clean white background, GCP brand colors.

Title: "{TITLE}"

Show a service mesh with:

LOAD BALANCER: Cloud Load Balancing (top)

SERVICES (middle, arranged in grid):
{FOR_EACH_SERVICE}
- "{SERVICE_NAME}" (Cloud Run/GKE box):
  - Port: {PORT}
  - {DESCRIPTION}
{END_FOR_EACH}

BACKING SERVICES (bottom):
{LIST_DATABASES_AND_QUEUES}

Show service-to-service connections with protocol labels.
Include Cloud Armor / IAP at the ingress layer.
Google Cloud product icons. Clean layout.
```
