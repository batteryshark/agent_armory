"""
Gemini Web Search Tool
"""
import os
import json
import time
import aiohttp
import logging
import requests
import re
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from mcp_server.utils.tool_decorator import mcp_tool

# Configure logging
logger = logging.getLogger(__name__)

class WebSearchInput(BaseModel):
    """Input model for web search."""
    query: str = Field(description="The search query to process")

def extract_title_from_html(html_content: str) -> Optional[str]:
    """Extract title from HTML content using regex."""
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
    return title_match.group(1).strip() if title_match else None

def follow_redirect(url: str, timeout: int = 5, follow_redirects: bool = True) -> tuple[str, Optional[str]]:
    """Follow a URL redirect and return the final URL and page title."""
    try:
        head_response = requests.head(url, allow_redirects=follow_redirects, timeout=timeout)
        final_url = head_response.url if follow_redirects else url
        
        if not follow_redirects:
            return final_url, None
        
        response = requests.get(final_url, stream=True, timeout=timeout)
        content = next(response.iter_content(8192)).decode('utf-8', errors='ignore')
        response.close()
        
        title = extract_title_from_html(content)
        
        # Return None for title if it's a Cloudflare attention page
        if title and ("Attention Required! | Cloudflare" in title or 
                     "Just a moment..." in title or 
                     "Security check" in title):
            return final_url, None
            
        return final_url, title
    except:
        return url, None

def extract_references(response, max_references: int = 10, include_confidence: bool = True) -> List[Dict]:
    """Extract detailed references from Gemini response."""
    try:
        # Convert response to raw format to access grounding metadata
        raw_response = json.loads(response.model_dump_json())
        grounding_metadata = raw_response["candidates"][0]["grounding_metadata"]
        
        references = []
        
        for support in grounding_metadata["grounding_supports"]:
            if len(references) >= max_references:
                break
                
            for chunk_idx in support["grounding_chunk_indices"]:
                chunk = grounding_metadata["grounding_chunks"][chunk_idx]
                if "web" in chunk:
                    # Follow URL and get actual title
                    url = chunk["web"]["uri"]
                    final_url, actual_title = follow_redirect(url)
                    
                    reference = {
                        "content": support["segment"]["text"],
                        "url": final_url,
                        "title": actual_title or chunk["web"].get("title", "")  # Fallback to Gemini-provided title
                    }
                    
                    if include_confidence:
                        reference["confidence"] = support["confidence_scores"][0] if support["confidence_scores"] else None
                    
                    references.append(reference)
                    
                    if len(references) >= max_references:
                        break
        
        return references
    except Exception as e:
        logger.error(f"Error extracting references: {e}")
        return []

@mcp_tool(
    name="gemini_web_search",
    description="Web search tool powered by Gemini Search API",
    input_model=WebSearchInput,
    required_env_vars=[],  # Remove environment variable requirement
    config_defaults={
        "max_retries": 3,
        "gemini_model": "gemini-2.0-flash",
        "max_references": 10,
        "include_confidence_scores": True,
        "timeout": 5,
        "follow_redirects": True,
        "gemini_api_key": None  # Must be provided in config
    },
    rate_limit=100,
    rate_limit_window=60
)
async def search_web(query: str, config: Dict[str, Any]) -> Dict:
    """Perform a web search using Gemini API."""
    if not config.get("gemini_api_key"):
        logger.error("Gemini API key not provided in tool configuration")
        return {
            "status": "error",
            "error": "Gemini API key not provided in tool configuration"
        }
        
    for attempt in range(config["max_retries"]):
        try:
            # Initialize Gemini client with config API key
            client = genai.Client(api_key=config["gemini_api_key"])
            
            # Generate content using Gemini
            response = client.models.generate_content(
                model=config["gemini_model"],
                contents=f"Search the web for this information and summarize what you find: {query}",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            
            # Extract all metadata from response
            raw_response = json.loads(response.model_dump_json())
            grounding_metadata = raw_response["candidates"][0]["grounding_metadata"]
            
            # Extract references with detailed information
            references = extract_references(
                response,
                max_references=config["max_references"],
                include_confidence=config["include_confidence_scores"]
            )
            
            # Return structured response
            return {
                "status": "success",
                "data": {
                    "prompt": query,
                    "search_query": grounding_metadata["web_search_queries"],
                    "response": response.text,
                    "references": references
                }
            }
        except Exception as e:
            logger.error(f"Search attempt {attempt + 1} failed: {str(e)}")
            if attempt == config["max_retries"] - 1:
                return {
                    "status": "error",
                    "error": str(e)
                }
            time.sleep(1)  # Wait before retrying
