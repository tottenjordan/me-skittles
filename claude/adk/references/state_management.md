# ADK State Management Best Practices

Source: https://google.github.io/adk-docs/sessions/state/

## Core Rules

### 1. NEVER Modify State on Retrieved Session Objects

```python
# WRONG - bypasses event tracking, breaks persistence
session = await session_service.get_session(...)
session.state['key'] = 'value'  # NOT PERSISTED

# RIGHT - use ToolContext or CallbackContext (framework-tracked)
def my_tool(tool_context: ToolContext):
    tool_context.state['key'] = 'value'  # AUTO-TRACKED

# RIGHT - use EventActions.state_delta (explicit persistence)
event = Event(
    actions=EventActions(state_delta={"key": "value"})
)
```

### 2. State Update Methods (Ranked by Use Case)

| Method | When to Use |
|--------|-------------|
| `output_key` on Agent | Save agent's final text response |
| `tool_context.state['key'] = val` | Inside tool functions |
| `callback_context.state['key'] = val` | Inside callbacks |
| `EventActions.state_delta` | BaseAgent orchestrators, manual events |

### 3. State Key Prefixes (Scope)

| Prefix | Scope | Persists? |
|--------|-------|-----------|
| (none) | Current session | Yes (with persistent SessionService) |
| `user:` | All sessions for user | Yes |
| `app:` | All users + sessions | Yes |
| `temp:` | Current invocation only | **NO** — discarded after invocation |

### 4. Value Requirements

- **Keys**: Always strings
- **Values**: Must be serializable — strings, numbers, booleans, simple lists/dicts
- **NO**: Custom class instances, functions, connections
- **Shallow structures**: Avoid deep nesting

## Agent Engine / Gemini Enterprise Patterns

### The Wave Problem

On Agent Engine (AE) and Gemini Enterprise (GE), each user message triggers an "invocation" (wave) with ~60s timeout. State ONLY persists between waves if saved via `state_delta` events.

### Critical: state_delta is the ONLY Way to Persist on AE

```python
# DOES NOT PERSIST across AE waves:
ctx.session.state['key'] = 'value'

# PERSISTS across AE waves:
event = Event(
    invocation_id=ctx.invocation_id,
    author=self.name,
    branch=ctx.branch,
    actions=EventActions(state_delta={"key": "value"}),
)
yield event

# Dual-write pattern (persist + same-invocation read):
ctx.session.state['key'] = 'value'  # For reading later in this invocation
event.actions.state_delta['key'] = 'value'  # For persistence across waves
yield event
```

### Per-Operation Persistence

Emit state_delta AFTER EACH significant operation, not batched at the end. AE waves can timeout mid-operation.

```python
# WRONG — all progress lost if wave times out before final yield
results = generate_all_images()  # 30s
save_event.actions.state_delta["images"] = results  # Only saved at end
yield save_event

# RIGHT — each image persisted immediately
for i, image in enumerate(generate_images_parallel()):
    per_img_event = self._status_event(ctx, f"Image {i+1} saved")
    per_img_event.actions.state_delta["images"] = current_list
    ctx.session.state["images"] = current_list  # Same-invocation read
    yield per_img_event
```

### output_key Does NOT Survive AE Waves

ADK Agent `output_key` writes to state but does NOT survive AE wave timeouts. Capture agent text from events and persist via state_delta:

```python
async def _run_agent_and_capture(self, ctx, agent_name, state_key):
    captured_text = ""
    async for event in target.run_async(ctx):
        yield event
        # Capture non-thought text
        if event.content:
            for part in event.content.parts or []:
                if part.text and not getattr(part, 'thought', False):
                    if len(part.text) > len(captured_text):
                        captured_text = part.text
    # Persist via state_delta (survives AE waves)
    if captured_text:
        persist_event = Event(actions=EventActions(
            state_delta={state_key: captured_text}
        ))
        ctx.session.state[state_key] = captured_text  # Same-invocation
        yield persist_event
```

### Sub-Agent Tool Writes Don't Survive AE Waves

When a sub-agent's tool writes to `tool_context.state`, those writes are tracked within the current invocation but may NOT persist across AE waves. The orchestrator must re-persist critical state via its own state_delta after each sub-agent completes:

```python
# After ad_creative_agent runs, re-persist its tool outputs
async for event in self._run_agent_and_capture(ctx, "ad_creative_agent", "output"):
    yield event
done_event = Event(actions=EventActions(state_delta={"_complete": True}))
# Re-persist tool outputs via orchestrator's state_delta
for key in ("final_ad_copies", "final_visual_concepts"):
    val = ctx.session.state.get(key)
    if val:
        done_event.actions.state_delta[key] = val
yield done_event
```

### Pre-Increment Failure Counters

For operations that can timeout (image gen, video gen), pre-increment the failure counter BEFORE the operation. Reset to 0 on success. This prevents infinite retry if the wave times out during the operation.

