# Vertex AI Agent Engine Reference

Comprehensive reference for advanced deployment patterns, session management, memory capabilities, and optimization strategies.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Deployment Patterns](#deployment-patterns)
- [Session Management](#session-management)
- [Memory Bank](#memory-bank)
- [Runtime Optimization](#runtime-optimization)
- [Framework Integration](#framework-integration)

---

## Architecture Overview

Vertex AI Agent Engine is a managed platform for deploying, scaling, and managing AI agents in production environments.

### Core Components

1. **Runtime Services**
   - Managed runtime for deploying and scaling agents
   - Container image customization support
   - Multiple Python framework compatibility
   - Built-in security features (VPC-SC, authentication)

2. **Additional Services**
   - **Sessions**: Store individual user-agent interactions
   - **Memory Bank**: Store and retrieve interaction memories
   - **Code Execution**: Secure sandbox for agent code running
   - **Example Store**: Store and retrieve few-shot examples
   - **Observability**: Tracing, monitoring, and logging tools

### Enterprise Security

- VPC Service Controls
- Customer-managed encryption keys (CMEK)
- Data residency support
- HIPAA compliance
- Access Transparency

### Pricing

Agent Engine Runtime includes a free tier for initial development and testing.

---

## Deployment Patterns

### Standard Deployment Workflow

1. **Develop** agent using supported frameworks
2. **Set up** Google Cloud environment
3. **Deploy** agent to Vertex AI Agent Engine Runtime
4. **Manage** and monitor agent performance

### Multi-Agent Deployment Strategy

For hierarchical agent systems (like A2A multi-tier architectures):

**Phased Deployment Order** (leaf → functional → root):
1. Deploy leaf agents first (no dependencies)
2. Deploy functional/mid-tier agents (with environment variables pointing to leaf agents)
3. Deploy orchestrator/root agent (with environment variables pointing to functional agents)

Example:
```
Phase 1: pto_agent, quarterly_agent (no dependencies)
Phase 2: hr_agent (needs PTO_AGENT_URL), finance_agent (needs QUARTERLY_AGENT_URL)
Phase 3: orchestrator_agent (needs HR_AGENT_URL, FINANCE_AGENT_URL)
```

### Service Discovery Patterns

**Agent Cards**: Each deployed agent exposes metadata via `/.well-known/agent.json` endpoint
- Use `RemoteA2aAgent` to fetch agent cards automatically
- Agent cards contain capabilities, tools, and connection information

**Environment Variables**: Configure agent URLs via environment variables
```python
PTO_AGENT_URL = os.getenv("PTO_AGENT_URL")
HR_AGENT_URL = os.getenv("HR_AGENT_URL")
FINANCE_AGENT_URL = os.getenv("FINANCE_AGENT_URL")
```

---

## Session Management

### What are Sessions?

A **session** represents the chronological sequence of interactions between a user and an agent, maintaining conversation history and context.

### Core Components

1. **Event**: Stores conversation content and agent actions
2. **State**: Temporary data relevant to the current conversation
3. **Memory**: Personalized information that persists across multiple sessions

### Session Lifecycle

```
Create Session → Append Events → Process Interactions → Retrieve/Resume → Delete
```

**Operations**:
- Starting new conversations
- Resuming existing conversations
- Saving interaction progress
- Listing conversation threads
- Cleaning up session data

### Management Options

#### 1. Automatic Management (ADK)

The Agent Development Kit handles session management automatically:

```python
from google.adk.agents import Agent

agent = Agent(
    name="my_agent",
    model="gemini-2.0-flash",
    # ADK manages sessions automatically
)
```

#### 2. Manual Management (API)

Direct API calls for fine-grained control:

```python
# Create session
session = client.create_session(
    agent_id="projects/{project}/locations/{location}/agents/{agent}",
    session_id="unique-session-id"
)

# Append events
client.append_event(
    session=session.name,
    event={"user_input": "Hello"}
)

# Retrieve session
session = client.get_session(name="session_name")

# Delete session
client.delete_session(name="session_name")
```

### Best Practices

- **Use sessions** to maintain conversation context across interactions
- **Leverage memory** for personalized, cross-session experiences
- **Choose management approach** based on control needs (ADK for simplicity, API for flexibility)
- **Clean up sessions** to manage storage costs

---

## Memory Bank

### Overview

Memory Bank allows agents to dynamically generate and manage long-term, personalized memories across multiple user interactions, enabling context-aware and personalized agent behavior.

### Key Features

#### 1. Memory Generation

- **Automatic extraction**: Extract meaningful information from conversations
- **Memory consolidation**: Merge new information with existing memories
- **Asynchronous processing**: Generate memories without blocking user interactions
- **Multimodal support**: Process information from text, images, and other modalities
- **Customization**: Define topics and examples to guide memory extraction

#### 2. Storage and Retrieval

- **User isolation**: Memories stored separately per user identity
- **Persistence**: Memories persist across environments and sessions
- **Similarity search**: Retrieve relevant memories based on semantic similarity
- **Automatic expiration**: Configure memory TTL (time-to-live)
- **Revision tracking**: Track changes to memories over time

### Use Cases

- **Long-term personalization**: Customer service agents remembering user preferences
- **Knowledge extraction**: Automatically build knowledge bases from conversations
- **Contextual understanding**: Evolving understanding of user needs and behaviors
- **Cross-session continuity**: Maintain context across multiple interactions

### Workflow

```python
# 1. Create a session
session = client.create_session(agent_id=agent_id)

# 2. Append conversation events
client.append_event(
    session=session.name,
    event={"user_input": "I prefer vegetarian options"}
)

# 3. Generate memories from conversation history
client.generate_memories(session=session.name)

# 4. Retrieve relevant memories for future interactions
memories = client.search_memories(
    agent_id=agent_id,
    user_id=user_id,
    query="What are the user's dietary preferences?"
)
```

### Memory Bank with ADK (PreloadMemoryTool)

Memory Bank is **auto-enabled** on Agent Engine when ADK >= 1.5.0 and the `GOOGLE_CLOUD_AGENT_ENGINE_ID` env var is set (automatic in Agent Engine runtime). No explicit configuration or deploy flags needed.

Add `PreloadMemoryTool` to auto-load user memories at conversation start:

```python
from google.adk.agents import Agent
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

agent = Agent(
    name="personalized_agent",
    model="gemini-2.5-flash",
    tools=[PreloadMemoryTool()],
    instruction="You are a helpful assistant. Use remembered preferences to personalize responses.",
)
```

### Security Considerations

- **Model Armor**: Use for prompt inspection and adversarial attack detection
- **Adversarial testing**: Regularly test memory extraction for security vulnerabilities
- **Sandboxed execution**: Implement for critical actions based on memories
- **User consent**: Ensure compliance with privacy regulations (GDPR, CCPA)

### Integration Options

- **Agent Development Kit (ADK)**: High-level, declarative approach
- **REST API**: Fine-grained control over memory operations
- **Framework compatible**: Works with LangChain, LangGraph, and other supported frameworks

---

## Runtime Optimization

### Performance Configuration Parameters

```python
from vertexai import agent_engines

agent = agent_engines.create(
    agent_id="my-optimized-agent",
    min_instances=3,              # Reduce cold start latency
    container_concurrency=36,     # Handle multiple concurrent requests
    # ... other configuration
)
```

### 1. Cold Start Mitigation

**Problem**: High initial latency when instances spin up from zero.

**Solution**: Set `min_instances` higher to maintain warm instances.

```python
min_instances=3  # Keep 3 instances always running
```

**Recommended Range**: 1-10 instances

**Performance Impact**:
- Without optimization: ~4.7 seconds cold start latency
- With optimization: ~1.4 seconds latency (70% reduction)

**Trade-offs**:
- Cost: Higher minimum instances = higher baseline cost
- Benefit: Consistent low-latency response times

### 2. Asynchronous Worker Optimization

**Problem**: Request queuing during traffic spikes with default concurrency settings.

**Solution**: Increase `container_concurrency` for I/O-bound agents.

```python
container_concurrency=36  # Handle 36 concurrent requests per instance
```

**Recommended Setting**: Multiples of 9 (e.g., 9, 18, 27, 36)

**Benefits**:
- Reduces request queuing
- Improves responsiveness during traffic spikes
- Better resource utilization for async/I/O-bound workloads

**Caution**: Setting too high risks out-of-memory (OOM) errors. Test incrementally.

### 3. Performance Measurement Insights

- **Stable loads** help maintain "warm" service performance
- **Default configuration** may result in high latency during traffic spikes
- **Asynchronous agents** can significantly improve request processing efficiency
- **Traffic patterns** should guide configuration (bursty vs. continuous)

### Optimization Best Practices

#### Load Testing
```bash
# Use tools like Apache Bench, Locust, or custom scripts
ab -n 1000 -c 10 https://your-agent-url/
```

#### Monitoring
- Track instance scaling patterns
- Monitor request latency (p50, p95, p99)
- Watch for OOM errors
- Observe CPU and memory utilization

#### Incremental Tuning
```python
# Start conservative
min_instances=1
container_concurrency=9

# Monitor performance, then adjust
min_instances=3
container_concurrency=18

# Continue tuning based on metrics
min_instances=5
container_concurrency=36
```

#### Traffic Pattern Optimization

**Predictable, Continuous Load**:
- Lower `min_instances` (cost optimization)
- Higher `container_concurrency` (efficiency)

**Bursty, Unpredictable Load**:
- Higher `min_instances` (latency optimization)
- Moderate `container_concurrency` (stability)

### Cost vs. Performance Trade-offs

| Configuration | Cost | Latency | Best For |
|--------------|------|---------|----------|
| `min_instances=1, concurrency=9` | Low | High (cold starts) | Development, low-traffic |
| `min_instances=3, concurrency=18` | Medium | Medium | Production, moderate traffic |
| `min_instances=5, concurrency=36` | High | Low | Production, high-traffic |

### Advanced Optimization Techniques

1. **Caching**: Implement response caching for repeated queries
2. **Connection pooling**: Reuse database and API connections
3. **Lazy loading**: Load resources only when needed
4. **Batch processing**: Group similar requests together
5. **Regional deployment**: Deploy closer to users for reduced latency

---

## Framework Integration

### Integration Levels

Vertex AI Agent Engine supports multiple integration levels based on framework maturity:

#### Full Integration
Frameworks with deep integration and automatic feature support:
- **Agent Development Kit (ADK)** - Google's native framework
- **LangChain** - Popular agent orchestration framework
- **LangGraph** - State machine-based agent framework

Features:
- Automatic session management
- Built-in Memory Bank support
- Native observability integration
- Streamlined deployment

#### SDK Integration
Frameworks with SDK support but manual feature configuration:
- **AG2** (formerly AutoGen)
- **LlamaIndex**

Features:
- Deploy via SDK
- Manual session and memory configuration
- Custom observability setup

#### Custom Template Support
Any framework using custom deployment templates:
- **CrewAI**
- **Custom frameworks**

Features:
- Dockerfile-based deployment
- Manual service integration
- Full control over runtime

### Framework-Specific Patterns

#### ADK (Recommended for A2A Systems)

```python
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Create agent
agent = Agent(
    name="my_agent",
    model="gemini-2.0-flash",
    tools=[my_tool]
)

# Convert to A2A-compatible ASGI app
app = to_a2a(agent)

# Deploy
from vertexai import agent_engines
deployed = agent_engines.create(
    agent_id="my-agent",
    agent=agent,
    min_instances=2,
    container_concurrency=18
)
```

#### LangChain

```python
from langchain.agents import AgentExecutor
from vertexai import agent_engines

# Create LangChain agent
agent = AgentExecutor(...)

# Deploy
deployed = agent_engines.create(
    agent_id="langchain-agent",
    langchain_agent=agent,
    min_instances=2
)
```

#### LangGraph

```python
from langgraph.graph import StateGraph
from vertexai import agent_engines

# Create LangGraph agent
graph = StateGraph(...)

# Deploy
deployed = agent_engines.create(
    agent_id="langgraph-agent",
    langgraph_agent=graph.compile(),
    min_instances=2
)
```

### Multi-Agent Framework Patterns

For systems using Agent-to-Agent (A2A) protocol with multiple frameworks:

1. **Leaf agents**: Can use any framework (ADK, LangChain, custom)
2. **Connecting agents**: Use `RemoteA2aAgent` to communicate via A2A protocol
3. **Protocol compatibility**: A2A ensures cross-framework communication

Example:
```python
# Leaf agent (LangChain)
leaf_agent = LangChainAgent(...)

# Functional agent (ADK) connecting to leaf
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

remote_leaf = RemoteA2aAgent(
    name="remote_leaf",
    url=os.getenv("LEAF_AGENT_URL")
)

functional_agent = Agent(
    name="functional",
    agents=[remote_leaf],
    # Transfer to remote_leaf as needed
)
```

---

## Quick Reference: Common Tasks

### Deploy an Agent
```python
from vertexai import agent_engines

deployed = agent_engines.create(
    agent_id="my-agent",
    agent=my_agent,
    min_instances=2,
    container_concurrency=18
)
```

### Create and Use a Session
```python
# Automatic (ADK)
agent = Agent(name="my_agent", model="gemini-2.0-flash")
# Sessions managed automatically

# Manual (API)
session = client.create_session(agent_id=agent_id)
client.append_event(session=session.name, event={"user_input": "Hello"})
```

### Enable Memory Bank
```python
from google.adk.features import memory_bank

agent = Agent(
    name="my_agent",
    features=[
        memory_bank.MemoryBank(
            topics=["preferences", "history"]
        )
    ]
)
```

### Optimize Performance
```python
deployed = agent_engines.create(
    agent_id="optimized-agent",
    agent=agent,
    min_instances=3,           # Reduce cold starts
    container_concurrency=36   # Handle concurrent requests
)
```

### Connect Multi-Tier Agents
```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# Connect to remote agent
remote = RemoteA2aAgent(
    name="remote_agent",
    url=os.getenv("REMOTE_AGENT_URL")
)

# Use in parent agent
parent = Agent(
    name="parent",
    agents=[remote]
)
```

---

## Additional Resources

- **Official Documentation**: https://cloud.google.com/agent-builder/agent-engine/docs
- **ADK GitHub**: https://github.com/google/adk
- **A2A Protocol Spec**: https://github.com/google/a2a-spec
- **Vertex AI Agent Engine Pricing**: https://cloud.google.com/agent-builder/pricing

---

*Last Updated: 2026-01-27*
