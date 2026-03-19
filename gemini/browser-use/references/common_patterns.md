# Browser-Use Common Patterns

## Table of Contents
- Data Extraction Patterns
- Form Automation Patterns
- Navigation Patterns
- Advanced Features

## Data Extraction Patterns

### Scraping Structured Data

```python
from browser_use import Agent, Browser, ChatBrowserUse
import asyncio

async def scrape_data():
    browser = Browser()
    llm = ChatBrowserUse()

    agent = Agent(
        task="Go to example.com/products and extract all product names and prices into a list",
        llm=llm,
        browser=browser,
    )

    result = await agent.run()
    await browser.close()
    return result
```

### Multi-Page Data Collection

```python
async def scrape_multiple_pages():
    agent = Agent(
        task="Go to example.com/articles, scrape the first 5 pages of articles, collecting title and author for each",
        llm=llm,
        browser=browser,
    )
    return await agent.run()
```

## Form Automation Patterns

### Simple Form Filling

```python
async def fill_form():
    agent = Agent(
        task="Go to example.com/contact, fill the form with name 'John Doe', email 'john@example.com', and submit",
        llm=llm,
        browser=browser,
    )
    return await agent.run()
```

### Multi-Step Forms

```python
async def multi_step_form():
    agent = Agent(
        task="""
        Go to example.com/signup and complete the multi-step registration:
        1. Step 1: Enter email 'user@example.com' and password 'SecurePass123'
        2. Step 2: Fill personal info - name 'Jane Doe', age '30'
        3. Step 3: Select preferences - interests in 'Technology' and 'Science'
        4. Review and submit
        """,
        llm=llm,
        browser=browser,
    )
    return await agent.run()
```

## Navigation Patterns

### Search and Navigate

```python
async def search_task():
    agent = Agent(
        task="Search Google for 'browser automation python' and open the first result",
        llm=llm,
        browser=browser,
    )
    return await agent.run()
```

### Conditional Navigation

```python
async def conditional_navigation():
    agent = Agent(
        task="""
        Go to example.com/dashboard.
        If there's a login page, log in with username 'user' and password 'pass'.
        Once on the dashboard, click on the 'Reports' section.
        """,
        llm=llm,
        browser=browser,
    )
    return await agent.run()
```

## Advanced Features

### Custom Tools Integration

```python
from browser_use import Agent, Browser, ChatBrowserUse, Controller

@Controller.action("Save data to file")
def save_data(data: str, filename: str):
    """Custom tool to save scraped data."""
    with open(filename, 'w') as f:
        f.write(data)
    return f"Data saved to {filename}"

async def automation_with_tools():
    browser = Browser()
    llm = ChatBrowserUse()
    controller = Controller()

    agent = Agent(
        task="Scrape product data from example.com and save it to products.txt",
        llm=llm,
        browser=browser,
        controller=controller,
    )

    result = await agent.run()
    await browser.close()
    return result
```

### Stealth Mode

```python
async def stealth_automation():
    browser = Browser(stealth=True)  # Enable stealth mode
    agent = Agent(
        task="Your task here",
        llm=llm,
        browser=browser,
    )
    return await agent.run()
```

### Cloud Browser

```python
async def cloud_automation():
    browser = Browser(
        cloud=True,
        cloud_provider="browserbase"  # or other providers
    )
    agent = Agent(
        task="Your task here",
        llm=llm,
        browser=browser,
    )
    return await agent.run()
```

## Error Handling

```python
async def robust_automation():
    browser = Browser()
    llm = ChatBrowserUse()

    try:
        agent = Agent(
            task="Your task description",
            llm=llm,
            browser=browser,
        )
        result = await agent.run()
        return result
    except Exception as e:
        print(f"Automation failed: {e}")
        return None
    finally:
        await browser.close()
```

## Performance Tips

1. **Use headless mode** for faster execution: `Browser(headless=True)`
2. **Reuse browser instances** for multiple tasks when possible
3. **Be specific in task descriptions** - clearer instructions lead to better results
4. **Use stealth mode** only when necessary to avoid detection overhead
5. **Close browsers properly** using `await browser.close()` in finally blocks
