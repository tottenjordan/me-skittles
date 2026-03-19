#!/usr/bin/env python3
"""
Basic browser automation template using browser-use.
This script demonstrates the core pattern for AI-powered browser automation.
"""
import asyncio
from browser_use import Agent, Browser, ChatBrowserUse

async def automate_task(task_description: str, headless: bool = False):
    """
    Execute a browser automation task using AI.

    Args:
        task_description: Natural language description of what to do
        headless: Whether to run browser in headless mode

    Returns:
        Task execution history
    """
    browser = Browser(headless=headless)
    llm = ChatBrowserUse()

    agent = Agent(
        task=task_description,
        llm=llm,
        browser=browser,
    )

    try:
        history = await agent.run()
        return history
    finally:
        await browser.close()

def run_task(task: str, headless: bool = False):
    """Synchronous wrapper for running automation tasks."""
    return asyncio.run(automate_task(task, headless))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python basic_automation.py '<task description>'")
        sys.exit(1)

    task = sys.argv[1]
    headless = "--headless" in sys.argv

    print(f"Running task: {task}")
    result = run_task(task, headless)
    print(f"Task completed. Result: {result}")
