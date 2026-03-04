# 🤖 IaC Agent - Local Infrastructure as Code Workspace

A local-first, Jupyter-style intelligent workspace for Infrastructure as Code (IaC) with conversational AI agent, real-time visualization, and state persistence.

## 🌟 Features

- **📱 Split-Pane Interface**: Terminal-style chat on the left, infrastructure graph on the right
- **🧠 Multi-LLM Support**: OpenAI, Anthropic Claude, Google Gemini, Ollama, and Azure OpenAI
- **🎯 Terraform Integration**: Direct integration with Terraform CLI for plan/apply operations
- **☁️ Azure Discovery**: Import existing Azure resources using aztfexport
- **💾 State Persistence**: Resumable agent conversations with SQLite checkpointing
- **🔐 Local-First Security**: Credential scrubbing before sending to LLMs
- **📊 Visual Infrastructure**: Real-time graph visualization with ghost nodes for proposed changes
- **⚡ Real-time Sync**: WebSocket communication between terminal and graph

## 🚀 Quick Start

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

3. **Initialize workspace**
   ```bash
   iac-agent init
   ```

4. **Configure LLM provider**
   ```bash
   # For OpenAI
   iac-agent configure --provider openai --api-key sk-your-api-key
   
   # For Anthropic Claude
   iac-agent configure --provider anthropic --api-key your-api-key
   
   # For Azure OpenAI
   iac-agent configure --provider openai --api-key your-key --model gpt-4
   ```

5. **Start the server**
   ```bash
   iac-agent serve
   ```

6. **Open your browser**
   Navigate to `http://localhost:8080`

## 🛠️ Usage

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

### Web Interface

1. **Chat Interface**: Use natural language to describe your infrastructure needs
   - "Create a new Azure resource group in East US"
   - "Import my existing production resource group"  
   - "Add a storage account with blob containers"
   - "Show me the current terraform plan"

2. **Graph Visualization**: 
   - **Solid nodes**: Existing infrastructure
   - **Dashed nodes**: Proposed changes (ghost nodes)
   - **Colors**: Green (add), Yellow (modify), Red (delete)

3. **Human-in-the-Loop**: The agent always asks for confirmation before destructive operations

### Example Workflows

#### 1. Import Existing Azure Resources
```
User: "Import my production resource group 'rg-prod-eastus'"
Agent: "I'll use aztfexport to reverse-engineer your Azure resources. This will:"
       "1. Connect to Azure CLI"
       "2. Export terraform configuration"
       "3. Import state file"
       "4. Update the visualization"
       "Proceed? (yes/no)"
```

#### 2. Plan Infrastructure Changes
```
User: "Add a new storage account for backups"
Agent: "I'll create a storage account configuration. Here's what I propose:"
       [Shows ghost node in graph]
       "Shall I run terraform plan to see the exact changes?"
```

#### 3. Apply Changes
```
User: "Apply the changes"
Agent: "Running terraform plan first..."
       "This will create 1 resource:"
       "• azurerm_storage_account.backup (cost: ~$5/month)"
       "Type 'proceed' to apply these changes."
```

## 📁 Project Structure

```
iac_agent/
├── src/iac_agent/
│   ├── core/                 # Core configuration and settings
│   ├── api/                  # FastAPI routes and WebSocket handling
│   ├── agents/               # Agent session management and LangGraph
│   ├── providers/            # LLM provider abstraction layer
│   ├── infrastructure/       # Terraform integration and binary management
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

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# LLM Provider API Keys
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/

# Application Settings
DEBUG=false
HOST=127.0.0.1
PORT=8080

# Database
DATABASE__URL=sqlite:///./workspace.db

# Security
SECURITY__SECRET_KEY=your-secret-key-here

# Infrastructure
INFRASTRUCTURE__WORKSPACE_DIRECTORY=./workspace
INFRASTRUCTURE__MAX_RESOURCES=100
```

### Provider Configuration

The application automatically detects and configures available providers:

- **OpenAI**: Requires `OPENAI_API_KEY`
- **Anthropic**: Requires `ANTHROPIC_API_KEY` 
- **Azure OpenAI**: Requires `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT`
- **Ollama**: Runs locally, no API key needed
- **Google Gemini**: Requires `GOOGLE_API_KEY`

## 🐳 Development

### Running in Development Mode

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run with auto-reload
iac-agent serve --reload --debug

# Run tests
pytest

# Format code
black src/
ruff check src/
```

### Frontend Development

The MVP includes a self-contained React app that loads via CDN. For advanced frontend development:

```bash
cd frontend/
npm install
npm run dev
```

## 📊 Architecture Overview

### Technology Stack

- **Backend**: FastAPI + Python 3.11+
- **Frontend**: React + TailwindCSS + SVG-based graph visualization
- **Database**: SQLite + SQLAlchemy
- **Agent Framework**: LangGraph for state persistence
- **Infrastructure**: Terraform CLI integration
- **Communication**: WebSockets for real-time sync
- **Security**: Local credential scrubbing and encryption

### Key Components

1. **LLM Orchestration**: Multi-provider abstraction supporting OpenAI, Anthropic, Google, Ollama
2. **State Persistence**: LangGraph-based agent memory with SQLite checkpointing
3. **Binary Management**: Auto-installation of terraform, az, aztfexport
4. **Infrastructure Integration**: Safe terraform execution with human-in-the-loop
5. **Real-time Visualization**: WebSocket-synced graph updates

## 🔒 Security

- **Local-First**: No sensitive infrastructure data sent to external services
- **Credential Scrubbing**: Automatic detection and redaction of secrets
- **Subprocess Isolation**: Safe execution of terraform commands
- **Encrypted Storage**: Local encryption of API keys and sensitive data

## 🚧 Limitations (MVP)

- **Scale**: Optimized for infrastructure with <100 resources
- **Providers**: Limited Azure support (AWS/GCP planned)
- **Offline Mode**: View/edit only (LLM requires internet)
- **Collaboration**: Single-user workspace only
- **Graph Layout**: Basic SVG rendering (React Flow integration planned)

## 📚 API Reference

### WebSocket Messages

```typescript
// Start session
{
  "type": "start_session",
  "payload": {"session_id": "optional-id"}
}

// Chat message
{
  "type": "chat_message", 
  "payload": {"content": "Your message"},
  "session_id": "session-uuid"
}

// Terraform command
{
  "type": "terraform_command",
  "payload": {"command": "plan", "args": []},
  "session_id": "session-uuid"
}
```

### HTTP Endpoints

```bash
GET    /api/health                 # Health check
GET    /api/settings               # Get configuration
POST   /api/settings/provider      # Update LLM provider
GET    /api/workspace              # Get workspace info
POST   /api/workspace/upload       # Upload terraform files
GET    /api/graph/data             # Get infrastructure graph
POST   /api/terraform/plan         # Run terraform plan
POST   /api/terraform/apply        # Run terraform apply
POST   /api/azure/import           # Import Azure resources
GET    /api/binaries/status        # Check binary status
POST   /api/binaries/install       # Install binaries
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙋 Support

- **Issues**: [GitHub Issues](issue-url)
- **Discussions**: [GitHub Discussions](discussion-url) 
- **Documentation**: [Wiki](wiki-url)

---

**🎯 Built for Infrastructure Engineers who want to combine the power of AI with the precision of Infrastructure as Code.**