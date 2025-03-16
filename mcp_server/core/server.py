"""
MCP Server with dynamic tool loading and hot reloading during development.
"""
import logging
import threading
import time
import os
from typing import Optional
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from mcp.server.lowlevel import Server
from mcp.server.sse import SseServerTransport
from watchdog.observers import Observer
from mcp_server.core.config import config
from mcp_server.core.tool_manager import ToolManager
from mcp_server.handlers.watchdog import ToolDirectoryHandler, ConfigDirectoryHandler

# Configure logging
logger = logging.getLogger(__name__)

class MCPToolServer:
    """MCP Tool Server with dynamic tool loading and hot reloading."""
    
    def __init__(self):
        """Initialize the MCP Tool Server."""
        self.app = Server(config.name)
        self.tool_manager = ToolManager(self)
        self.observers: list[Observer] = []
        self.watchdog_threads: list[threading.Thread] = []
        self.is_running = True  # Set this to True during initialization
        
        # Set up SSE transport
        self.sse = SseServerTransport("/messages/")
        
        # Register tool listing handler
        @self.app.list_tools()
        async def list_tools():
            return self.tool_manager.get_tool_list()
        
        # Set up watchdog in debug mode
        if config.debug_mode:        
            self.setup_watchdog()
            logger.info("Running in DEBUG mode with hot reloading enabled")
            
        # Load tools after watchdog is set up
        self.tool_manager.load_tools_from_directory()
        
    async def handle_sse(self, request):
        """Handle SSE connection."""
        async with self.sse.connect_sse(
            request.scope,
            request.receive,
            request._send
        ) as streams:
            await self.app.run(
                streams[0],
                streams[1],
                self.app.create_initialization_options()
            )
    
    def setup_routes(self):
        """Set up Starlette routes."""
        return Starlette(
            debug=config.debug_mode,
            routes=[
                Route("/sse", endpoint=self.handle_sse),
                Mount("/messages/", app=self.sse.handle_post_message),
            ],
        )
        
    def run_watchdog(self, observer: Observer):
        """Run a watchdog observer in a separate thread."""
        thread_id = threading.get_ident()
        logger.info(f"Watchdog thread {thread_id} started")
        try:
            while self.is_running:
                #logger.debug(f"Watchdog thread {thread_id} is alive")
                time.sleep(1)  # Keep thread alive but don't busy-wait
        except Exception as e:
            logger.error(f"Watchdog thread {thread_id} error: {str(e)}", exc_info=True)
        finally:
            logger.info(f"Stopping watchdog thread {thread_id}...")
            observer.stop()
            observer.join()
            logger.info(f"Watchdog thread {thread_id} stopped")
        
    def setup_watchdog(self):
        """Set up watchdogs for the tools and config directories."""
        if not config.debug_mode:
            logger.warning("Debug mode is disabled, watchdog will not start")
            return
            
        logger.info("Setting up file system watchdogs...")
        logger.info(f"Current working directory: {os.getcwd()}")
        
        # Set up tools directory watchdog
        tools_observer = Observer()
        tools_handler = ToolDirectoryHandler(self)
        tools_path = str(config.tools_dir.resolve())
        logger.info(f"Setting up tools watchdog for directory: {tools_path}")
        logger.info(f"Tools directory exists: {os.path.exists(tools_path)}")
        tools_observer.schedule(tools_handler, tools_path, recursive=False)
        tools_observer.start()
        self.observers.append(tools_observer)
        logger.info("Tools directory watchdog started")
        
        # Set up config directory watchdog
        config_observer = Observer()
        config_handler = ConfigDirectoryHandler(self)
        config_path = str(config.config_dir.resolve())
        logger.info(f"Setting up config watchdog for directory: {config_path}")
        logger.info(f"Config directory exists: {os.path.exists(config_path)}")
        config_observer.schedule(config_handler, config_path, recursive=False)
        config_observer.start()
        self.observers.append(config_observer)
        logger.info("Config directory watchdog started")
        
        # Start watchdog threads
        logger.info("Starting watchdog threads...")
        for observer in self.observers:
            thread = threading.Thread(target=self.run_watchdog, args=(observer,))
            thread.daemon = True
            thread.start()
            thread_id = thread.ident
            self.watchdog_threads.append(thread)
            logger.info(f"Started watchdog thread {thread_id}")
            
        logger.info(f"All watchdogs started and running. Active threads: {len(self.watchdog_threads)}")
        
    def cleanup_watchdog(self):
        """Clean up watchdog observers and threads."""
        logger.info("Beginning watchdog cleanup...")
        self.is_running = False
        
        # Stop and join watchdog threads
        for i, thread in enumerate(self.watchdog_threads):
            logger.info(f"Stopping watchdog thread {thread.ident} ({i+1}/{len(self.watchdog_threads)})")
            thread.join(timeout=2)
            if thread.is_alive():
                logger.warning(f"Watchdog thread {thread.ident} did not stop cleanly")
            
        # Stop and join observers
        for i, observer in enumerate(self.observers):
            logger.info(f"Stopping observer {i+1}/{len(self.observers)}")
            observer.stop()
            observer.join()
            
        logger.info("Watchdogs stopped and cleaned up")
    
    def reload_tool(self, tool_name: str):
        """Reload a specific tool."""
        self.tool_manager.reload_tool(tool_name)
        
    def reload_tools(self):
        """Reload all tools."""
        self.tool_manager.reload_tools()
        
    def unload_tool(self, tool_name: str):
        """Unload a specific tool."""
        self.tool_manager.unload_tool(tool_name)
    
    def run(self):
        """Start the MCP server."""
        try:
            logger.info(f"Starting {config.name}")
            logger.info(f"Loaded tools: {list(self.tool_manager.tools.keys())}")
            
            # Run the server using uvicorn
            server_config = uvicorn.Config(
                self.setup_routes(),
                host=config.host,
                port=config.port,
                log_level="info"
            )
            server = uvicorn.Server(server_config)
            server.run()
            
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
        finally:
            self.is_running = False
            self.cleanup_watchdog() 