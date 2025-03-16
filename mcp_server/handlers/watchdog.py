"""
File system watchdog for monitoring tool and configuration changes.
"""
import time
import logging
from pathlib import Path
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
from mcp_server.core.config import config

# Configure logging
logger = logging.getLogger(__name__)

class ToolDirectoryHandler(FileSystemEventHandler):
    """Handle file system events in the tools directory."""
    def __init__(self, server):
        self.server = server
        self.last_reload = 0
        logger.info("ToolDirectoryHandler initialized")
        
    def _should_handle_event(self, event) -> bool:
        """Check if we should handle this event."""
        if event.is_directory:
            logger.debug(f"Ignoring directory event: {event.src_path}")
            return False
            
        current_time = time.time()
        if current_time - self.last_reload < config.reload_delay:
            logger.debug(f"Ignoring event due to reload delay: {event.src_path}")
            return False
            
        logger.debug(f"Should handle event: {event.src_path}")
        return True
        
    def _get_tool_name(self, event) -> str:
        """Extract tool name from event path."""
        path = Path(event.src_path)
        return path.stem
        
    def on_modified(self, event):
        logger.info(f"[TOOL] Modification detected: {event.src_path}")
        if not self._should_handle_event(event):
            return
            
        path = Path(event.src_path)
        
        # Handle tool files
        if path.parent == config.tools_dir and path.suffix == '.py' and not path.name.startswith('__'):
            self.last_reload = time.time()
            logger.info(f"[TOOL] Reloading tool due to file change: {path.name}")
            try:
                self.server.reload_tool(path.stem)
                logger.info(f"[TOOL] Successfully reloaded tool: {path.stem}")
            except Exception as e:
                logger.error(f"[TOOL] Failed to reload tool {path.stem}: {str(e)}", exc_info=True)
            
    def on_created(self, event):
        logger.info(f"[TOOL] Creation detected: {event.src_path}")
        if not self._should_handle_event(event):
            return
            
        path = Path(event.src_path)
        
        # Handle new tool files
        if path.parent == config.tools_dir and path.suffix == '.py' and not path.name.startswith('__'):
            logger.info(f"[TOOL] Loading new tool: {path.name}")
            try:
                self.server.reload_tool(path.stem)
                logger.info(f"[TOOL] Successfully loaded new tool: {path.stem}")
            except Exception as e:
                logger.error(f"[TOOL] Failed to load new tool {path.stem}: {str(e)}", exc_info=True)
            
    def on_deleted(self, event):
        logger.info(f"[TOOL] Deletion detected: {event.src_path}")
        if not self._should_handle_event(event):
            return
            
        path = Path(event.src_path)
        
        # Handle deleted tool files
        if path.parent == config.tools_dir and path.suffix == '.py' and not path.name.startswith('__'):
            logger.info(f"[TOOL] Unloading deleted tool: {path.name}")
            try:
                self.server.unload_tool(path.stem)
                logger.info(f"[TOOL] Successfully unloaded tool: {path.stem}")
            except Exception as e:
                logger.error(f"[TOOL] Failed to unload tool {path.stem}: {str(e)}", exc_info=True)

class ConfigDirectoryHandler(FileSystemEventHandler):
    """Handle file system events in the config directory."""
    def __init__(self, server):
        self.server = server
        self.last_reload = 0
        logger.info("ConfigDirectoryHandler initialized")
        
    def _should_handle_event(self, event) -> bool:
        """Check if we should handle this event."""
        if event.is_directory:
            logger.debug(f"Ignoring directory event: {event.src_path}")
            return False
            
        current_time = time.time()
        if current_time - self.last_reload < config.reload_delay:
            logger.debug(f"Ignoring event due to reload delay: {event.src_path}")
            return False
            
        logger.debug(f"Should handle event: {event.src_path}")
        return True
        
    def on_modified(self, event):
        logger.info(f"[CONFIG] Modification detected: {event.src_path}")
        if not self._should_handle_event(event):
            return
            
        path = Path(event.src_path)
        
        # Handle config files
        if path.parent == config.config_dir and path.suffix == '.yaml':
            self.last_reload = time.time()
            logger.info(f"[CONFIG] Reloading tool due to config change: {path.name}")
            try:
                self.server.reload_tool(path.stem)
                logger.info(f"[CONFIG] Successfully reloaded tool: {path.stem}")
            except Exception as e:
                logger.error(f"[CONFIG] Failed to reload tool {path.stem}: {str(e)}", exc_info=True) 