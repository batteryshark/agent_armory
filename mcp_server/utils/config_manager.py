"""
Configuration management for MCP tools.
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from mcp_server.core.config import config

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages tool configurations."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self.env_overrides = {}
        
        # Load environment variables
        load_dotenv()
        
        # Cache environment overrides
        self._cache_env_overrides()
    
    def _cache_env_overrides(self):
        """Cache all environment variables that could override tool configs."""
        for key in os.environ:
            # Look for tool-specific environment variables
            # Format: TOOL_NAME__CONFIG_KEY=value (double underscore separator)
            if '__' in key:
                tool_name, config_key = key.lower().split('__', 1)
                if tool_name not in self.env_overrides:
                    self.env_overrides[tool_name] = {}
                self.env_overrides[tool_name][config_key] = os.getenv(key)
    
    def get_tool_config(self, tool_name: str, refresh: bool = False) -> Dict[str, Any]:
        """Get configuration for a specific tool."""
        if not refresh and tool_name in self._cache:
            return self._cache[tool_name]
            
        config_path = config.config_dir / f"{tool_name}.yaml"
        if not config_path.exists():
            self._cache[tool_name] = {}
            return {}
            
        try:
            with open(config_path) as f:
                tool_config = yaml.safe_load(f) or {}
            self._cache[tool_name] = tool_config
            return tool_config
        except Exception as e:
            logger.error(f"Error loading config for {tool_name}: {str(e)}")
            self._cache[tool_name] = {}
            return {}
    
    def get_value(self, tool_name: str, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value for a tool.
        
        Args:
            tool_name: Name of the tool
            key: Configuration key to get
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        config = self.get_tool_config(tool_name)
        return config.get(key, default)

    def clear_cache(self):
        """Clear the configuration cache."""
        self._cache.clear()

# Global config manager instance
config_manager = ConfigManager() 