```python
# Pre-increment (saved before operation starts)
pre_event.actions.state_delta[f"_fail_{idx}"] = fail_count + 1
yield pre_event

# Do the operation (may timeout)
result = generate_image(prompt)

# Reset on success
success_event.actions.state_delta[f"_fail_{idx}"] = 0
yield success_event
```

### State Reconstruction from History

On GE, state_delta may not persist between waves, but conversation history does. Scan all past events to reconstruct missing state:

```python
async def _reconstruct_state_from_history(self, ctx):
    KEYS = {"key1", "key2", ...}
    reconstructed = {}
    for event in ctx.session.events or []:
        if event.actions and event.actions.state_delta:
            for key in KEYS:
                if key in event.actions.state_delta:
                    reconstructed[key] = event.actions.state_delta[key]
    # Only emit what's missing
    missing = {k: v for k, v in reconstructed.items() if not ctx.session.state.get(k)}
    if missing:
        for k, v in missing.items():
            ctx.session.state[k] = v  # Same-invocation
        yield Event(actions=EventActions(state_delta=missing))
```

### New Dict Creation for Mutable State

ADK state tracking may not detect in-place mutations. Always create NEW objects:

```python
# WRONG — in-place mutation may not be tracked
existing = state.get("images", [])
existing.append(new_image)  # Mutation not detected
state["images"] = existing

# RIGHT — new dict/list creation
existing = list(state.get("images", []))  # Copy
existing.append(new_image)
state["images"] = {"images": existing}  # New dict wrapper
```

### AE Dict Merging — Clearing Nested Keys

AE **merges** dict state_deltas instead of replacing them. Setting a parent dict to `{}` does NOT clear nested keys from prior waves.

```python
# WRONG — AE merges, so _pending_veo_op survives from prior wave
event.actions.state_delta["_commercial_clips"] = {}

# RIGHT — explicitly null the nested key
event.actions.state_delta["_commercial_clips"] = {"_pending_veo_op": ""}
ctx.session.state["_commercial_clips"] = {"_pending_veo_op": ""}
```

This is critical for any state dict tracking pending operations (Veo, long-poll jobs). If the nested key isn't explicitly nulled, the orchestrator re-enters the stage indefinitely.

### Sub-Agent Events Don't Propagate on AE (Platform Bug)

`target.run_async(ctx)` called from a BaseAgent orchestrator returns **0 events** on Agent Engine. Works locally. This means `_run_agent_and_capture()` captures empty text.

**Workaround**: Bypass sub-agent entirely with a direct model call:

```python
async def _generate_research_direct(self, ctx):
    """Generate research via direct model call (bypasses sub-agent)."""
    from google import genai
    client = genai.Client(vertexai=True)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            temperature=0.7,
        ),
    )
    return response.text or ""
```

**Limitation**: Direct calls cannot use ADK tools. For agents with tools (e.g., ad_creative_agent with `save_select_ad_copy`), either:
1. Parse tool calls from the response manually, or
2. Accept that the sub-agent may work intermittently on AE

### google_search Grounding Incompatibilities

- `google_search` (ADK grounding tool) returns **0 events** on `gemini-3-flash-preview` — use `gemini-2.0-flash` if grounding is needed
- `google_search` + non-search tools in same agent → error: "Multiple tools are supported only when they are all search tools"
- `google_search` as sub-agent tool on AE → 0 events (separate from the sub-agent propagation bug)

### Wave Budget Ordering Rule

In BaseAgent stage handlers, the **critical state-persisting operation MUST run first**. Optional operations (logging, analytics, Skill Council) go AFTER. AE waves have ~60s budget — if an optional operation consumes it, the critical write never happens.

```python
# WRONG — optional op consumes wave budget, report never saved
await run_skill_council()  # 50s
await save_final_report_tool()  # Wave timeout!

# RIGHT — critical op first
await save_final_report_tool()  # 5s, state_delta persisted
await run_skill_council()  # Best-effort, may timeout
```

## Checklist for AE/GE Readiness

- [ ] All state writes use `state_delta` events (not direct session.state mutation)
- [ ] state_delta emitted AFTER EACH significant operation (not batched)
- [ ] Failure counters pre-incremented before risky operations
- [ ] Sub-agent tool outputs re-persisted via orchestrator's state_delta
- [ ] `_reconstruct_state_from_history` covers all pipeline-critical keys
- [ ] No `output_key` relied upon for cross-wave persistence
- [ ] Key name aliases normalized (check tool saves vs orchestrator reads)
- [ ] Critical operations run FIRST in stage handlers (before optional ops)
- [ ] Completion flags prevent infinite re-entry on all stages
- [ ] Values are serializable (no custom objects, no deep nesting)
- [ ] Dict state_deltas explicitly null nested keys (AE merges, doesn't replace)
- [ ] Sub-agents tested on AE — use direct model call if events return empty
- [ ] google_search grounding only used with compatible models (gemini-2.0-flash)
- [ ] Absolute caps on retry loops (not just counter-based — pending ops can bypass counters)
