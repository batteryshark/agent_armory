"""
Logging configuration for the MCP server.
"""
import logging
from mcp_server.core.config import config

def configure_logging():
    """Configure logging based on server settings."""
    # Set up root logger
    root_logger = logging.getLogger()
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Set log level based on debug mode
    log_level = logging.DEBUG if config.debug_mode else logging.INFO
    root_logger.setLevel(log_level)
    console_handler.setLevel(log_level)
    
    # Remove any existing handlers to avoid duplicate logs
    root_logger.handlers.clear()
    
    # Add the console handler to the root logger
    root_logger.addHandler(console_handler)
    
    # Log initial configuration
    logging.info(f"Logging configured with level: {logging.getLevelName(log_level)}")
    if config.debug_mode:
        logging.debug("Debug logging enabled") 