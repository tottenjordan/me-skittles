# A2A Protocol Reference Guide

## Overview

Agent-to-Agent (A2A) is an **open standard protocol** designed to enable seamless communication and collaboration between AI agents. It provides a standardized framework for agent discovery, communication, and interoperability across distributed systems.

## Core Concepts

### What is A2A?

A2A enables agents to:
- **Discover** other agents and their capabilities
- **Communicate** using standardized protocols
- **Collaborate** to complete complex tasks
- **Interoperate** across different platforms and languages

### Key Benefits

- Simplified agent interoperability
- Dynamic skill sharing between agents
- Standardized agent communication patterns
- Flexible deployment options
- Minimal integration complexity
- Support for multi-agent collaboration

## Architecture Patterns

### Agent Hierarchy

A2A supports multi-tier agent architectures:

```
Orchestrator Agent (Level 1)
├── Functional Agent A (Level 2)
│   └── Specialized Agent A1 (Level 3)
└── Functional Agent B (Level 2)
    └── Specialized Agent B1 (Level 3)
```

### Communication Workflow

1. **Agent Discovery**: Agents expose capabilities via AgentCard
2. **Request Routing**: Orchestrators route requests to appropriate agents
3. **Task Execution**: Leaf agents execute tasks using their tools
4. **Response Propagation**: Results flow back through the hierarchy

## Core Components

### 1. AgentCard

The AgentCard serves as a "business card" describing an agent's capabilities.

#### AgentCard Schema

```python
agent_card = {
    "id": "unique-agent-identifier",
    "name": "Agent Name",
    "description": "What this agent does",
    "version": "1.0.0",
    "url": "https://agent-url.com",
    "protocol_version": "a2a/1.0",
    "skills": [...],
    "capabilities": [...],
    "input_modes": ["text", "structured"],
    "output_modes": ["text", "structured"]
}
```

#### AgentCard Components

- **Unique identifier**: Persistent ID for the agent
- **Name**: Human-readable agent name
- **Description**: What the agent does and when to use it
- **Skills/Capabilities**: List of functions the agent can perform
- **Example interactions**: Sample queries the agent can handle
- **URL**: Endpoint where the agent is accessible
- **Protocol version**: A2A protocol version supported

#### Creating an AgentSkill

```python
from google.adk.a2a import AgentSkill

currency_skill = AgentSkill(
    id='get_exchange_rate',
    name='Get Currency Exchange Rate',
    description='Retrieves exchange rate between two currencies',
    tags=['Finance', 'Currency'],
    examples=[
        'What is the exchange rate from USD to EUR?'
    ]
)
```

#### Creating an AgentCard

```python
from google.adk.a2a import create_agent_card

agent_card = create_agent_card(
    agent_name='Currency Exchange Agent',
    description='An agent providing currency exchange rates',
    skills=[currency_skill]
)
```

### 2. AgentExecutor

The AgentExecutor implements the agent's core logic:

- Handles task execution
- Manages request processing
- Generates responses
- Maintains state (if needed)

#### Key Methods

```python
class AgentExecutor:
    def handle_authenticated_agent_card(self):
        """Return the agent's card for discovery"""
        pass

    def on_message_send(self, message):
        """Process incoming messages"""
        pass

    def on_get_task(self, task_id):
        """Retrieve task status/results"""
        pass
```

### 3. Agent Discovery Mechanism

Agents expose their capabilities via a standardized endpoint:

```
GET /.well-known/agent.json
```

This endpoint returns the agent's AgentCard, allowing other agents to:
- Discover available capabilities
- Understand how to interact with the agent
- Route appropriate requests

## Protocol Specifications

### Transport Protocols

A2A supports multiple transport mechanisms:

1. **JSON-RPC**: Structured request/response pattern
2. **Server-Sent Events (SSE)**: Streaming responses
3. **HTTP/REST**: Standard HTTP communication
4. **Stateful interactions**: Maintaining context across requests

### Communication Patterns

#### Synchronous Request/Response

```python
# Agent A calls Agent B
response = await agent_b.execute(request)
```

