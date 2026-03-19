---
name: adk
description: Build AI agents using Google's Agent Development Kit (ADK). Use when creating LLM agents with tools, building workflow agents (Sequential, Parallel, Loop), composing multi-agent systems, or developing custom agents. Covers agent creation patterns, function tools, agent configuration, session management, and running agents locally with CLI or web interface.
---

# Agent Development Kit (ADK)

Build AI agents with Google's ADK framework.

## Quick Reference

| Task | Pattern |
|------|---------|
| Install ADK | `pip install google-adk` |
| Create project | `adk create my_agent` |
| Run agent (CLI) | `adk run my_agent` |
| Run agent (Web) | `adk web --port 8000` |
| Create LLM agent | `Agent(name, model, instruction, tools)` |

## Installation

```bash
# Requires Python 3.10+
pip install google-adk

# For A2A support
pip install google-adk[a2a]
```

## Project Structure

```
my_agent/
├── __init__.py
├── agent.py      # Main agent with root_agent
└── .env          # API keys (GOOGLE_API_KEY or Vertex AI config)
```

Create with: `adk create my_agent`

## Creating Agents

### LLM Agent with Tools

```python
from google.adk.agents.llm_agent import Agent

def get_weather(city: str) -> dict:
    """Gets the current weather for a city.

    Args:
        city: The city name to get weather for.
    """
    return {"status": "success", "city": city, "temp": "72F", "condition": "sunny"}

def calculate(expression: str) -> dict:
    """Evaluates a mathematical expression.

    Args:
        expression: The math expression to evaluate.
    """
    try:
        result = eval(expression)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

root_agent = Agent(
    name="assistant_agent",
    model="gemini-2.0-flash",
    description="A helpful assistant that can check weather and do math.",
    instruction="""You are a helpful assistant.
    Use get_weather when asked about weather.
    Use calculate for math questions.
    Be concise and friendly.""",
    tools=[get_weather, calculate]
)
```

### Agent Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `name` | Yes | Unique identifier |
| `model` | Yes | LLM model (e.g., `gemini-2.0-flash`) |
| `instruction` | Yes | Agent behavior and personality |
| `description` | No | Summary of capabilities |
| `tools` | No | List of functions/tools |
| `sub_agents` | No | Child agents for delegation |
| `output_key` | No | Store response in session state |
| `input_schema` | No | Pydantic model for structured input |
| `output_schema` | No | Pydantic model for structured output |

### Dynamic Instructions

Use variables in instructions:

```python
root_agent = Agent(
    name="greeter",
    model="gemini-2.0-flash",
    instruction="Greet the user. Their name is {user_name}.",
    tools=[]
)
```

Variables are resolved from session state at runtime.

## Function Tools

Tools let agents interact with external systems.

### Tool Requirements

1. Type hints for all parameters
2. Docstring with description and Args section
3. Return a dict (recommended) or simple type

```python
def search_database(query: str, limit: int = 10) -> dict:
    """Searches the database for matching records.

    Args:
        query: The search query string.
        limit: Maximum number of results to return.
    """
    results = do_search(query, limit)
    return {"status": "success", "count": len(results), "results": results}
```

### Tool Context

Access session state and actions within tools:

```python
from google.adk.tools.tool_context import ToolContext

def get_user_preference(key: str, tool_context: ToolContext) -> dict:
    """Gets a user preference from session state.

    Args:
        key: The preference key to retrieve.
    """
    value = tool_context.state.get(key)
    return {"key": key, "value": value}
```

### Transfer Tool (for Multi-Agent)

```python
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

def transfer_to_agent(agent_name: str, tool_context: ToolContext) -> None:
    """Transfer to another agent."""
    tool_context.actions.transfer_to_agent = agent_name
```

## Workflow Agents

### Sequential Agent

Execute steps in order:

```python
from google.adk.agents.sequential_agent import SequentialAgent

pipeline = SequentialAgent(
    name="data_pipeline",
    sub_agents=[fetch_agent, process_agent, store_agent]
)
```

### Parallel Agent

Execute steps concurrently:

```python
from google.adk.agents.parallel_agent import ParallelAgent

parallel_search = ParallelAgent(
    name="multi_search",
    sub_agents=[search_web, search_db, search_cache]
)
```

### Loop Agent

Repeat until condition:

