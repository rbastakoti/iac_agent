# IaC Agent - Local Infrastructure as Code Workspace

A local-first, Jupyter-style intelligent workspace for Infrastructure as Code (IaC) with conversational AI agent, real-time visualization, and state persistence.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend development only)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd iac_agent
   ```

2. **Install Python dependencies**
   ```bash
   pip install -e .
   ```

3. **Configure LLM provider**
   ```bash
   # For OpenAI
   iac-agent configure --provider openai --api-key sk-your-api-key
   
   # For Anthropic Claude
   iac-agent configure --provider anthropic --api-key your-api-key
   
   # For Azure OpenAI
   iac-agent configure --provider openai --api-key your-key --model gpt-4
   ```

4. **Start the server**
   ```bash
   iac-agent serve
   ```

5. **Open your browser**
   Navigate to `http://localhost:8080`

## Usage

### Basic Commands

```bash
# Check system status
iac-agent status

# Check/install binary dependencies
iac-agent binaries --install

# Start server with custom port
iac-agent serve --port 8080 --host 0.0.0.0

# Enable development mode with auto-reload
iac-agent serve --reload

```

## Project Structure

```
iac_agent/
├── src/iac_agent/
│   ├── core/                 # Core configuration and settings
│   ├── api/                  # FastAPI routes and WebSocket handling
│   ├── agents/               # Agent session management and LangGraph
│   ├── providers/            # LLM manager
│   ├── infrastructure/       # binary manager/ terminal manager
|   ├── mcp                   # currently Fast MCP based File server and client
│   ├── database/             # SQLite persistence and state management
│   ├── security/             # Credential scrubbing and encryption
│   ├── static/web/           # React frontend application
│   └── cli.py                # Command line interface
├── frontend/                 # Frontend development (optional)
├── tests/                    # Test suite
├── workspace/                # Default Terraform workspace
├── bin/                      # Auto-installed binaries
└── pyproject.toml            # Python project configuration
```

**🎯 Built for Infrastructure Engineers who want to combine the power of AI with the precision of Infrastructure as Code.**
