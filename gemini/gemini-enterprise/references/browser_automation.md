# GE Browser Automation & Parsing

Patterns for automating and parsing the Gemini Enterprise web UI using Playwright + CDP.

## Shadow DOM Challenge

GE's UI is built with web components and deep shadow DOM. Standard Playwright selectors (`innerText`, `querySelector`) cannot see chat content.

### What Works

| Method | Sees Shadow DOM | Sees JS Source | Recommended |
|--------|:-:|:-:|:-:|
| `document.body.innerText` | No | No | Only for nav/header text |
| `getAllText(shadowRoot)` with `textContent` | Yes | YES (false positives) | No |
| `getAllText(shadowRoot)` with `innerText` | Partial | No | Fragile |
| **CDP `Accessibility.getFullAXTree`** | **Yes** | **No** | **Yes** |
| Playwright `page.locator("text=...")` | Partial | No | For buttons only |

### CDP Accessibility Tree (Recommended)

```python
async def get_ax_text(page):
    """Extract all visible text from GE page via CDP Accessibility tree."""
    cdp = await page.context.new_cdp_session(page)
    tree = await cdp.send("Accessibility.getFullAXTree")
    await cdp.detach()
    texts = []
    for node in tree.get("nodes", []):
        name = node.get("name", {}).get("value", "")
        if name and len(name) > 3:
            texts.append(name)
    return " ".join(texts)
```

This penetrates all shadow DOM boundaries and returns only visible text (no scripts).

## GE Chat UI Elements

### Chat Input
```python
# Standard selector works — input is NOT in deep shadow DOM
for sel in ['div[contenteditable="true"]', 'textarea']:
    el = await page.wait_for_selector(sel, timeout=5000)
    if el and await el.is_visible():
        await el.click()
        break
```

### @mention Agent Dropdown
```python
# Type @AgentName to trigger dropdown
await page.keyboard.type("@Trend", delay=80)
await page.wait_for_timeout(2500)

# Click agent from dropdown (locator works for dropdown items)
try:
    loc = page.locator("text=Trends2Insights").first
    if await loc.count() > 0:
        await loc.click()
except:
    # Fallback: keyboard navigation
    await page.keyboard.press("ArrowDown")
    await page.keyboard.press("Enter")
```

### Clear Agent Bar (CRITICAL)
After sending a message with `@AgentName`, the agent bar stays selected.
Subsequent messages route to that agent, not the root orchestrator.

```python
# Clear the agent bar so "continue" goes to root orchestrator
btn = await page.wait_for_selector('button[aria-label*="clear"]', timeout=2000)
if btn and await btn.is_visible():
    await btn.click()
```

AX tree shows: `"Trends2Insights Button to clear the selected agent and close the agent bar."`

### New Chat Button
```python
btn = await page.wait_for_selector('button:has-text("New chat")', timeout=5000)
if btn:
    await btn.click()
```

## CDP Connection

GE tests connect to an existing Chrome instance via CDP:

```python
# Chrome must be running with --remote-debugging-port=9222
# For headless/virtual display: DISPLAY=:20
browser = await p.chromium.connect_over_cdp("http://localhost:9222")
page = browser.contexts[0].pages[0]
```

## Pipeline Stage Detection

Using AX text, detect pipeline stages by keyword matching:

```python
def detect_stages(ax_text):
    lower = ax_text.lower()
    stages = {}
    stages["TRENDS"] = "search trend" in lower or "youtube trend" in lower
    stages["RESEARCH"] = "research report" in lower or "research findings" in lower
    stages["AD_COPY"] = "ad copy" in lower or "headline" in lower or "tagline" in lower
    stages["IMAGES"] = "generating image" in lower or "generated image" in lower
    stages["VIDEO"] = "veo" in lower or "commercial" in lower
    stages["FOCUS_GROUP"] = "focus group" in lower or "panelist" in lower
    stages["PDF"] = "campaign brief" in lower or "final report" in lower
    stages["THINKING"] = "thinking" in lower
    stages["STATUS"] = "running" in lower
    return stages
```

