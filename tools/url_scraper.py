"""
URL Scraper Tool - Converts webpage content to markdown
"""
import re
import json
import logging
import requests
from typing import Dict, Any, List
from markdownify import markdownify
from requests.exceptions import RequestException
from pydantic import BaseModel, Field
from mcp_server.utils.tool_decorator import mcp_tool
from mcp import types as mcp_types

# Configure logging
logger = logging.getLogger(__name__)

# Define tool name as a constant
TOOL_NAME = "url_scraper"

class URLScraperInput(BaseModel):
    """Input model for URL scraping."""
    url: str = Field(description="The URL of the webpage to scrape")

def scrape_url_impl(url: str, config: Dict[str, Any]) -> Dict:
    """Implementation of the URL scraping functionality."""
    try:
        # Send GET request with configured headers
        headers = {"User-Agent": config["user_agent"]}
        response = requests.get(url, headers=headers, timeout=config["timeout"])
        response.raise_for_status()

        # Convert HTML to markdown
        markdown_content = markdownify(response.text).strip()
        
        # Clean up the markdown content
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        return {
            "status": "success",
            "content": markdown_content
        }
    except RequestException as e:
        logger.error(f"Error fetching webpage: {str(e)}")
        return {
            "status": "error",
            "error": f"Error fetching webpage: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "status": "error",
            "error": f"An unexpected error occurred: {str(e)}"
        }

@mcp_tool(
    name=TOOL_NAME,
    description="Scrapes a webpage and returns its content as markdown",
    input_model=URLScraperInput,
    required_env_vars=[],
    config_defaults={
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "timeout": 10
    },
    rate_limit=50,
    rate_limit_window=60
)
async def scrape_url(url: str, config: Dict[str, Any]) -> Dict:
    """Scrape content from a URL and convert it to markdown.
    
    Args:
        url: The URL to scrape
        config: Configuration dictionary containing user_agent and timeout settings
    
    Returns:
        Dictionary containing the scraped content and metadata
    """
    # Call the implementation function
    result = scrape_url_impl(url, config)
    
    # Return the result in the format expected by the decorator
    return result 