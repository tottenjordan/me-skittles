# Multi-Agent Deployment (A2A) on Agent Engine

Deploy agents in phases: leaf → functional → orchestrator.

### Phase 1: Deploy Leaf Agents

```python
from google.adk.agents import Agent
from vertexai.agent_engines import AdkApp
from google.adk.sessions import InMemorySessionService
import a2a
import os

def get_pto_balance(user_id: str) -> dict:
    """Gets PTO balance for a user."""
    return {"user_id": user_id, "balance": 15}

pto_agent = Agent(
    name="pto_agent",
    model="gemini-3.7-flash",
    instruction="You check PTO balances. Use get_pto_balance when asked.",
    tools=[get_pto_balance]
)

# Bundle a2a package
a2a_path = os.path.dirname(a2a.__file__)

pto_remote = client.agent_engines.create(
    agent=AdkApp(
        agent=pto_agent,
        session_service_builder=lambda **kwargs: InMemorySessionService()
    ),
    config={
        "display_name": "pto-agent",
        "requirements": [
            "google-cloud-aiplatform[agent_engines,a2a]",
            "google-adk[a2a]",
            "a2a-sdk>=1.1"
        ],
        "extra_packages": ["./agent_system", a2a_path],
        "staging_bucket": "gs://your-bucket"
    }
)

pto_url = f"https://us-central1-aiplatform.googleapis.com/v1/{pto_remote.resource_name}"
```

### Phase 2: Deploy Functional Agents

```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# Functional agent connects to leaf via A2A
# Pass leaf URL as environment variable
hr_remote = client.agent_engines.create(
    agent=AdkApp(
        agent=hr_agent,
        session_service_builder=lambda **kwargs: InMemorySessionService()
    ),
    config={
        "display_name": "hr-agent",
        "requirements": [...],
        "env_vars": {"PTO_AGENT_URL": pto_url},
        "extra_packages": ["./agent_system", a2a_path],
        "staging_bucket": "gs://your-bucket"
    }
)
```

### Phase 3: Deploy Orchestrator

```python
orch_remote = client.agent_engines.create(
    agent=AdkApp(
        agent=orchestrator_agent,
        session_service_builder=lambda **kwargs: InMemorySessionService()
    ),
    config={
        "display_name": "orchestrator",
        "requirements": [...],
        "env_vars": {
            "HR_AGENT_URL": hr_url,
            "FINANCE_AGENT_URL": finance_url
        },
        "extra_packages": ["./agent_system", a2a_path],
        "staging_bucket": "gs://your-bucket"
    }
)
```
