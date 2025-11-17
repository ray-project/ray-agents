# Token-Efficient Agent

Interactive CLI agent that generates and executes Python code for data analysis with 90%+ token efficiency.

## Quick Start

### Setup

```bash
# From project root
uv sync
source .venv/bin/activate
cd examples/analyzer/token_efficient_agent
```

### Option 1: Pre-build (recommended)

```bash
# 1. Pre-build the Docker image
./build.sh

# 2. Run the CLI with pre-built image
./run_cli.sh --image token-efficient-agent
```

This is fastest - image is ready before you start chatting.

### Option 2: Auto-build (slower first run)

```bash
# Run the CLI (builds Docker image automatically on first execution)
./run_cli.sh
```

Note: First run takes 3-5 minutes to build the Docker image.

**Important**: Use `./run_cli.sh` instead of `uv run cli.py` or `python cli.py` to avoid stdin buffering issues with interactive input.

## How It Works

### Architecture

```
CLI (Host) → Starts MCP server + manages Ray
    ↓
┌─────────────────────────────────────┐
│  Agent → Generates code             │
│    ↓                                │
│  Sandbox (gVisor) → Executes code   │
│    ├── /mnt/servers (MCP clients)   │
│    └── Persistent Python session    │
└──────────┬──────────────────────────┘
           │
      Unix socket (/tmp/mcp.sock)
           │
    MCP Sidecar Proxy (auto-started)
           │
    MCP Server (Ray Serve, :8265)
           │
    Datasets (../datasets/)
```

The CLI automatically:
1. Starts MCP server on port 8265
2. Creates sidecar proxy container when needed
3. Connects sandbox to datasets via MCP

### Token Efficiency

**Traditional**: Send 100KB CSV in every prompt = 150K tokens across 3 turns

**This approach**: Generate code that loads CSV once = 8K tokens across 3 turns

**Savings: 94%**

### Example Interaction

```
You: What datasets are available?

Agent: I'll check the datasets via MCP.

```python
import sys
sys.path.append('/mnt')
from servers.datasets_client import list_datasets

datasets = list_datasets()
print(datasets)
```

[Executing code...]
{'datasets': ['car_price_prediction_.csv']}

You: Load it and show summary stats

Agent: [Generates code that loads the dataset via MCP]

```python
from servers.datasets_client import import_dataset
from io import StringIO
import pandas as pd

result = import_dataset('car_price_prediction_.csv')
df = pd.read_csv(StringIO(result['content']))
print(df.describe())
```

[Variables persist across executions!]
```

## Features

- **Streaming responses** - See agent thinking in real-time
- **Session persistence** - Variables persist across turns
- **MCP integration** - Secure dataset access via proxy
- **Auto-managed sidecar** - Proxy container started automatically
- **Sandboxed** - Complete network isolation with gVisor
- **Token efficient** - Only summaries in context, not raw data

## Commands

- `/exit` - Quit
- `/clear` - Clear conversation history
- `/help` - Show help

## Files

- `agent.py` - Core agent with streaming and code execution
- `cli.py` - Interactive terminal interface (starts MCP server)
- `Dockerfile` - Container image with Python data analysis packages
- `../mcp_serve.py` - Ray Serve MCP server
- `../servers/` - MCP client libraries (mounted in sandbox)

## Requirements

- Docker with gVisor (required for security)
- OpenAI API key (in .env file at project root)
- Python packages: ray, openai, python-dotenv, docker

### gVisor Setup for MCP

To enable network-isolated sandboxes with MCP access, configure gVisor to allow Unix socket connections.

Add to `/etc/docker/daemon.json`:
```json
{
  "runtimes": {
    "runsc": {
      "path": "/var/lib/docker/volumes/runsc-bin/_data/runsc",
      "runtimeArgs": [
        "--host-uds=all"
      ]
    }
  }
}
```

Then restart Docker:
```bash
# macOS
killall Docker && open /Applications/Docker.app

# Linux
sudo systemctl restart docker
```

**Why this is needed:**
- `--host-uds=all`: Allows gVisor containers to connect to Unix sockets on the host
- Enables `network_mode: none` (complete isolation) + Unix socket communication with sidecar
- Sidecar enforces MCP allowlist while sandbox has zero network access

## Customization

### Add Python packages

Edit `Dockerfile`:
```dockerfile
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    your-package
```

Rebuild: `docker build -t token-efficient-agent .`

### Change model

Edit `cli.py`:
```python
agent = TokenEfficientAgent(..., model="gpt-4o-mini")
```

### Adjust timeout

Edit `agent.py`:
```python
execute_code.remote(..., timeout=120)  # 2 minutes
```