**False positive warning:** The user's original message may contain terms like "focus group", "commercial", "pdf". Use text growth from baseline to distinguish real stage detection from prompt echoing.

## GE Chat URL

```
https://vertexaisearch.cloud.google.com/home/cid/{conversation_id}?hl=en_US
```

The conversation ID can be found in the GE dashboard or from the URL after starting a chat.

## Chrome CDP Authentication (for SSH sessions)

Chrome with `--remote-debugging-port=9222` requires a **non-default** `--user-data-dir`. The default `~/.config/google-chrome` path is blocked.

### Working pattern:
```bash
# Use the chrome-data profile (non-default path)
DISPLAY=:20 /opt/google/chrome/chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=$HOME/.config/chrome-data \
  --no-first-run --no-sandbox --disable-setuid-sandbox \
  --disable-dev-shm-usage --ozone-platform=x11 \
  --window-size=1920,1080 "about:blank"
```

### Login automation via Playwright:
```python
# Type email
email = await page.wait_for_selector('input[type="email"]')
await email.fill('admin@jwortz.altostrat.com')
await page.locator('button:has-text("Next")').click()

# Type password (after page loads)
pw = await page.wait_for_selector('input[type="password"]')
await pw.fill(password)
await page.locator('button:has-text("Next")').click()

# Handle 2FA code input
code_input = await page.wait_for_selector('input')  # code field
await code_input.fill(code)
await page.locator('button:has-text("Next")').click()
```

### Key facts:
- `--user-data-dir=~/.config/google-chrome` **BLOCKED** — Chrome says "DevTools remote debugging requires a non-default data directory"
- Cookie encryption is per-profile OS keyring — copying profiles doesn't transfer auth
- CRD Chrome (started by chrome-remote-desktop) uses the default profile without CDP
- Must log in interactively after launching CDP Chrome with non-default profile

## Welcome Modal

GE shows a "Welcome to Gemini Enterprise!" modal on first visit. Dismiss it:
```python
loc = page.locator("text=Get started")
if await loc.count() > 0:
    await loc.first.click()
    await page.wait_for_timeout(3000)
```
**Important:** "Get started" is NOT a `<button>` — use `page.locator("text=...")` not `page.wait_for_selector('button:has-text(...)')`.

## Key Gotchas

1. **Agent bar may not persist**: In newer GE versions (2026-03), the agent bar does NOT stay selected after @mention. Check AX tree for "Button to clear the selected agent" before attempting to clear — if not found, skip clearing. Wrap all clear operations in try/except.
2. **Shadow DOM text**: Only CDP `Accessibility.getFullAXTree` reliably extracts chat content.
3. **False positives**: The user's prompt contains pipeline keywords. Track text growth from a baseline measurement.
4. **GE response timing**: Agents take 30-120s to respond. Use 30s polling intervals.
5. **Thinking is transient**: "Thinking" appears mid-response then disappears. Capture it per-wave, not at final check.
6. **"continue" routing**: If agent bar IS present, clear it. Otherwise "continue" already routes correctly.
7. **Input element fragility**: GE UI placeholder text changes across versions. Use multiple fallback selectors:
   ```python
   SELECTORS = [
       'div[contenteditable="true"]',
       'textarea',
       '[role="textbox"]',
       'rich-textarea',
   ]
   ```
   Also try clicking "Ask a follow-up" or "Ask Gemini" text as fallback.
8. **Screenshot timeouts**: GE pages with heavy shadow DOM can cause `Page.screenshot` to timeout waiting for fonts. Wrap screenshot capture in try/except with short timeout (10s).
9. **Decouple browser UI from critic**: The Ralph Loop critic can evaluate pipeline quality from API output + GCS-downloaded images alone. Browser screenshots are nice-to-have but not required for PASS/FAIL scoring.
10. **TargetClosedError**: Page/browser can close during long operations. Wrap all Playwright calls in try/except for `TargetClosedError`.
