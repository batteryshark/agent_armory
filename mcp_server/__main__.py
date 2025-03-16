"""
MCP Tool Server entry point.
"""
from mcp_server.core.server import MCPToolServer
from mcp_server.utils.logging_config import configure_logging

def main():
    """Run the MCP Tool Server."""
    # Configure logging first
    configure_logging()
    
    # Initialize and run server
    server = MCPToolServer()
    server.run()

if __name__ == "__main__":
    main() 