#### Streaming Responses (SSE)

```python
# Agent streams responses back
async for chunk in agent.execute_stream(request):
    yield chunk
```

#### Agent Transfer

```python
# Transfer conversation to another agent
transfer_tool = TransferToAgentTool(
    remote_agent=agent_b,
    transfer_instructions="Route to specialized agent"
)
```

## Implementation Approaches

### Approach 1: Using `to_a2a()`

Convert existing ADK agents to A2A-compatible format:

```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents.llm_agent import Agent

# Create your agent
root_agent = Agent(
    model="gemini-2.0-flash-exp",
    name="My Agent",
    description="What my agent does",
    tools=[...],
    system_instruction="Agent instructions"
)

# Convert to A2A-compatible ASGI app
a2a_app = to_a2a(root_agent, port=8001)

# Run with uvicorn
import uvicorn
uvicorn.run(a2a_app, host="0.0.0.0", port=8001)
```

**Features:**
- Auto-generates agent cards
- Minimal configuration required
- Quick setup for simple agents

### Approach 2: Custom Agent Cards with API Server

More flexible configuration for complex deployments:

```python
# Use ADK API server with A2A support
# adk api_server --a2a

# Supports multiple agents in a single server
# Requires manually creating agent cards
```

**Features:**
- Manual agent card creation
- Support for multiple agents per server
- More control over configuration

## Consuming Remote Agents

### Using RemoteA2aAgent

```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# Connect to remote agent
remote_agent = RemoteA2aAgent(
    name="Remote HR Agent",
    agent_url="https://hr-agent.example.com"
)

# Agent card is fetched from /.well-known/agent.json
# Use the remote agent in your tools
```

### Client Factory Pattern

```python
from a2a.client import ClientFactory

# Create A2A client
client = await ClientFactory.create_client_from_url(
    "https://agent.example.com"
)

# Send request
response = await client.send_message("What is my PTO balance?")
```

## Best Practices

### 1. Agent Design

- **Single Responsibility**: Each agent should have a clear, focused purpose
- **Clear Capabilities**: Document what the agent can and cannot do
- **Descriptive Names**: Use names that clearly indicate the agent's function
- **Comprehensive Examples**: Provide example queries in AgentSkills

### 2. Multi-Agent Systems

- **Hierarchical Organization**: Use levels (orchestrator → functional → specialized)
- **Dependency Management**: Deploy leaf agents before parent agents
- **Service Discovery**: Use environment variables or service registries
- **Error Handling**: Handle agent unavailability gracefully

### 3. Communication

- **Structured Transfers**: Use TransferToAgentTool for clean handoffs
- **Context Preservation**: Maintain conversation context during transfers
- **Clear Instructions**: Provide transfer instructions for downstream agents
- **Enum Constraints**: Use enums to limit valid transfer destinations

### 4. Deployment

#### Phased Deployment Order

Deploy from leaf to root:

1. **Leaf Agents** (Level 3): No dependencies, can deploy first
2. **Functional Agents** (Level 2): Depend on leaf agents
3. **Orchestrator** (Level 1): Depends on functional agents

#### Environment Variables

```bash
# Leaf agent URLs for functional agents
export PTO_AGENT_URL="https://pto-agent.example.com"
export QUARTERLY_AGENT_URL="https://quarterly-agent.example.com"

# Functional agent URLs for orchestrator
export HR_AGENT_URL="https://hr-agent.example.com"
export FINANCE_AGENT_URL="https://finance-agent.example.com"
```

### 5. Testing

- **Local Testing**: Test full stack locally before deploying
- **Integration Testing**: Test agent-to-agent communication
- **End-to-End Testing**: Test from orchestrator to leaf agents
- **Error Scenarios**: Test timeout, unavailability, invalid requests

### 6. Security

- **Authentication**: Use authenticated agent cards when needed
- **Authorization**: Control which agents can communicate
- **Input Validation**: Validate all inputs before processing
- **Rate Limiting**: Protect agents from overload

## Development Platforms

A2A supports multiple programming languages and SDKs:

