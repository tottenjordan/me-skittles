# Google Agent Development Kit (ADK) - Comprehensive Reference

## Table of Contents
1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Agent Types & Patterns](#agent-types--patterns)
4. [Tool Development](#tool-development)
5. [Multi-Agent Architecture](#multi-agent-architecture)
6. [Advanced Configuration](#advanced-configuration)
7. [Session & State Management](#session--state-management)
8. [Deployment Strategies](#deployment-strategies)
9. [Safety & Security](#safety--security)
10. [Evaluation & Testing](#evaluation--testing)
11. [Code Examples](#code-examples)

---

## Overview

The Agent Development Kit (ADK) is a framework for building, deploying, and managing AI agents across multiple platforms and models.

### Key Features
- **Model Agnostic**: Supports Gemini, Claude (Anthropic), Vertex AI, and other LLM providers
- **Flexible Agent Orchestration**: LLM agents, workflow agents (Sequential, Parallel, Loop), and custom agents
- **Multi-Language Support**: Python, TypeScript, Go, Java
- **Deployment Options**: Local, Vertex AI Agent Engine, Cloud Run, GKE, containerized environments
- **A2A Protocol Support**: Built-in Agent-to-Agent communication protocol integration

### Installation

```bash
# Python (requires Python 3.10+)
pip install google-adk

# With A2A support
pip install google-adk[a2a]

# TypeScript
npm install @google/adk

# Go
go get google.golang.org/adk
```

### Project Creation

```bash
# Create new agent project
adk create my_agent

# Run agent (CLI)
adk run my_agent

# Run agent (Web UI)
adk web --port 8000

# Run API server
adk api_server
```

---

## Core Concepts

### Agent Hierarchy
- Agents can have parent-child relationships
- Each agent can only have one parent
- Enables structured composition and delegation

### Agent Execution Model
- **Event Loop**: Manages agent execution cycle
- **InvocationContext**: Carries state and history through agent calls
- **Resume Capabilities**: Allows pausing and resuming agent states

### State Management
- **Session State**: Shared dictionary accessible across agents
- **Output Keys**: Automatic state saving using `output_key` parameter
- **Context Persistence**: State persists across multi-turn conversations

---

## Agent Types & Patterns

### 1. LLM Agents

LLM Agents use Large Language Models for reasoning, decision-making, and tool interaction. They have non-deterministic behavior driven by the model's reasoning capabilities.

#### Core Configuration

```python
from google.adk.agents.llm_agent import Agent

agent = Agent(
    name="assistant_agent",                    # Required: Unique identifier
    model="gemini-2.0-flash",                  # Required: Model specification
    description="A helpful assistant",         # Optional but recommended
    instruction="You are a helpful assistant", # Agent persona and behavior
    tools=[tool_func_1, tool_func_2],         # Functions/tools agent can use
    sub_agents=[sub_agent_1, sub_agent_2],    # Child agents for delegation
)
```

#### Advanced Configuration Parameters

```python
agent = Agent(
    name="advanced_agent",
    model="gemini-2.5-flash",

    # Instructions (supports dynamic state injection)
    instruction="You are an agent for {user_name}",  # {var} replaced from state
    global_instruction="Global context for all agents",
    static_instruction="Static context (files, images, etc.)",

    # Input/Output Schema
    input_schema=InputModel,      # Pydantic BaseModel for input validation
    output_schema=OutputModel,     # Pydantic BaseModel for output structure
    output_key="result",          # Auto-save response to state["result"]

    # Advanced Features
    planner=BuiltInPlanner(),     # Enable multi-step reasoning
    code_executor=CodeExecutor(),  # Allow code execution
    generate_content_config=GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=2048
    ),

    # Agent Transfer Control
    disallow_transfer_to_parent=False,  # Allow/prevent parent delegation
    disallow_transfer_to_peers=False,   # Allow/prevent peer delegation
    include_contents='default',         # 'default' or 'none'

    # Callbacks
    before_agent_callback=before_callback,
    after_agent_callback=after_callback,
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    on_model_error_callback=error_callback,
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
    on_tool_error_callback=tool_error_callback,
)
```

#### LLM Agent Best Practices
1. **Be Specific in Instructions**: Provide clear, detailed guidance
2. **Use Examples**: Include example interactions in instructions
3. **Clear Tool Descriptions**: Write detailed docstrings for tools
4. **Appropriate Model Selection**: Choose model based on task complexity
5. **Structured Outputs**: Use `output_schema` for consistent responses
6. **State Variables**: Use `{var}` syntax for dynamic instruction content

### 2. Workflow Agents

Workflow agents provide deterministic, structured execution patterns without LLM reasoning.

#### 2.1 Sequential Agents

Execute sub-agents in a fixed order, one after another.

```python
from google.adk.agents.sequential_agent import SequentialAgent

code_pipeline = SequentialAgent(
    name="CodePipelineAgent",
    sub_agents=[
        code_writer_agent,     # Step 1: Generate code
        code_reviewer_agent,   # Step 2: Review code
        code_refactorer_agent  # Step 3: Refactor code
    ]
)
```

**Use Cases:**
- Multi-step workflows with dependencies
- Code development pipelines
- Document processing chains
- Data transformation pipelines

**Key Characteristics:**
- Deterministic execution order
- Shared `InvocationContext` across all sub-agents
- Each agent can access previous outputs via state
- Not powered by LLM

**State Passing Example:**
```python
# Agent 1 saves output
writer = Agent(
    name="writer",
    output_key="generated_code",  # Saves to state["generated_code"]
    # ...
)

# Agent 2 uses output via instruction
reviewer = Agent(
    name="reviewer",
    instruction="Review this code: {generated_code}",  # Reads from state
    # ...
)

pipeline = SequentialAgent(
    name="pipeline",
    sub_agents=[writer, reviewer]
)
```

#### 2.2 Parallel Agents

Execute sub-agents concurrently for independent tasks.

```python
from google.adk.agents.parallel_agent import ParallelAgent

research_agent = ParallelAgent(
    name="ParallelWebResearchAgent",
    sub_agents=[
        researcher_agent_1,  # Runs concurrently
        researcher_agent_2,  # Runs concurrently
        researcher_agent_3   # Runs concurrently
    ],
    description="Runs multiple research tasks in parallel"
)
```

**Use Cases:**
- Multi-source data retrieval
- Independent resource-intensive tasks
- Parallel API calls
- Concurrent document processing

**Key Characteristics:**
- Simultaneous execution of all sub-agents
- Independent execution branches (no automatic state sharing)
- Significantly faster for independent tasks
- Not powered by LLM

**State Management:**
- No automatic conversation history sharing between branches
- Options for explicit communication:
  1. Shared `InvocationContext` (requires manual management)
  2. External state management (databases, message queues)
  3. Post-processing result aggregation

#### 2.3 Loop Agents

Execute sub-agents iteratively until a condition is met.

```python
from google.adk.agents.loop_agent import LoopAgent

refinement_loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[
        critic_agent_in_loop,   # Reviews current version
        refiner_agent_in_loop   # Improves based on feedback
    ],
    max_iterations=5  # Safety limit
)
```

**Use Cases:**
- Iterative document improvement
- Code refinement loops
- Iterative problem solving
- Quality improvement cycles

**Termination Strategies:**
1. **Max Iterations**: Predetermined iteration limit
2. **Condition-Based**:
   - Sub-agents raise custom events
   - Set flags in shared context
   - Return specific completion values

**Best Practices:**
- Always implement an exit strategy
- Use `max_iterations` as a safeguard
- Design clear completion criteria
- Ensure deterministic behavior

### 3. Custom Agents

Custom agents provide ultimate flexibility by inheriting from `BaseAgent`.

```python
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext

class CustomOrchestrator(BaseAgent):
    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> InvocationContext:
        # Implement custom orchestration logic

        # Example: Conditional agent selection
        if ctx.state.get("task_type") == "code":
            ctx = await self.sub_agents[0].run_async(ctx)
        else:
            ctx = await self.sub_agents[1].run_async(ctx)

        # Example: Iterative refinement with custom logic
        for i in range(3):
            ctx = await self.critic_agent.run_async(ctx)
            score = ctx.state.get("quality_score", 0)

            if score >= 8:
                break

            ctx = await self.refiner_agent.run_async(ctx)

        return ctx
```

**Use Cases:**
- Complex conditional workflows
- Dynamic agent selection
- External system integrations
- Custom state management logic

### 4. Remote A2A Agents

Connect to remote agents via Agent-to-Agent (A2A) protocol.

```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# Option 1: Direct AgentCard object
from a2a.protocols.agent_card import AgentCard

remote_agent = RemoteA2aAgent(
    name="remote_pto_agent",
    agent_card=AgentCard(
        base_url="http://localhost:8001",
        # ... other card fields
    )
)

# Option 2: URL to agent card JSON
remote_agent = RemoteA2aAgent(
    name="remote_pto_agent",
    agent_card="http://localhost:8001/.well-known/agent.json"
)

# Option 3: File path to agent card JSON
remote_agent = RemoteA2aAgent(
    name="remote_pto_agent",
    agent_card="/path/to/agent_card.json"
)

# Advanced configuration
remote_agent = RemoteA2aAgent(
    name="remote_agent",
    agent_card=card_url,
    timeout=600.0,  # 10 minutes
    httpx_client=shared_client,  # Optional shared HTTP client
    full_history_when_stateless=False,  # Control history sending
)
```

**Key Features:**
- Automatic agent card resolution
- HTTP client management with proper cleanup
- A2A message conversion and error handling
- Session state management across requests

**Best Practices:**
- Use environment variables for URLs in production
- Implement proper error handling for network failures
- Consider timeout values based on expected operation duration
- Clean up resources with `await agent.cleanup()`

---

## Tool Development

### Basic Function Tools

The simplest way to create tools is using Python functions with docstrings.

```python
def get_weather(city: str, units: str = "celsius") -> dict:
    """Get the current weather for a city.

    Args:
        city: The name of the city.
        units: Temperature units (celsius or fahrenheit).

    Returns:
        A dictionary with weather information.
    """
    # Tool implementation
    return {
        "city": city,
        "temperature": 72,
        "units": units,
        "conditions": "sunny"
    }

# Use in agent
agent = Agent(
    name="weather_agent",
    tools=[get_weather],
    # ...
)
```

### Tool Best Practices

1. **Clear Docstrings**: LLM uses docstrings to understand when and how to use tools
2. **Type Hints**: Use Python type hints for parameter validation
3. **Descriptive Names**: Function names should clearly indicate purpose
4. **Return Structured Data**: Use dictionaries or Pydantic models for returns
5. **Error Handling**: Return error information in structured format

### Advanced Tool Patterns

#### Using ToolContext for State Access

```python
from google.adk.tools.tool_context import ToolContext

def save_user_preference(
    preference: str,
    value: str,
    tool_context: ToolContext
) -> dict:
    """Save a user preference to session state.

    Args:
        preference: The preference name.
        value: The preference value.
        tool_context: Context providing state access.
    """
    # Access session state
    tool_context.state[f"pref_{preference}"] = value

    return {"status": "success", "preference": preference}

# Agent automatically injects ToolContext
agent = Agent(
    name="preferences_agent",
    tools=[save_user_preference],
    # ...
)
```

#### Custom Tool Classes

```python
from google.adk.tools.base_tool import BaseTool

class DatabaseTool(BaseTool):
    def __init__(self, db_connection):
        super().__init__(
            name="query_database",
            description="Query the customer database"
        )
        self.db = db_connection

    async def run(self, query: str, tool_context: ToolContext) -> dict:
        """Execute a database query."""
        # Implement tool logic
        results = await self.db.execute(query)
        return {"results": results}

# Use in agent
db_tool = DatabaseTool(db_connection)
agent = Agent(
    name="db_agent",
    tools=[db_tool],
    # ...
)
```

#### Tool Callbacks for Validation

```python
async def validate_tool_params(
    tool: BaseTool,
    args: dict,
    tool_context: ToolContext
) -> dict | None:
    """Validate tool parameters before execution."""

    # Example: Validate user ID matches session user
    expected_user = tool_context.state.get("session_user_id")
    actual_user = args.get("user_id")

    if actual_user != expected_user:
        return {"error": "User ID mismatch - access denied"}

    # Return None to allow execution
    return None

agent = Agent(
    name="secure_agent",
    tools=[sensitive_tool],
    before_tool_callback=validate_tool_params,
    # ...
)
```

### Transfer Tool Pattern

For agent-to-agent delegation, use transfer tools:

```python
from enum import Enum

class AgentChoice(str, Enum):
    HR = "hr_helper"
    FINANCE = "finance_helper"

def transfer_to_agent(agent_name: AgentChoice) -> dict:
    """Transfer the conversation to a specialized agent.

    Args:
        agent_name: The agent to transfer to.
    """
    return {
        "transfer_to": agent_name.value,
        "message": f"Transferring to {agent_name.value}"
    }

# Use enum to constrain choices
orchestrator = Agent(
    name="orchestrator",
    tools=[transfer_to_agent],
    sub_agents=[hr_agent, finance_agent],
    # ...
)
```

---

## Multi-Agent Architecture

### Interaction Mechanisms

ADK provides three primary mechanisms for multi-agent interaction:

#### 1. Shared Session State

Agents communicate by reading/writing to a shared state dictionary.

```python
# Agent 1: Writes to state
data_collector = Agent(
    name="collector",
    output_key="collected_data",  # Saves response to state
    # ...
)

# Agent 2: Reads from state
data_processor = Agent(
    name="processor",
    instruction="Process this data: {collected_data}",  # Reads from state
    # ...
)

pipeline = SequentialAgent(
    name="data_pipeline",
    sub_agents=[data_collector, data_processor]
)
```

**Best For:**
- Sequential workflows
- Passive data exchange
- Asynchronous communication

#### 2. LLM-Driven Delegation

Agents dynamically route tasks based on agent descriptions and LLM reasoning.

```python
# Specialized agents
greeting_agent = Agent(
    name="greeter",
    description="Handles greetings and welcomes users",
    instruction="Greet the user warmly",
    # ...
)

weather_agent = Agent(
    name="weather",
    description="Provides weather information for cities",
    tools=[get_weather],
    # ...
)

# Orchestrator with automatic delegation
root_agent = Agent(
    name="assistant",
    description="Main assistant that routes requests",
    instruction="Route user requests to appropriate sub-agents based on intent",
    sub_agents=[greeting_agent, weather_agent],
    # LLM automatically chooses which agent to invoke
)
```

**Best For:**
- Dynamic routing
- Intent-based delegation
- Flexible orchestration

#### 3. Explicit Invocation (AgentTool)

Agents are used as callable tools for controlled invocation.

```python
# Sub-agent as tool
analyzer_agent = Agent(
    name="analyzer",
    instruction="Analyze the provided data",
    # ...
)

# Parent agent uses sub-agent as tool
coordinator = Agent(
    name="coordinator",
    tools=[analyzer_agent],  # Agent as tool
    instruction="Use the analyzer when you need data analysis",
    # ...
)
```

**Best For:**
- Hierarchical task decomposition
- Synchronous agent calls
- Controlled execution

### Common Multi-Agent Patterns

#### 1. Coordinator/Dispatcher Pattern

Central agent routes requests to specialized sub-agents.

```python
# Specialized agents
hr_agent = Agent(name="hr", description="HR and PTO queries", ...)
finance_agent = Agent(name="finance", description="Financial reports", ...)
it_agent = Agent(name="it", description="IT support", ...)

# Coordinator
orchestrator = Agent(
    name="orchestrator",
    description="Routes requests to appropriate department",
    instruction="Analyze the user query and delegate to the right department agent",
    sub_agents=[hr_agent, finance_agent, it_agent],
)
```

#### 2. Sequential Pipeline Pattern

Agents execute in fixed order, each building on previous output.

```python
pipeline = SequentialAgent(
    name="content_pipeline",
    sub_agents=[
        research_agent,      # Step 1: Gather information
        writer_agent,        # Step 2: Create content
        editor_agent,        # Step 3: Edit and refine
        fact_checker_agent   # Step 4: Verify accuracy
    ]
)
```

#### 3. Parallel Fan-Out/Gather Pattern

Concurrent execution with result aggregation.

```python
# Multiple data sources queried in parallel
data_gathering = ParallelAgent(
    name="multi_source_data",
    sub_agents=[
        database_agent,
        api_agent,
        file_agent
    ]
)

# Aggregator processes combined results
aggregator = Agent(
    name="aggregator",
    instruction="Combine results from: {database_results}, {api_results}, {file_results}",
    # ...
)

# Combined workflow
workflow = SequentialAgent(
    name="gather_and_process",
    sub_agents=[data_gathering, aggregator]
)
```

#### 4. Hierarchical Task Decomposition

Multi-level agent structure with progressive specialization.

```python
# Level 3: Highly specialized agents
pto_agent = Agent(name="pto", tools=[get_pto_balance], ...)
benefits_agent = Agent(name="benefits", tools=[get_benefits], ...)

# Level 2: Functional agents
hr_agent = Agent(
    name="hr",
    description="Human resources functions",
    sub_agents=[pto_agent, benefits_agent],
    # ...
)

# Level 1: Top-level orchestrator
orchestrator = Agent(
    name="orchestrator",
    description="Enterprise assistant",
    sub_agents=[hr_agent, finance_agent, it_agent],
    # ...
)
```

#### 5. Review/Critique Pattern

Generator creates content, critic reviews and provides feedback.

```python
# Loop agent for iterative improvement
refinement_loop = LoopAgent(
    name="iterative_refinement",
    sub_agents=[
        generator_agent,  # Creates/updates content
        critic_agent      # Reviews and suggests improvements
    ],
    max_iterations=5
)

# With custom termination logic
class QualityControlAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        for i in range(5):
            # Generate
            ctx = await self.generator.run_async(ctx)

            # Critique
            ctx = await self.critic.run_async(ctx)

            # Check quality threshold
            if ctx.state.get("quality_score", 0) >= 8:
                break

        return ctx
```

---

## Advanced Configuration

### Input/Output Schemas

Use Pydantic models for structured input/output validation.

```python
from pydantic import BaseModel, Field

class CityWeatherInput(BaseModel):
    city: str = Field(description="The city name")
    units: str = Field(default="celsius", description="Temperature units")

class WeatherOutput(BaseModel):
    city: str
    temperature: float
    conditions: str
    humidity: int

weather_agent = Agent(
    name="weather",
    model="gemini-2.0-flash",
    input_schema=CityWeatherInput,   # Validates input
    output_schema=WeatherOutput,      # Enforces output structure
    tools=[get_weather],
    # ...
)
```

### Model Configuration

#### Model Selection

```python
# Direct model string (Google Cloud integrated)
agent = Agent(model="gemini-2.0-flash", ...)

# Vertex AI model
agent = Agent(model="gemini-2.5-flash", ...)

# Claude via Anthropic
agent = Agent(model="claude-sonnet-4-5", ...)
```

#### Model Connectors for External Providers

```python
from google.adk.models.apigee_llm import ApigeeLlm
from google.adk.models.litellm import LiteLlm

# Apigee connector
apigee_model = ApigeeLlm(
    endpoint="https://api.example.com",
    # ... configuration
)
agent = Agent(model=apigee_model, ...)

# LiteLLM connector (supports many providers)
lite_model = LiteLlm(
    model="gpt-4",
    # ... configuration
)
agent = Agent(model=lite_model, ...)
```

#### Generation Configuration

```python
from google.genai.types import GenerateContentConfig

agent = Agent(
    name="creative_agent",
    model="gemini-2.0-flash",
    generate_content_config=GenerateContentConfig(
        temperature=0.9,           # Higher = more creative
        top_p=0.95,               # Nucleus sampling
        top_k=40,                 # Top-k sampling
        max_output_tokens=2048,   # Maximum response length
        stop_sequences=["END"],   # Stop generation at these sequences
    ),
    # ...
)
```

### Planning and Code Execution

#### Built-in Planner

Enable multi-step reasoning and planning.

```python
from google.adk.planners.built_in_planner import BuiltInPlanner

agent = Agent(
    name="planning_agent",
    planner=BuiltInPlanner(),  # Enables multi-step planning
    tools=[tool1, tool2, tool3],
    instruction="Break down complex tasks into steps and execute them",
    # ...
)
```

#### Code Executor

Allow agent to generate and execute code.

```python
from google.adk.code_executors.base_code_executor import CodeExecutor

agent = Agent(
    name="coding_agent",
    code_executor=CodeExecutor(),  # Enables code execution
    instruction="You can write and execute Python code to solve problems",
    # ...
)
```

**Security Note**: Code execution is sandboxed and hermetic (no network access).

### Callbacks for Custom Logic

#### Agent Callbacks

```python
async def before_agent(callback_context):
    """Called before agent executes."""
    print(f"Agent starting: {callback_context.agent.name}")
    # Can return Content to inject into conversation
    return None

async def after_agent(callback_context):
    """Called after agent completes."""
    print(f"Agent completed: {callback_context.agent.name}")
    return None

agent = Agent(
    name="monitored_agent",
    before_agent_callback=before_agent,
    after_agent_callback=after_agent,
    # ...
)
```

#### Model Callbacks

```python
async def before_model(callback_context, llm_request):
    """Called before LLM call."""
    # Can modify request or return LlmResponse to skip call
    print(f"Calling model with {len(llm_request.messages)} messages")
    return None

async def after_model(callback_context, llm_response):
    """Called after LLM responds."""
    # Can modify or replace response
    print(f"Model returned {llm_response.text}")
    return llm_response

async def on_model_error(callback_context, llm_request, exception):
    """Called when model call fails."""
    print(f"Model error: {exception}")
    # Can return LlmResponse to recover from error
    return None

agent = Agent(
    name="monitored_llm_agent",
    before_model_callback=before_model,
    after_model_callback=after_model,
    on_model_error_callback=on_model_error,
    # ...
)
```

#### Tool Callbacks

```python
async def before_tool(tool, args, tool_context):
    """Called before tool execution."""
    # Validation, logging, parameter modification
    print(f"Executing tool: {tool.name}")

    # Example: Validate user permissions
    if not validate_permissions(args, tool_context.state):
        return {"error": "Permission denied"}

    return None  # Allow execution

async def after_tool(tool, args, tool_context, result):
    """Called after tool execution."""
    # Result modification, logging, state updates
    print(f"Tool {tool.name} returned: {result}")
    return result

async def on_tool_error(tool, args, tool_context, exception):
    """Called when tool fails."""
    print(f"Tool error in {tool.name}: {exception}")
    # Return dict to recover from error
    return {"error": str(exception)}

agent = Agent(
    name="tool_agent",
    tools=[sensitive_tool],
    before_tool_callback=before_tool,
    after_tool_callback=after_tool,
    on_tool_error_callback=on_tool_error,
    # ...
)
```

### Agent Configuration via YAML

```yaml
# agent_config.yaml
agent_class: LlmAgent
name: assistant_agent
model: gemini-2.5-flash
description: A helpful assistant that can search and code

instruction: |
  You are a helpful assistant with access to search and code execution.
  Help users solve problems by searching for information and writing code.

tools:
  - name: google_search
  - name: custom_calculator

sub_agents:
  - config_path: code_tutor_agent.yaml
  - config_path: math_tutor_agent.yaml
```

Load configuration:

```python
from google.adk.agents import load_agent_from_config

agent = load_agent_from_config("agent_config.yaml")
```

---

## Session & State Management

### Session State Basics

Every agent invocation receives an `InvocationContext` containing session state.

```python
# Accessing state in instruction
agent = Agent(
    instruction="Hello {user_name}, your role is {user_role}",
    # {user_name} and {user_role} are replaced from state
    # ...
)

# Setting state via output_key
agent = Agent(
    output_key="analysis_result",  # Saves response to state["analysis_result"]
    # ...
)
```

### State in Tools

```python
def get_user_preference(
    preference_name: str,
    tool_context: ToolContext
) -> dict:
    """Retrieve user preference from session state."""

    # Read from state
    value = tool_context.state.get(f"pref_{preference_name}")

    # Write to state
    tool_context.state["last_accessed_pref"] = preference_name

    return {"preference": preference_name, "value": value}
```

### State Management Across Agent Hierarchy

```python
# Parent sets initial state
parent_agent = Agent(
    name="parent",
    instruction="Set user_id to {user_id} for all sub-agents",
    sub_agents=[child_agent],
    # ...
)

# Child accesses parent's state
child_agent = Agent(
    name="child",
    instruction="Process data for user {user_id}",  # Inherits from parent
    # ...
)

# Run with initial state
from google.adk.agents.invocation_context import InvocationContext

ctx = InvocationContext(state={"user_id": "user_123"})
result = await parent_agent.run_async(ctx)
```

### Multi-Turn Conversations

```python
# Initialize context
ctx = InvocationContext(
    state={"user_name": "Alice"},
    conversation_history=[]
)

# Turn 1
ctx = await agent.run_async(ctx)
print(ctx.response)  # Agent's response

# Turn 2 (context preserves history)
ctx.user_message = "Tell me more about that"
ctx = await agent.run_async(ctx)
print(ctx.response)

# Access conversation history
for message in ctx.conversation_history:
    print(f"{message.role}: {message.parts}")
```

### State Persistence Strategies

#### In-Memory (Default)
```python
# State lives only during execution
ctx = InvocationContext(state={})
```

#### External Storage
```python
async def load_state(session_id: str) -> dict:
    """Load state from database."""
    return await db.get_session_state(session_id)

async def save_state(session_id: str, state: dict):
    """Save state to database."""
    await db.save_session_state(session_id, state)

# Use in application
state = await load_state(session_id)
ctx = InvocationContext(state=state)
ctx = await agent.run_async(ctx)
await save_state(session_id, ctx.state)
```

---

## Deployment Strategies

### Local Development

```bash
# Run agent interactively (CLI)
adk run my_agent

# Run agent with web UI
adk web --port 8000

# Run as API server
adk api_server --port 8080
```

### Python Programmatic Execution

```python
from google.adk.agents.invocation_context import InvocationContext

# Single-turn execution
ctx = InvocationContext(
    user_message="What's the weather in Paris?",
    state={}
)
result = await agent.run_async(ctx)
print(result.response)

# Multi-turn with history
ctx = InvocationContext(state={})
ctx.user_message = "Hello"
ctx = await agent.run_async(ctx)

ctx.user_message = "What can you help me with?"
ctx = await agent.run_async(ctx)
```

### A2A Protocol Deployment

Convert agent to A2A-compatible ASGI application:

```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a
import uvicorn

# Create A2A app
app = to_a2a(root_agent)

# Run with uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

Multi-agent A2A deployment:

```python
import threading
import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a

def run_agent(agent, port):
    """Run agent on specific port."""
    app = to_a2a(agent)
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    server.run()

# Start multiple agents
threads = [
    threading.Thread(target=run_agent, args=(pto_agent, 8001)),
    threading.Thread(target=run_agent, args=(hr_agent, 8002)),
    threading.Thread(target=run_agent, args=(orchestrator, 8003)),
]

for t in threads:
    t.start()

for t in threads:
    t.join()
```

### Vertex AI Agent Engine Deployment

```python
import vertexai
from vertexai.agent_engines import create

# Initialize Vertex AI
vertexai.init(
    project="my-project",
    location="us-central1"
)

# Deploy agent
deployed_agent = create(
    display_name="my-agent",
    agent_module_path="my_agent.agent",  # Path to agent.py with root_agent
    agent_module_name="root_agent",       # Variable name in module
    environment_variables={
        "DEPENDENCY_URL": "https://other-agent.com",
    },
    requirements_file_path="requirements.txt",
)

print(f"Agent URL: {deployed_agent.base_url}")
```

Phased deployment for dependencies:

```python
# Phase 1: Deploy leaf agents (no dependencies)
pto_url = deploy_agent("pto_agent", {})
finance_url = deploy_agent("finance_agent", {})

# Phase 2: Deploy functional agents (depend on leaf agents)
hr_url = deploy_agent("hr_agent", {
    "PTO_AGENT_URL": pto_url
})

# Phase 3: Deploy orchestrator (depends on functional agents)
orchestrator_url = deploy_agent("orchestrator", {
    "HR_AGENT_URL": hr_url,
    "FINANCE_AGENT_URL": finance_url
})
```

### Cloud Run Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8080"]
```

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/my-project/my-agent
gcloud run deploy my-agent \
  --image gcr.io/my-project/my-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Container Deployment

```bash
# Build container
docker build -t my-agent:latest .

# Run locally
docker run -p 8080:8080 my-agent:latest

# Deploy to any container platform
# GKE, Cloud Run, Kubernetes, etc.
```

---

## Safety & Security

### Multi-Layered Security Approach

1. **Identity and Authorization**
2. **Input/Output Guardrails**
3. **Sandboxed Code Execution**
4. **Network Perimeter Controls**
5. **Evaluation and Tracing**

### Key Risk Categories

- Misalignment and goal corruption
- Harmful content generation
- Unsafe actions
- Brand safety risks
- Data exfiltration

### Authorization Strategies

#### Agent-Auth Pattern

Tool uses agent's service account.

```python
# Tool authorized via agent's identity
def query_database(query: str) -> dict:
    """Query database using agent's service account."""
    # Agent's credentials used automatically
    return db_client.execute(query)

agent = Agent(
    name="db_agent",
    tools=[query_database],
    # Runs with agent's service account permissions
)
```

**Best For:** Uniform access across all users

#### User-Auth Pattern

Tool uses user's identity (OAuth).

```python
from google.adk.tools.tool_context import ToolContext

def access_user_files(
    file_path: str,
    tool_context: ToolContext
) -> dict:
    """Access files using user's credentials."""

    # Extract user credentials from state
    user_token = tool_context.state.get("oauth_token")

    # Use user's credentials
    return file_service.read(file_path, credentials=user_token)
```

**Best For:** User-specific access control

### Input/Output Guardrails

#### In-Tool Validation

```python
def validate_tool_params(
    tool: BaseTool,
    args: dict,
    tool_context: ToolContext
) -> dict | None:
    """Validate tool parameters before execution."""

    # Example: Validate user ID
    session_user = tool_context.state.get("session_user_id")
    requested_user = args.get("user_id")

    if requested_user != session_user:
        return {"error": "Tool call blocked: User ID mismatch"}

    # Example: Validate SQL query doesn't contain DROP
    if "query" in args:
        if "DROP" in args["query"].upper():
            return {"error": "Dangerous SQL operation blocked"}

    return None  # Allow execution

agent = Agent(
    name="secure_agent",
    tools=[database_tool],
    before_tool_callback=validate_tool_params,
)
```

#### Model Safety Features

```python
from google.genai.types import HarmCategory, HarmBlockThreshold

agent = Agent(
    name="safe_agent",
    model="gemini-2.0-flash",
    generate_content_config=GenerateContentConfig(
        safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
    ),
    instruction="System instruction to guide safe behavior...",
)
```

#### Callback-Based Security Plugins

```python
# PII Redaction Plugin
async def redact_pii(callback_context, llm_response):
    """Redact PII from responses."""
    text = llm_response.text

    # Redact email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                  '[EMAIL]', text)

    # Redact phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)

    llm_response.text = text
    return llm_response

agent = Agent(
    name="privacy_agent",
    after_model_callback=redact_pii,
    # ...
)
```

### Code Execution Security

```python
from google.adk.code_executors.base_code_executor import CodeExecutor

agent = Agent(
    name="coding_agent",
    code_executor=CodeExecutor(),
    # Code execution is:
    # - Sandboxed (isolated environment)
    # - Hermetic (no network access)
    # - Clean data management between executions
)
```

### Network Perimeter Controls

Use VPC Service Controls to restrict API calls:

```python
# Deploy with VPC-SC perimeter
deployed_agent = create(
    display_name="secure-agent",
    agent_module_path="secure_agent.agent",
    vpc_connector="projects/my-project/locations/us-central1/connectors/my-vpc",
    # Agent can only call APIs within VPC perimeter
)
```

### Security Best Practices

1. **Always Escape Model Output**: When displaying in UIs, escape HTML/JavaScript
2. **Validate Tool Parameters**: Use `before_tool_callback` for validation
3. **Implement User Auth**: For user-specific data access
4. **Use VPC-SC**: Restrict network access for sensitive deployments
5. **Enable Safety Filters**: Configure model safety settings
6. **Audit and Log**: Use callbacks for comprehensive logging
7. **Evaluate Regularly**: Test agents for security vulnerabilities

---

## Evaluation & Testing

### Evaluation Dimensions

1. **Trajectory Evaluation**: Analyze sequence of agent steps
2. **Response Quality**: Assess correctness and relevance
3. **Tool Usage**: Verify correct tool selection and parameters
4. **Safety**: Check for harmful content
5. **Semantic Similarity**: Compare against reference responses

### Testing Approaches

#### 1. Unit Testing with Test Files

```python
# test_agent.test.json
{
  "test_cases": [
    {
      "user_input": "What's the weather in Paris?",
      "expected_tool_calls": ["get_weather"],
      "expected_tool_args": {"city": "Paris"},
      "reference_response": "The weather in Paris is sunny with a temperature of 72°F."
    }
  ]
}
```

```python
# test_agent.py
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

@pytest.mark.asyncio
async def test_weather_agent():
    results = await AgentEvaluator.evaluate(
        agent_module="weather_agent",
        eval_dataset_file_path_or_dir="tests/weather_agent.test.json"
    )
    assert results.passed
```

#### 2. Integration Testing with Eval Sets

```python
# eval_set.json
{
  "eval_set_name": "multi_turn_conversation",
  "sessions": [
    {
      "session_id": "session_1",
      "turns": [
        {
          "user_input": "Hello",
          "expected_response_contains": ["hello", "hi"]
        },
        {
          "user_input": "What's the weather?",
          "expected_tool_calls": ["get_weather"]
        }
      ]
    }
  ]
}
```

#### 3. Programmatic Evaluation

```python
from google.adk.evaluation.agent_evaluator import AgentEvaluator
from google.adk.evaluation.metrics import (
    ToolTrajectoryMetric,
    SemanticSimilarityMetric,
    SafetyMetric
)

# Evaluate with custom metrics
results = await AgentEvaluator.evaluate(
    agent_module="my_agent",
    eval_dataset_file_path_or_dir="tests/",
    metrics=[
        ToolTrajectoryMetric(),
        SemanticSimilarityMetric(threshold=0.8),
        SafetyMetric()
    ]
)

print(f"Pass rate: {results.pass_rate}")
print(f"Failed tests: {results.failures}")
```

### Built-in Evaluation Metrics

- **Tool Trajectory Matching**: Verify correct tool sequence
- **Response Semantic Similarity**: LLM-based response comparison
- **Hallucination Detection**: Check for factual errors
- **Safety Assessment**: Verify content safety
- **Response Quality Rubrics**: Custom scoring criteria

### CI/CD Integration

```python
# pytest.ini
[pytest]
testpaths = tests
asyncio_mode = auto

# Run in CI
pytest tests/ --eval-mode --report-format=junit
```

### Evaluation Best Practices

1. **Fast, Predictable Criteria for CI/CD**: Use trajectory matching and exact checks
2. **Semantic Evaluation for Development**: Use LLM-based metrics for flexibility
3. **Define Clear Success Criteria**: Specify expected behavior explicitly
4. **Test Multi-Turn Conversations**: Cover realistic interaction patterns
5. **Automate Testing**: Integrate into CI/CD pipeline
6. **Combine Quantitative and Qualitative**: Use multiple evaluation approaches
7. **Continuously Refine**: Update eval sets as agent evolves

---

## Code Examples

### Complete Multi-Tier A2A System

```python
# ============================================================================
# LEAF AGENTS (Level 3) - Have actual tools
# ============================================================================

# pto_agent.py
from google.adk.agents.llm_agent import Agent

def get_pto_balance(user_id: str) -> dict:
    """Get PTO balance for a user."""
    balances = {"user_123": 15, "user_456": 22}
    return {
        "status": "success",
        "user_id": user_id,
        "pto_balance": balances.get(user_id, 0),
        "unit": "days"
    }

pto_agent = Agent(
    name="pto_agent",
    model="gemini-2.0-flash",
    description="Provides PTO balance information",
    instruction="Use get_pto_balance to check user PTO",
    tools=[get_pto_balance]
)

# quarterly_agent.py
def get_quarterly_report(quarter: str, year: int) -> dict:
    """Get financial report for a quarter."""
    reports = {
        "Q1": {"revenue": 100000, "profit": 20000},
        "Q2": {"revenue": 120000, "profit": 25000},
    }
    return {
        "status": "success",
        "quarter": quarter,
        "year": year,
        "report": reports.get(quarter, {})
    }

quarterly_agent = Agent(
    name="quarterly_agent",
    model="gemini-2.0-flash",
    description="Provides quarterly financial reports",
    instruction="Use get_quarterly_report for financial data",
    tools=[get_quarterly_report]
)

# ============================================================================
# FUNCTIONAL AGENTS (Level 2) - Connect to leaf agents via A2A
# ============================================================================

# hr_agent.py
import os
from google.adk.agents.llm_agent import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from enum import Enum

# Service discovery
PTO_URL = os.getenv("PTO_AGENT_URL", "http://localhost:8001")

# Remote agent connection
pto_remote = RemoteA2aAgent(
    name="pto_helper",
    agent_card=f"{PTO_URL}/.well-known/agent.json",
    description="PTO balance lookups"
)

# Transfer tool with enum constraint
class HRSubAgent(str, Enum):
    PTO = "pto_helper"

def transfer_to_hr_agent(agent: HRSubAgent) -> dict:
    """Transfer to HR sub-agent."""
    return {"transfer_to": agent.value}

hr_agent = Agent(
    name="hr_agent",
    model="gemini-2.0-flash",
    description="HR functions including PTO",
    instruction="Handle HR queries. Use pto_helper for PTO questions.",
    tools=[transfer_to_hr_agent],
    sub_agents=[pto_remote]
)

# finance_agent.py
QUARTERLY_URL = os.getenv("QUARTERLY_AGENT_URL", "http://localhost:8002")

quarterly_remote = RemoteA2aAgent(
    name="quarterly_helper",
    agent_card=f"{QUARTERLY_URL}/.well-known/agent.json",
    description="Quarterly financial reports"
)

class FinanceSubAgent(str, Enum):
    QUARTERLY = "quarterly_helper"

def transfer_to_finance_agent(agent: FinanceSubAgent) -> dict:
    """Transfer to finance sub-agent."""
    return {"transfer_to": agent.value}

finance_agent = Agent(
    name="finance_agent",
    model="gemini-2.0-flash",
    description="Financial information and reports",
    instruction="Handle finance queries. Use quarterly_helper for reports.",
    tools=[transfer_to_finance_agent],
    sub_agents=[quarterly_remote]
)

# ============================================================================
# ORCHESTRATOR (Level 1) - Routes to functional agents
# ============================================================================

# orchestrator_agent.py
HR_URL = os.getenv("HR_AGENT_URL", "http://localhost:8003")
FINANCE_URL = os.getenv("FINANCE_AGENT_URL", "http://localhost:8004")

hr_remote = RemoteA2aAgent(
    name="hr_helper",
    agent_card=f"{HR_URL}/.well-known/agent.json",
    description="HR functions"
)

finance_remote = RemoteA2aAgent(
    name="finance_helper",
    agent_card=f"{FINANCE_URL}/.well-known/agent.json",
    description="Finance functions"
)

class OrchestratorAgent(str, Enum):
    HR = "hr_helper"
    FINANCE = "finance_helper"

def transfer_to_agent(agent: OrchestratorAgent) -> dict:
    """Transfer to appropriate department."""
    return {"transfer_to": agent.value}

orchestrator = Agent(
    name="orchestrator_agent",
    model="gemini-2.0-flash",
    description="Enterprise assistant routing to HR and Finance",
    instruction="""Route user requests to appropriate department:
    - HR questions (PTO, benefits) -> hr_helper
    - Finance questions (reports, budgets) -> finance_helper
    """,
    tools=[transfer_to_agent],
    sub_agents=[hr_remote, finance_remote]
)

# ============================================================================
# DEPLOYMENT
# ============================================================================

# start_local_stack.py
import threading
import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a

def run_agent(agent, port):
    app = to_a2a(agent)
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    server.run()

# Start all agents
threads = [
    threading.Thread(target=run_agent, args=(pto_agent, 8001)),
    threading.Thread(target=run_agent, args=(quarterly_agent, 8002)),
    threading.Thread(target=run_agent, args=(hr_agent, 8003)),
    threading.Thread(target=run_agent, args=(finance_agent, 8004)),
    threading.Thread(target=run_agent, args=(orchestrator, 8005)),
]

for t in threads:
    t.daemon = True
    t.start()

print("All agents running. Orchestrator: http://localhost:8005")

for t in threads:
    t.join()

# ============================================================================
# CLIENT TESTING
# ============================================================================

# test_client.py
from a2a.client import ClientFactory

async def test_full_chain():
    # Create A2A client
    client = await ClientFactory.create_client(
        "http://localhost:8005/.well-known/agent.json"
    )

    # Test PTO query (routes through orchestrator -> hr -> pto)
    response = await client.send_message(
        "What is the PTO balance for user_123?"
    )
    print(f"PTO Response: {response}")

    # Test finance query (routes through orchestrator -> finance -> quarterly)
    response = await client.send_message(
        "Show me the Q2 2024 financial report"
    )
    print(f"Finance Response: {response}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_full_chain())
```

### Sequential Pipeline with State Passing

```python
from google.adk.agents.llm_agent import Agent
from google.adk.agents.sequential_agent import SequentialAgent
from pydantic import BaseModel

# Output schema for structured data
class CodeOutput(BaseModel):
    language: str
    code: str
    complexity: str

# Stage 1: Code generation
code_writer = Agent(
    name="code_writer",
    model="gemini-2.0-flash",
    instruction="Generate Python code based on the request",
    output_key="generated_code",
    output_schema=CodeOutput
)

# Stage 2: Code review
code_reviewer = Agent(
    name="code_reviewer",
    model="gemini-2.0-flash",
    instruction="""Review this code: {generated_code}
    Provide feedback on quality, style, and potential issues.""",
    output_key="review_feedback"
)

# Stage 3: Code improvement
code_refactorer = Agent(
    name="code_refactorer",
    model="gemini-2.0-flash",
    instruction="""Improve this code: {generated_code}
    Based on this feedback: {review_feedback}""",
    output_schema=CodeOutput
)

# Pipeline
pipeline = SequentialAgent(
    name="code_pipeline",
    sub_agents=[code_writer, code_reviewer, code_refactorer]
)

# Run pipeline
from google.adk.agents.invocation_context import InvocationContext

ctx = InvocationContext(
    user_message="Write a function to calculate fibonacci numbers"
)
result = await pipeline.run_async(ctx)

print(f"Final code: {result.state.get('generated_code')}")
print(f"Review: {result.state.get('review_feedback')}")
```

### Parallel Data Gathering with Aggregation

```python
from google.adk.agents.parallel_agent import ParallelAgent

# Create specialized data collectors
db_agent = Agent(
    name="database_collector",
    model="gemini-2.0-flash",
    tools=[query_database],
    output_key="db_results"
)

api_agent = Agent(
    name="api_collector",
    model="gemini-2.0-flash",
    tools=[call_external_api],
    output_key="api_results"
)

file_agent = Agent(
    name="file_collector",
    model="gemini-2.0-flash",
    tools=[read_file_data],
    output_key="file_results"
)

# Parallel data collection
parallel_collector = ParallelAgent(
    name="parallel_data_collection",
    sub_agents=[db_agent, api_agent, file_agent]
)

# Aggregator
aggregator = Agent(
    name="data_aggregator",
    model="gemini-2.0-flash",
    instruction="""Combine and analyze these data sources:
    - Database: {db_results}
    - API: {api_results}
    - Files: {file_results}

    Provide a comprehensive summary."""
)

# Full workflow
workflow = SequentialAgent(
    name="data_workflow",
    sub_agents=[parallel_collector, aggregator]
)
```

### Custom Agent with Complex Logic

```python
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext

class AdaptiveQualityAgent(BaseAgent):
    """Custom agent with quality-based iteration."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.generator = Agent(
            name="content_generator",
            model="gemini-2.0-flash",
            instruction="Generate content based on: {topic}",
            output_key="content"
        )
        self.critic = Agent(
            name="content_critic",
            model="gemini-2.0-flash",
            instruction="Rate this content 1-10: {content}",
            output_key="quality_score"
        )
        self.improver = Agent(
            name="content_improver",
            model="gemini-2.0-flash",
            instruction="Improve: {content}. Issues: {feedback}",
            output_key="content"
        )

    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> InvocationContext:
        # Initial generation
        ctx = await self.generator.run_async(ctx)

        # Iterative improvement up to 5 times
        for iteration in range(5):
            # Get quality score
            ctx = await self.critic.run_async(ctx)

            score = float(ctx.state.get("quality_score", 0))

            # Success threshold
            if score >= 8.0:
                ctx.add_message(
                    "model",
                    f"Quality achieved after {iteration + 1} iterations"
                )
                break

            # Improve content
            ctx.state["feedback"] = f"Current score: {score}/10. Needs improvement."
            ctx = await self.improver.run_async(ctx)

        return ctx

# Use custom agent
adaptive_agent = AdaptiveQualityAgent(
    name="adaptive_quality",
    description="Generates high-quality content iteratively"
)
```

---

## Quick Reference

### Agent Creation Checklist

- [ ] Choose agent type (LLM, Sequential, Parallel, Loop, Custom)
- [ ] Define name and description
- [ ] Select appropriate model
- [ ] Write clear instructions
- [ ] Define tools (if needed)
- [ ] Set up sub-agents (if needed)
- [ ] Configure input/output schemas (optional)
- [ ] Add callbacks for monitoring/security (optional)
- [ ] Set output_key for state management (optional)

### Tool Development Checklist

- [ ] Write clear, descriptive function name
- [ ] Add comprehensive docstring
- [ ] Use type hints for all parameters
- [ ] Include ToolContext parameter (if state access needed)
- [ ] Return structured data (dict or Pydantic model)
- [ ] Handle errors gracefully
- [ ] Add validation in before_tool_callback (if sensitive)

### Multi-Agent Design Checklist

- [ ] Identify agent hierarchy levels
- [ ] Define clear agent responsibilities
- [ ] Choose interaction mechanism (state, delegation, invocation)
- [ ] Plan state passing strategy
- [ ] Implement service discovery (for A2A)
- [ ] Add transfer tools with enum constraints
- [ ] Test individual agents before integration
- [ ] Plan phased deployment (leaf → functional → orchestrator)

### Security Checklist

- [ ] Implement authorization strategy (agent-auth or user-auth)
- [ ] Add input validation in before_tool_callback
- [ ] Configure model safety settings
- [ ] Escape model output in UIs
- [ ] Use VPC-SC for network controls (if applicable)
- [ ] Enable audit logging via callbacks
- [ ] Evaluate for security vulnerabilities
- [ ] Implement PII redaction (if handling sensitive data)

### Deployment Checklist

- [ ] Test locally with `adk run` or `adk web`
- [ ] Create requirements.txt with dependencies
- [ ] Configure environment variables
- [ ] Choose deployment target (Agent Engine, Cloud Run, GKE, etc.)
- [ ] Handle service discovery for remote agents
- [ ] Deploy in correct order (leaf → functional → orchestrator)
- [ ] Verify agent card endpoints
- [ ] Test deployed agents
- [ ] Set up monitoring and logging
- [ ] Document deployment process

---

## Additional Resources

### Official Documentation
- Main Documentation: https://google.github.io/adk-docs/
- Python Getting Started: https://google.github.io/adk-docs/get-started/python/
- API Reference: https://google.github.io/adk-docs/api-reference/python/

### Key Concepts
- LLM Agents: Non-deterministic, reasoning-based agents
- Workflow Agents: Deterministic, structured execution patterns
- Multi-Agent Systems: Hierarchical composition and coordination
- A2A Protocol: Agent-to-Agent communication standard
- Tool Development: Extending agent capabilities
- Session Management: State persistence and context handling
- Safety & Security: Multi-layered protection mechanisms

### Common Patterns
- Coordinator/Dispatcher: Central routing to specialized agents
- Sequential Pipeline: Fixed-order processing chains
- Parallel Fan-Out: Concurrent task execution
- Hierarchical Decomposition: Multi-level agent structures
- Review/Critique: Iterative quality improvement

### Best Practices
- Start simple, add complexity incrementally
- Test agents individually before integration
- Use structured outputs for reliability
- Implement comprehensive error handling
- Monitor and evaluate continuously
- Document agent behavior and limitations
- Follow security best practices
