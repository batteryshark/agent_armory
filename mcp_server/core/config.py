"""
Configuration management for the MCP server.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ServerConfig:
    """Server configuration management."""
    
    def __init__(self):
        # Server settings
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        self.port = int(os.getenv("MCP_SERVER_PORT", "32823"))
        self.host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")  # Default to localhost
        self.name = os.getenv("MCP_SERVER_NAME", "MCP Tool Server")
        self.reload_delay = float(os.getenv("MCP_RELOAD_DELAY", "1.0"))
        
        # Directory paths
        self.tools_dir = self._resolve_path(
            os.getenv("MCP_TOOLS_DIR"),
            "tools"
        )
        self.config_dir = self._resolve_path(
            os.getenv("MCP_CONFIG_DIR"),
            "config"
        )
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Log configuration on init
        self._log_config()
        
    def _resolve_path(self, env_path: Optional[str], default_name: str) -> Path:
        """Resolve a directory path from environment or default."""
        if env_path:
            return Path(env_path).resolve()
        return Path.cwd() / default_name
        
    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    def _log_config(self):
        """Log the current configuration."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Server Configuration:")
        logger.info(f"  Host: {self.host}")
        logger.info(f"  Port: {self.port}")
        logger.info(f"  Debug Mode: {self.debug_mode}")
        logger.info(f"  Tools Directory: {self.tools_dir}")
        logger.info(f"  Config Directory: {self.config_dir}")

# Global configuration instance
config = ServerConfig() 