- **Python**: `google-adk[a2a]`, `a2a-sdk`
- **Go**: A2A Go SDK
- **JavaScript/TypeScript**: A2A JS SDK
- **Java**: A2A Java SDK
- **C#/.NET**: A2A .NET SDK

## Common Use Cases

### 1. Multi-Agent Collaboration

Multiple agents work together to solve complex problems:

```
User Query → Orchestrator → HR Agent → PTO Agent
                         → Finance Agent → Reporting Agent
```

### 2. Distributed Agent Systems

Agents deployed across different services/regions:

```
Regional Agents (US, EU, APAC) → Global Orchestrator
```

### 3. Modular Agent Design

Reusable specialized agents:

```
Authentication Agent ← Multiple Application Agents
Data Access Agent    ← Multiple Business Logic Agents
```

### 4. Complex Workflow Orchestration

Step-by-step process automation:

```
Intake Agent → Validation Agent → Processing Agent → Notification Agent
```

## Code Examples

### Complete Local A2A Setup

```python
from google.adk.agents.llm_agent import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
import uvicorn
import threading

# Leaf agent with tools
leaf_agent = Agent(
    model="gemini-2.0-flash-exp",
    name="PTO Agent",
    description="Manages PTO requests and balances",
    tools=[get_pto_balance, request_pto],
    system_instruction="Help users with PTO queries"
)

# Functional agent using RemoteA2aAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

remote_pto_agent = RemoteA2aAgent(
    name="PTO Agent",
    agent_url="http://localhost:8001"
)

hr_agent = Agent(
    model="gemini-2.0-flash-exp",
    name="HR Agent",
    description="Handles HR queries",
    tools=[TransferToAgentTool(remote_agent=remote_pto_agent)],
    system_instruction="Route HR queries to appropriate agents"
)

# Start agents
def start_agent(agent, port):
    app = to_a2a(agent, port=port)
    uvicorn.run(app, host="0.0.0.0", port=port)

threads = [
    threading.Thread(target=start_agent, args=(leaf_agent, 8001)),
    threading.Thread(target=start_agent, args=(hr_agent, 8002))
]

for t in threads:
    t.daemon = True
    t.start()

# Keep running
for t in threads:
    t.join()
```

### Testing A2A Agents

```python
from a2a.client import ClientFactory
import asyncio

async def test_agent():
    # Create client
    client = await ClientFactory.create_client_from_url(
        "http://localhost:8002"
    )

    # Send query
    response = await client.send_message(
        "What is my PTO balance?"
    )

    print(f"Response: {response}")

asyncio.run(test_agent())
```

## Troubleshooting

### Common Issues

1. **Agent not discoverable**
   - Verify `/.well-known/agent.json` endpoint is accessible
   - Check agent card is properly formatted

2. **Connection timeout**
   - Ensure target agent is running
   - Verify network connectivity
   - Check URL configuration

3. **Transfer failures**
   - Verify remote agent URL is correct
   - Check agent card was fetched successfully
   - Ensure tools are properly configured

4. **Deployment order issues**
   - Deploy leaf agents before parent agents
   - Set environment variables before deploying dependents
   - Verify URLs are accessible from deployment environment

## Additional Resources

- [Google Cloud Agent Engine A2A Documentation](https://docs.cloud.google.com/agent-builder/agent-engine/develop/a2a)
- [ADK A2A Quickstart](https://google.github.io/adk-docs/a2a/quickstart-exposing/)
- [Agent Development Kit (ADK) Documentation](https://google.github.io/adk-docs/)
- [A2A SDK Documentation](https://pypi.org/project/a2a-sdk/)

## Summary

A2A provides a robust, standardized framework for building interconnected, intelligent agent systems. By following the protocol specifications and best practices outlined in this guide, developers can create scalable, maintainable multi-agent architectures with minimal integration complexity.

Key takeaways:
- Use AgentCards for discovery and capability advertisement
- Implement hierarchical agent structures for complex systems
- Follow phased deployment patterns (leaf → functional → orchestrator)
- Test locally before deploying to production
- Leverage RemoteA2aAgent for clean agent-to-agent integration
