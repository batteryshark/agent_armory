"""
Tool management for the MCP server.
"""
import os
import importlib
import logging
import functools
from typing import Dict, List, Any, Callable, Awaitable
from pathlib import Path
from mcp import types as mcp_types
from mcp_server.core.config import config
from mcp_server.utils.rate_limiter import RateLimiter
from mcp_server.utils.config_manager import config_manager
import sys
import json

# Configure logging
logger = logging.getLogger(__name__)

class ToolManager:
    """Manage MCP tools and their lifecycle."""
    
    def __init__(self, server):
        self.server = server
        self.tools: Dict[str, dict] = {}
        self.handlers: Dict[str, Callable] = {}  # Store handlers by tool name
        self.rate_limiters: Dict[str, RateLimiter] = {}
        
        # Register the global tool handler
        @server.app.call_tool()
        async def handle_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
            """Global tool handler that routes to the appropriate tool."""
            logger.debug(f"Global handler received call for tool: {name}")
            
            if name not in self.tools:
                error_msg = f"Unknown tool: {name}"
                logger.error(error_msg)
                return [mcp_types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "error": error_msg
                    })
                )]
            
            handler = self.handlers.get(name)
            if not handler:
                error_msg = f"Handler not found for tool: {name}"
                logger.error(error_msg)
                return [mcp_types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "error": error_msg
                    })
                )]
            
            # Apply rate limiting if configured
            rate_limiter = self.rate_limiters.get(name)
            if rate_limiter:
                rate_limiter.wait_for_slot()
            
            try:
                # Call the handler with the tool name and arguments
                result = await handler(name, arguments)
                if not result or not isinstance(result, list):
                    error_msg = f"Handler for {name} returned invalid response"
                    logger.error(error_msg)
                    return [mcp_types.TextContent(
                        type="text",
                        text=json.dumps({
                            "status": "error",
                            "error": error_msg
                        })
                    )]
                return result
            except Exception as e:
                error_msg = f"Error executing tool {name}: {str(e)}"
                logger.error(error_msg)
                return [mcp_types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "error": error_msg
                    })
                )]
        
    def wrap_tool_handler(self, handler: Callable, tool_name: str) -> Callable:
        """Wrap a tool handler with rate limiting if configured."""
        @functools.wraps(handler)
        async def wrapped_handler(name: str, arguments: dict) -> Any:
            # Apply rate limiting if configured
            rate_limiter = self.rate_limiters.get(tool_name)
            if rate_limiter:
                rate_limiter.wait_for_slot()
            return await handler(name, arguments)
        return wrapped_handler
        
    def load_tool(self, filename: str) -> bool:
        """Load a single tool module."""
        try:
            logger.info(f"Attempting to load tool from file: {filename}")
            
            # Import the tool module
            module_name = Path(filename).stem
            tool_path = config.tools_dir / filename
            
            if not tool_path.exists():
                logger.error(f"Tool file not found: {tool_path}")
                return False
                
            logger.debug(f"Loading module from path: {tool_path}")
            spec = importlib.util.spec_from_file_location(
                module_name,
                str(tool_path)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find the decorated function
            tool_func = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if hasattr(attr, 'register_tool'):
                    tool_func = attr
                    break
            
            if not tool_func:
                logger.warning(f"Tool {module_name} has no decorated function with register_tool")
                return False
                
            # Check required environment variables
            if hasattr(tool_func, 'REQUIRED_ENV_VARS'):
                missing_vars = [var for var in tool_func.REQUIRED_ENV_VARS if not os.getenv(var)]
                if missing_vars:
                    logger.error(f"Missing required environment variables for {module_name}: {missing_vars}")
                    return False
            
            logger.info(f"Loading configuration for tool: {module_name}")
            # Load tool configuration from config directory
            tool_config = config_manager.get_tool_config(module_name, refresh=True)
            
            # Store tool metadata using the tool's name as the key
            tool_name = tool_func.TOOL_NAME
            self.tools[tool_name] = {
                "name": tool_name,
                "description": tool_func.TOOL_DESCRIPTION,
                "schema": tool_func.TOOL_SCHEMA
            }
            logger.debug(f"Stored metadata for tool: {tool_name}")
            
            # Get the handler without registering it with the server
            handler = tool_func.register_tool(self.server.app, tool_config)
            self.handlers[tool_name] = handler
            logger.debug(f"Successfully stored handler for: {tool_name}")
            
            # Set up rate limiter if configured
            if hasattr(tool_func, '_tool_metadata') and tool_func._tool_metadata.rate_limit:
                self.rate_limiters[tool_name] = RateLimiter(
                    tool_func._tool_metadata.rate_limit,
                    tool_func._tool_metadata.rate_limit_window
                )
            
            logger.info(f"Successfully loaded tool: {module_name} as {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load tool {filename}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
    def load_tools_from_directory(self) -> List[str]:
        """Load all tool modules from the tools directory."""
        loaded_tools = []
        
        logger.info(f"Scanning directory for tools: {config.tools_dir}")
        
        # Load each .py file in the directory
        for path in config.tools_dir.glob("*.py"):
            if not path.name.startswith('__'):
                logger.debug(f"Found tool file: {path.name}")
                if self.load_tool(path.name):
                    loaded_tools.append(path.stem)
                    logger.info(f"Successfully loaded tool: {path.stem}")
                else:
                    logger.warning(f"Failed to load tool: {path.name}")
        
        logger.info(f"Finished loading tools. Loaded {len(loaded_tools)} tools: {loaded_tools}")
        return loaded_tools
        
    def reload_tool(self, tool_name: str):
        """Reload a specific tool."""
        logger.info(f"Attempting to reload tool: {tool_name}")
        try:
            # First unload the tool if it exists
            if tool_name in self.tools:
                logger.info(f"Unloading existing tool: {tool_name}")
                self.unload_tool(tool_name)
            
            # Try to load the tool file
            tool_file = f"{tool_name}.py"
            logger.info(f"Loading tool from file: {tool_file}")
            
            if not os.path.exists(os.path.join(config.tools_dir, tool_file)):
                logger.error(f"Tool file not found: {tool_file}")
                return
                
            # Force reload the module if it was previously imported
            module_name = f"tools.{tool_name}"
            if module_name in sys.modules:
                logger.info(f"Force reloading module: {module_name}")
                importlib.reload(sys.modules[module_name])
            
            # Load the tool
            if self.load_tool(tool_file):
                logger.info(f"Successfully reloaded tool: {tool_name}")
            else:
                logger.error(f"Failed to reload tool: {tool_name}")
        except Exception as e:
            logger.error(f"Error reloading tool {tool_name}: {str(e)}", exc_info=True)
            
    def reload_tools(self):
        """Reload all tools."""
        logger.info("Reloading all tools...")
        try:
            # Get list of current tools
            current_tools = list(self.tools.keys())
            logger.info(f"Current tools: {current_tools}")
            
            # Clear tracking dicts
            self.tools.clear()
            self.handlers.clear()
            self.rate_limiters.clear()
            logger.info("Cleared tool tracking dictionaries")
            
            # Load all tools
            loaded_tools = self.load_tools_from_directory()
            if loaded_tools:
                logger.info(f"Successfully reloaded tools: {loaded_tools}")
            else:
                logger.warning("No tools were loaded during reload")
                
        except Exception as e:
            logger.error(f"Error reloading tools: {str(e)}", exc_info=True)
            
    def unload_tool(self, tool_name: str):
        """Unload a specific tool."""
        logger.info(f"Unloading tool: {tool_name}")
        try:
            if tool_name in self.tools:
                # Remove from tracking dictionaries
                self.tools.pop(tool_name, None)
                self.handlers.pop(tool_name, None)
                self.rate_limiters.pop(tool_name, None)
                logger.info(f"Successfully unloaded tool: {tool_name}")
            else:
                logger.warning(f"Tool not found for unloading: {tool_name}")
        except Exception as e:
            logger.error(f"Error unloading tool {tool_name}: {str(e)}", exc_info=True)
            
    def get_tool_list(self) -> list[mcp_types.Tool]:
        """Get the current list of tools."""
        return [
            mcp_types.Tool(
                name=tool_info["name"],
                description=tool_info["description"],
                inputSchema=tool_info["schema"]
            )
            for tool_info in self.tools.values()
        ] 