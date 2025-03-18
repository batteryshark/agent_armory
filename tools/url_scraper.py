"""
URL Scraper Tool
"""
import os
import logging
import requests
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from mcp_server.utils.tool_decorator import mcp_tool

# Configure logging
logger = logging.getLogger(__name__)

class URLScraperInput(BaseModel):
    """Input model for URL scraping."""
    url: str = Field(description="The URL to scrape")

def extract_title_from_html(html_content: str) -> Optional[str]:
    """Extract title from HTML content using regex."""
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
    return title_match.group(1).strip() if title_match else None

def is_anti_bot_page(content: str) -> bool:
    """Check if the page is an anti-bot protection page."""
    anti_bot_indicators = [
        "Attention Required! | Cloudflare",
        "Just a moment...",
        "Security check",
        "Please verify you are a human",
        "Access Denied",
        "Bot Protection"
    ]
    return any(indicator in content for indicator in anti_bot_indicators)

# Define the tool name as a constant to ensure consistency
TOOL_NAME = "url_scraper"

@mcp_tool(
    name=TOOL_NAME,
    description="Safely scrape content from a given URL",
    input_model=URLScraperInput,
    required_env_vars=[],
    config_defaults={},  # Config is now only defined in url_scraper.yaml
    rate_limit=50,
    time_window=60
)
async def scrape_url(url: str, config: Dict[str, Any]) -> Dict:
    """Scrape content from a given URL with safety measures."""
    headers = {
        "User-Agent": config["user_agent"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    for attempt in range(config["max_retries"]):
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                return {
                    "status": "error",
                    "error": "Invalid URL format"
                }

            # Make request with streaming to handle large responses
            response = requests.get(
                url,
                headers=headers,
                stream=True,
                timeout=config["timeout"],
                allow_redirects=config["follow_redirects"]
            )
            response.raise_for_status()

            # Check for anti-bot protection
            content = ""
            size = 0
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    content += chunk
                    size += len(chunk.encode('utf-8'))
                    if size >= config["max_content_size"]:
                        content = content[:config["max_content_size"]]
                        break

            if is_anti_bot_page(content):
                return {
                    "status": "error",
                    "error": "Anti-bot protection detected"
                }

            # Extract title
            title = extract_title_from_html(content)

            return {
                "status": "success",
                "url": response.url,  # Final URL after redirects
                "content": content,
                "title": title
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Scraping attempt {attempt + 1} failed: {str(e)}")
            if attempt == config["max_retries"] - 1:
                return {
                    "status": "error",
                    "error": str(e)
                }
            continue
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

# Ensure tool metadata is properly set
scrape_url.TOOL_NAME = TOOL_NAME
scrape_url.TOOL_DESCRIPTION = "Safely scrape content from a given URL"
scrape_url.TOOL_SCHEMA = URLScraperInput.model_json_schema()
scrape_url.REQUIRED_ENV_VARS = [] 