```python
from google.adk.agents.loop_agent import LoopAgent

retry_agent = LoopAgent(
    name="retry_logic",
    sub_agents=[attempt_agent, check_result_agent],
    max_iterations=3
)
```

## Multi-Agent Composition

### Sub-Agents

```python
specialist_agent = Agent(
    name="specialist",
    model="gemini-2.0-flash",
    instruction="You are a specialist.",
    tools=[specialist_tool]
)

manager_agent = Agent(
    name="manager",
    model="gemini-2.0-flash",
    instruction="Delegate specialist tasks to the specialist agent.",
    tools=[transfer_tool],
    sub_agents=[specialist_agent]
)
```

## Running Agents

### Command Line

```bash
# Interactive CLI
adk run my_agent

# With specific model
adk run my_agent --model gemini-2.5-flash
```

### Web Interface

```bash
# Start web UI
adk web --port 8000

# With specific agent
adk web my_agent --port 8000
```

### Programmatic

```python
from google.adk import Runner
from google.adk.sessions import InMemorySessionService

runner = Runner(
    app_name="my_app",
    agent=root_agent,
    session_service=InMemorySessionService()
)

# Run async
async for event in runner.run_async(
    session_id="session-1",
    user_id="user-1",
    new_message=types.Content(role="user", parts=[types.Part(text="Hello")])
):
    if event.is_final_response():
        print(event.content)
```

## Session State

Store and retrieve data across turns:

```python
def save_preference(key: str, value: str, tool_context: ToolContext) -> dict:
    """Saves a user preference.

    Args:
        key: The preference key.
        value: The preference value.
    """
    tool_context.state[key] = value
    return {"status": "saved", "key": key}

def get_preference(key: str, tool_context: ToolContext) -> dict:
    """Gets a user preference.

    Args:
        key: The preference key.
    """
    return {"key": key, "value": tool_context.state.get(key)}
```

## Structured Output

Use Pydantic for typed responses:

```python
from pydantic import BaseModel

class WeatherReport(BaseModel):
    city: str
    temperature: float
    condition: str
    humidity: int

root_agent = Agent(
    name="weather_agent",
    model="gemini-2.0-flash",
    instruction="Provide weather information as structured data.",
    output_schema=WeatherReport
)
```

## Advanced Topics

For detailed information on advanced ADK patterns, agent composition strategies, and complex multi-agent systems, see:

**[references/advanced_patterns.md](references/advanced_patterns.md)** - Comprehensive ADK reference including:
- Advanced workflow patterns (coordinator, pipeline, hierarchical)
- Tool development best practices
- Custom agent classes
- Security patterns and guardrails
- Evaluation and testing strategies
- Complete multi-tier examples

## Environment Configuration

### Google AI (Gemini API)

```bash
# .env
GOOGLE_API_KEY="your-api-key"
```

### Vertex AI

```bash
# .env
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"
GOOGLE_GENAI_USE_VERTEXAI="1"
```

## Common Patterns

### Error Handling in Tools

```python
def safe_operation(data: str) -> dict:
    """Performs an operation safely.

    Args:
        data: The input data.
    """
    try:
        result = risky_operation(data)
        return {"status": "success", "result": result}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": "Unexpected error occurred"}
```

### Agent with Context

```python
root_agent = Agent(
    name="context_aware",
    model="gemini-2.0-flash",
    instruction="""You are a helpful assistant.

    Context:
    - Current user: {user_name}
    - User preferences: {preferences}

    Use this context to personalize responses.""",
    tools=[get_data, update_data]
)
```

## Dependencies

```
google-adk
google-adk[a2a]  # For A2A support
```

## DiscoveryEngineSearchTool vs VertexAiSearchTool

**Use `DiscoveryEngineSearchTool` when the agent has sub-agents or mixed tool types.**

`VertexAiSearchTool` adds a built-in Gemini retrieval tool that **cannot coexist** with function tools like `transfer_to_agent` (injected by sub-agents). Use `DiscoveryEngineSearchTool` instead — it wraps the Discovery Engine SearchService REST API as a regular `FunctionTool`, avoiding this conflict.

