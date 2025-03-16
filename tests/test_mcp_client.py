"""
Test client for the Web Search MCP server.
"""
import asyncio
import json
import os
import traceback
from mcp import ClientSession, types
from mcp.client.sse import sse_client
from urllib.parse import urljoin

def tool_to_dict(tool):
    """Convert MCP tool object to a dictionary."""
    return {
        "name": tool.name,
        "description": tool.description,
        "inputSchema": tool.inputSchema
    }

async def test_web_search():
    """
    Test web search tools by connecting to an existing MCP server using SSE transport.
    """
    # Get connection details from environment or use defaults
    base_url = os.getenv("MCP_SERVER_URL", "http://localhost:32823")
    sse_url = urljoin(base_url, "/sse")  # Connect to the SSE endpoint
    print(f"\nConnecting to MCP server at {sse_url}...")

    try:
        async with sse_client(sse_url) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()

                # List available tools
                tools = await session.list_tools()
                print("\nAvailable tools:")
                # Convert tools to dictionary for JSON serialization
                tools_dict = [tool_to_dict(tool) for tool in tools.tools]
                print(json.dumps(tools_dict, indent=2))

                # Test queries
                test_queries = [
                    "What is the latest version of Python?",
                    "Who won the most recent Super Bowl?",
                    "What are the key features of the Rust programming language?"
                ]

                for query in test_queries:
                    print(f"\nTesting query: {query}")
                    print("-" * 50)

                    # Test web search
                    print("\nWeb Search Results:")
                    print("-" * 25)
                    try:
                        result = await session.call_tool(
                            "gemini_web_search",  # Use the actual tool name from the loaded tools
                            arguments={"query": query}
                        )
                        print("Result:")
                        # Extract text content from the first result
                        if result.content and len(result.content) > 0:
                            text_content = result.content[0].text
                            result_json = json.loads(text_content)
                            print(json.dumps(result_json, indent=2))
                        else:
                            print("No content returned")
                    except Exception as e:
                        print(f"Error during tool call: {e}")
                        traceback.print_exc()

    except ConnectionRefusedError:
        print(f"Error: Could not connect to MCP server at {sse_url}")
        print("Make sure the server is running and the connection details are correct.")
    except Exception as e:
        print(f"Error during connection: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()

async def main():
    try:
        await test_web_search()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())