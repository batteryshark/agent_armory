# Agent Construct

<p align="center">
  <img src="artwork/logo.png" alt="Logo" width="300"/>
</p>

> "We can load anything, from clothing to equipment, weapons, training simulations, anything we need." - The Matrix (1999)

Agent Construct is a Model Context Protocol (MCP) server implementation that standardizes how AI applications access tools and context. Just as the Construct in The Matrix provided operators with instant access to any equipment they needed, Agent Construct provides a standardized interface for AI models to access tools and data through the MCP specification.

Built on the [Model Context Protocol](https://modelcontextprotocol.io/introduction) specification, it acts as a central hub that manages tool discovery, execution, and context management for AI applications. It provides a robust and scalable way to expose capabilities to AI models through a standardized protocol. It also provides a simplified configuration and tool structure to make adding new capabilities a breeze! An example tool for searching the web with Gemini is included.

## Core Features

### MCP Protocol Implementation
- **Full MCP Compliance**: Complete implementation of the Model Context Protocol specification
- **Tool Discovery**: Dynamic tool registration and discovery mechanism
- **Standardized Communication**: Implements MCP's communication patterns for tool interaction

### Server Architecture
- **FastAPI Backend**: High-performance asynchronous server implementation
- **Event Streaming**: Real-time updates via Server-Sent Events (SSE)
- **Modular Design**: Clean separation between core protocol handling and tool implementations
- **Handler System**: Extensible request handler architecture for different MCP operations
- **Tool-Based Rate Limiting**: Let the server handle your configurable per-tool rate limiting.

### Development Features
- **Tool Decorator System**: Simple way to expose new tools via MCP
- **Logging & Monitoring**: Comprehensive logging system for debugging and monitoring
- **Configuration Management**: Environment-based configuration with secure defaults
- **Testing Framework**: Extensive test suite for protocol compliance
- **Agent Framework Friendly**: Included implementation examples for custom clients or frameworks like smolagents.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/agent-construct.git
   cd agent-construct
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory with the following variables:
   ```
   # Server Configuration
   SERVER_HOST=localhost
   SERVER_PORT=8000
   
   # MCP Protocol Settings
   MCP_VERSION=1.0
   TOOL_DISCOVERY_ENABLED=true
   
   # Security Settings
   ENABLE_AUTH=false  # Enable for production
   ```

4. Run the server:
   ```bash
   python -m mcp_server
   ```

## Core Architecture

```
mcp_server/
├── core/               # Core MCP protocol implementation
│   ├── server.py      # Main server implementation
│   ├── protocol.py    # MCP protocol handlers
│   └── context.py     # Context management
├── handlers/          # MCP operation handlers
│   ├── discovery.py   # Tool discovery
│   ├── execution.py   # Tool execution
│   └── context.py     # Context operations
├── utils/            # Utility functions
│   ├── logging.py    # Logging configuration
│   ├── security.py   # Security utilities
│   └── config.py     # Configuration management
└── __main__.py       # Server entry point
```

## MCP Protocol Features

### Tool Discovery
- Dynamic tool registration system
- Tool capability advertisement
- Version management
- Tool metadata and documentation

### Context Management
- Efficient context storage and retrieval
- Context scoping and isolation
- Real-time context updates
- Context persistence options

### Communication Patterns
- Synchronous request/response
- Server-sent events for updates
- Streaming responses
- Error handling and recovery

## Future Enhancements

### Protocol Extensions
- [ ] Advanced context management features
- [ ] Custom protocol extensions
- [ ] Plugin system for protocol handlers

### Security
- [ ] Authentication and authorization
- [ ] Tool access control
- [-] Rate limiting and quota management
- [ ] Audit logging
- [ ] End-to-end encryption

### Performance
- [ ] Tool execution optimization
- [ ] Context caching
- [ ] Load balancing
- [ ] Request queuing
- [ ] Resource management

### Development
- [ ] Interactive protocol explorer
- [ ] Tool development SDK
- [ ] Protocol compliance testing tools
- [ ] Performance monitoring dashboard

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Model Context Protocol](https://modelcontextprotocol.io/) for the protocol specification
- FastAPI for the excellent web framework
- The open-source community for various tools and libraries used in this project 