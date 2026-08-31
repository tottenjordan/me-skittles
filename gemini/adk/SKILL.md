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

## ADK 2.x

ADK 2.0 added the **Workflow Runtime**, moving execution from a hierarchical agent executor to a
graph engine where agents, tools, and functions are nodes. `google.adk.Workflow` is a graph-based
node wired with explicit `edges`.

**Everything in this skill still works on 2.x** — `Agent`, `LlmAgent`, `SequentialAgent`,
`ParallelAgent`, `LoopAgent`, `Runner`, `ToolContext`, and `InMemorySessionService` were all
verified importable against `google-adk==2.8.0`. The graph runtime is an addition, not a
replacement.

Breaking changes that matter if you are upgrading from 1.x:

| Change | What to do |
|---|---|
| `Event` gained `node_info` and `output` | A custom `BaseSessionService` backed by rigid SQL columns needs a schema update |
| Tools that swallow exceptions | Let exceptions propagate — a broad `except Exception:` disables automatic retries, and catching `BaseException` traps `NodeInterruptedError` and breaks human-in-the-loop pauses |
| Manual `session.events.append(...)` | `yield` the event from your node or agent instead; the runner needs control of emission for routing and streaming |
| Custom `run()` overrides | Move the logic into `BeforeAgentCallback` / `AfterAgentCallback` |
| Session compatibility | 2.0 sessions are readable by 1.28+, but not by older 1.x |

Full migration guide: [adk.dev/2.0](https://adk.dev/2.0/)

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
    model="gemini-flash-latest",
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
| `model` | Yes | LLM model (e.g., `gemini-flash-latest`) |
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
    model="gemini-flash-latest",
    instruction="Greet the user. Their name is {user_name}.",
    tools=[]
)
```

Variables are resolved from session state at runtime.

> **Pin the model on regional endpoints.** `gemini-flash-latest` resolves fine for local
> development, but ADK's docs note the `-latest` aliases may not resolve when
> `GOOGLE_CLOUD_LOCATION` is a region such as `us-central1`. Use an explicit version there —
> the `agent-engine` skill pins `gemini-3.7-flash` for this reason.

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
    model="gemini-flash-latest",
    instruction="You are a specialist.",
    tools=[specialist_tool]
)

manager_agent = Agent(
    name="manager",
    model="gemini-flash-latest",
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
    model="gemini-flash-latest",
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

**[references/state_management.md](references/state_management.md)** - Session and state handling:

- `session.state` scopes (`user:`, `app:`, `temp:`) and when each persists
- `output_key` vs explicit state writes
- State propagation across sub-agents and workflow agents
- Known Agent Engine limitations and workarounds

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

## Dependencies

```
google-adk
google-adk[a2a]  # For A2A support
```

## Advanced patterns

Search-tool selection (`DiscoveryEngineSearchTool` vs `VertexAiSearchTool`), the
config-driven design pattern, keeping tool output under the token ceiling, Memory Bank
via `PreloadMemoryTool`, and assorted common patterns:
**[references/advanced_patterns.md](references/advanced_patterns.md)**

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
