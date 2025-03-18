"""
Decorator utilities for creating MCP tools.
"""
import os
import json
import functools
import logging
from typing import Any, Dict, List, Optional, Type, get_type_hints
from dataclasses import dataclass, field
from pydantic import BaseModel, create_model
from mcp import types as mcp_types

logger = logging.getLogger(__name__)

@dataclass
class ToolMetadata:
    """Tool metadata configuration."""
    name: str
    description: str
    required_env_vars: List[str] = field(default_factory=list)
    config_defaults: Dict[str, Any] = field(default_factory=dict)
    rate_limit: Optional[int] = None
    rate_limit_window: int = 60

def mcp_tool(
    name: str,
    description: str,
    *,
    input_model: Optional[Type[BaseModel]] = None,
    required_env_vars: List[str] = None,
    config_defaults: Dict[str, Any] = None,
    rate_limit: Optional[int] = None,
    rate_limit_window: int = 60
):
    """
    Decorator to create an MCP tool from a function.
    
    Example:
    ```python
    from pydantic import BaseModel
    
    class WebSearchInput(BaseModel):
        query: str = Field(description="The search query to process")
    
    @mcp_tool(
        name="web_search",
        description="Search the web for information",
        input_model=WebSearchInput,
        required_env_vars=["API_KEY"],
        config_defaults={
            "max_results": 10,
            "timeout": 5
        },
        rate_limit=100,
        rate_limit_window=60
    )
    async def search_web(query: str, config: Dict[str, Any]) -> Dict:
        # Your implementation here
        pass
    ```
    """
    def decorator(func):
        # Create input model from function signature if not provided
        nonlocal input_model
        if input_model is None:
            hints = get_type_hints(func)
            # Remove 'config' and 'return' from hints
            hints = {k: v for k, v in hints.items() 
                    if k not in ('config', 'return')}
            input_model = create_model(
                f"{func.__name__.title()}Input",
                **hints
            )
        
        # Store metadata
        metadata = ToolMetadata(
            name=name,
            description=description,
            required_env_vars=required_env_vars or [],
            config_defaults=config_defaults or {},
            rate_limit=rate_limit,
            rate_limit_window=rate_limit_window
        )
        
        @functools.wraps(func)
        async def wrapped_func(*args, **kwargs):
            return await func(*args, **kwargs)
            
        # Transfer metadata to wrapped function
        wrapped_func._tool_metadata = metadata
        wrapped_func.TOOL_NAME = name
        wrapped_func.TOOL_DESCRIPTION = description
        wrapped_func.TOOL_SCHEMA = input_model.model_json_schema()
        wrapped_func.REQUIRED_ENV_VARS = required_env_vars or []
        
        def register_tool(server, config: Dict[str, Any]):
            """Create and return a handler for this tool."""
            # Merge defaults with provided config
            tool_config = {
                **metadata.config_defaults,
                **(config or {})
            }
            
            # Create the handler function
            async def handle_tool(tool_name: str, arguments: dict) -> list[mcp_types.TextContent]:
                logger.debug(f"Tool handler called for {tool_name}")
                
                try:
                    # Validate input using the model
                    validated_input = input_model(**arguments)
                    
                    # Call the tool function with validated input and config
                    result = await wrapped_func(**validated_input.model_dump(), config=tool_config)
                    
                    # Handle different return types
                    if isinstance(result, (str, int, float, bool)):
                        result = {"result": result}
                    elif isinstance(result, list):
                        result = {"results": result}
                    
                    # Return as MCP TextContent
                    return [mcp_types.TextContent(
                        type="text",
                        text=json.dumps(result)
                    )]
                except Exception as e:
                    logger.error(f"Error in tool {tool_name}: {str(e)}")
                    return [mcp_types.TextContent(
                        type="text",
                        text=json.dumps({
                            "status": "error",
                            "error": str(e)
                        })
                    )]
            
            # Just return the handler, don't register it
            return handle_tool
        
        # Attach registration function to wrapped function
        wrapped_func.register_tool = register_tool
        
        return wrapped_func
    
    return decorator 