```python
from google.adk.tools.discovery_engine_search_tool import DiscoveryEngineSearchTool
from google.cloud import discoveryengine_v1beta as discoveryengine

# Restrict to specific data stores to avoid pulling in workspace connectors
search_tool = DiscoveryEngineSearchTool(
    search_engine_id=f"projects/{project}/locations/global/collections/default_collection/engines/{engine}",
    data_store_specs=[
        discoveryengine.SearchRequest.DataStoreSpec(
            data_store=f"projects/{project}/locations/global/collections/default_collection/dataStores/sop-store"
        ),
    ],
)

root_agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    tools=[search_tool],           # Works alongside transfer tools
    sub_agents=[analytics_agent],  # Sub-agents inject transfer_to_agent
)
```

**Critical**: Always specify `data_store_specs` to restrict which data stores are searched. If an engine has workspace connectors (Gmail, Calendar, Jira) attached, they inflate the token count — a single engine with 9 data stores can push input tokens above the 1M context limit.

## Config-Driven Design Pattern

Avoid hardcoding project IDs, retailer names, or model names. Use a central YAML config with env var overrides for deployment:

```python
import os
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"

def _load_config():
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)

    # Env var overrides for Agent Engine deployment
    if os.environ.get("RETAILER_NAME"):
        config.setdefault("retailer", {})["name"] = os.environ["RETAILER_NAME"]
    if os.environ.get("ADK_MODEL"):
        config.setdefault("models", {})["adk"] = os.environ["ADK_MODEL"]

    config.setdefault("models", {})
    config["models"].setdefault("adk", "gemini-2.5-flash")
    return config
```

This lets the same agent code run locally and on Agent Engine without code changes.

## Tool Output Size — Avoid Token Overflow

**Never return large binary data (images, PDFs) as base64 in tool responses.** A single image encoded as base64 is ~400K-1.5M tokens, which gets stored in session history and causes context overflow on subsequent turns.

Instead, upload to GCS and return a URI:

```python
def generate_image(product_name: str) -> dict:
    # ... generate image_bytes ...
    from google.cloud import storage
    client = storage.Client(project=project_id)
    bucket = client.bucket(gcs_bucket)
    blob = bucket.blob(f"images/{product_name}.png")
    blob.upload_from_string(image_bytes, content_type="image/png")
    return {
        "status": "success",
        "image_uri": f"gs://{gcs_bucket}/images/{product_name}.png",
    }
```

## Memory Bank (PreloadMemoryTool)

For cross-session personalization, add `PreloadMemoryTool` to the root agent. It auto-loads user memories at conversation start. Memory Bank is **auto-enabled** on Agent Engine when ADK >= 1.5.0.

```python
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

root_agent = Agent(
    name="assistant",
    model="gemini-2.5-flash",
    tools=[search_tool, PreloadMemoryTool()],
    sub_agents=[analytics_agent],
)
```

To generate memories after a session, call `memory_service.add_session_to_memory(session)` explicitly — `PreloadMemoryTool` only reads.

## ADK Evaluations

Run evals against deployed agents using the `genai.Client().evals` API:

```python
from google import genai
from google.genai import types

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

eval_cases = [
    types.EvalCase(
        eval_case_id="test_1",
        conversation_scenario=types.ConversationScenario(
            starting_prompt="Run a simulation of 3 shoppers",
            conversation_plan="Ask about endcap conversion rates",
        ),
    ),
]

eval_set = types.EvalSet(eval_set_id="my_eval", eval_cases=eval_cases)

# Step 1: Run inference
result = client.evals.run_inference(agent=agent_resource, eval_set=eval_set,
    config=types.RunInferenceConfig(eval_run_id="run_1"))

# Step 2: Evaluate
evaluation = client.evals.evaluate(
    eval_set=result,
    metrics=[
        types.EvalMetric(metric_name="rubric_based_final_response_quality_v1"),
        types.EvalMetric(metric_name="tool_use_quality_v1"),
    ],
    config=types.EvaluateConfig(eval_run_id="run_1"),
)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tool not called | Check docstring has Args section with descriptions |
| Import error | Ensure `google-adk` is installed |
| API key error | Set `GOOGLE_API_KEY` in `.env` |
| Model not found | Use valid model name like `gemini-2.5-flash` |
| State not persisting | Use `tool_context.state` not local variables |
| Token overflow (>1M) | Check data store count on engine; remove workspace connectors |
| Image tool causes overflow | Upload to GCS, return URI instead of base64 |
| VertexAiSearchTool + sub-agents fails | Use `DiscoveryEngineSearchTool` instead |
| Sub-agents not called | Verify `description` field is set on sub-agents |
