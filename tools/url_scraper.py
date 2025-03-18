"""
URL Scraper Tool - Converts webpage content to markdown, with support for JavaScript-rendered content
"""
import re
import json
import logging
import asyncio
import requests
import urllib3
from typing import Dict, Any, List
from markdownify import markdownify
from requests.exceptions import RequestException
from http.client import HTTPException
from pydantic import BaseModel, Field
from mcp_server.utils.tool_decorator import mcp_tool
from mcp import types as mcp_types
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Configure logging
logger = logging.getLogger(__name__)

# Define tool name as a constant
TOOL_NAME = "url_scraper"

class URLScraperInput(BaseModel):
    """Input model for URL scraping."""
    url: str = Field(description="The URL of the webpage to scrape")
    render_js: bool = Field(
        default=False,
        description="Whether to render JavaScript before scraping (slower but more accurate for dynamic content)"
    )

async def scrape_with_playwright(url: str, config: Dict[str, Any]) -> Dict:
    """Scrape content using Playwright with JavaScript rendering."""
    try:
        async with async_playwright() as p:
            # Launch browser with custom user agent
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=config["user_agent"],
                viewport={'width': 1920, 'height': 1080}  # Set a standard viewport
            )
            
            # Create new page and navigate
            page = await context.new_page()
            
            try:
                # First try with load event
                await page.goto(
                    url, 
                    wait_until="load",
                    timeout=config["timeout"] * 1000
                )
            except PlaywrightTimeout:
                logger.warning("Initial page load timed out, trying with domcontentloaded")
                # If that fails, try with just DOM content loaded
                await page.goto(
                    url, 
                    wait_until="domcontentloaded",
                    timeout=config["timeout"] * 1000
                )
            
            try:
                # Wait for the page to become mostly stable
                await page.wait_for_load_state("networkidle", timeout=5000)
            except PlaywrightTimeout:
                logger.warning("Network idle wait timed out, proceeding with current state")
            
            # Additional wait for any lazy-loaded content
            try:
                # Scroll to bottom to trigger lazy loading
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)  # Brief pause for content to load
            except Exception as e:
                logger.warning(f"Scroll attempt failed: {e}")
            
            # Get the rendered HTML
            content = await page.content()
            
            # Convert to markdown
            markdown_content = markdownify(content).strip()
            markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)
            
            await browser.close()
            
            return {
                "status": "success",
                "content": markdown_content
            }
            
    except Exception as e:
        logger.error(f"Error scraping with Playwright: {str(e)}")
        return {
            "status": "error",
            "error": f"Error scraping with Playwright: {str(e)}"
        }

def scrape_with_urllib3(url: str, config: Dict[str, Any]) -> Dict:
    """Fallback scraping implementation using urllib3 for cases where requests fails."""
    try:
        http = urllib3.PoolManager(
            headers={"User-Agent": config["user_agent"]},
            timeout=urllib3.Timeout(connect=config["timeout"], read=config["timeout"])
        )
        response = http.request("GET", url)
        
        if response.status >= 400:
            raise urllib3.exceptions.HTTPError(f"HTTP {response.status}")

        markdown_content = markdownify(response.data.decode('utf-8')).strip()
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        return {
            "status": "success",
            "content": markdown_content
        }
    except Exception as e:
        logger.error(f"Error fetching webpage with urllib3: {str(e)}")
        return {
            "status": "error",
            "error": f"Error fetching webpage with urllib3: {str(e)}"
        }

def scrape_with_requests(url: str, config: Dict[str, Any]) -> Dict:
    """Simple scraping implementation using requests."""
    try:
        headers = {"User-Agent": config["user_agent"]}
        response = requests.get(url, headers=headers, timeout=config["timeout"])
        response.raise_for_status()

        markdown_content = markdownify(response.text).strip()
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        return {
            "status": "success",
            "content": markdown_content
        }
    except (HTTPException, RequestException) as e:
        # If we hit header limits or other request issues, try urllib3
        logger.warning(f"Requests failed, falling back to urllib3: {str(e)}")
        return scrape_with_urllib3(url, config)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "status": "error",
            "error": f"An unexpected error occurred: {str(e)}"
        }

@mcp_tool(
    name=TOOL_NAME,
    description="Scrapes a webpage and returns its content as markdown, with optional JavaScript rendering support",
    input_model=URLScraperInput,
    required_env_vars=[],
    config_defaults={
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "timeout": 30  # Increased timeout for JS rendering
    },
    rate_limit=50,
    rate_limit_window=60
)
async def scrape_url(url: str, render_js: bool = False, config: Dict[str, Any] = None) -> Dict:
    """Scrape content from a URL and convert it to markdown.
    
    Args:
        url: The URL to scrape
        render_js: Whether to render JavaScript before scraping
        config: Configuration dictionary containing user_agent and timeout settings
    
    Returns:
        Dictionary containing the scraped content and metadata
    """
    if config is None:
        config = {}
    
    # Ensure we have default config values
    default_config = {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "timeout": 30
    }
    config = {**default_config, **config}
    
    if render_js:
        return await scrape_with_playwright(url, config)
    else:
        return scrape_with_requests(url, config) 