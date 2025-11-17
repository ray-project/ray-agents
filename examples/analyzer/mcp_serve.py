"""Ray Serve deployment for MCP Datasets Server.

This runs the MCP datasets server as a Ray Serve deployment,
providing HTTP access to dataset operations.
"""

import os
from pathlib import Path
from typing import Any

import ray
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from ray import serve

app = FastAPI()


class DatasetsMCPServer:
    """MCP Datasets server that provides controlled access to datasets."""

    def __init__(self, datasets_directory: str):
        """Initialize with datasets directory.

        Args:
            datasets_directory: Path to the datasets directory
        """
        self.datasets_dir = Path(datasets_directory).resolve()

        if not self.datasets_dir.exists():
            raise ValueError(f"Datasets directory does not exist: {datasets_directory}")

    def list_datasets(self) -> dict[str, Any]:
        """List available datasets (names only, no paths).

        Returns:
            Dictionary with 'datasets' key containing list of dataset filenames
        """
        try:
            datasets = []
            for item in sorted(self.datasets_dir.iterdir()):
                if item.is_file():
                    datasets.append(item.name)

            return {"datasets": datasets}
        except Exception as e:
            return {"error": f"Error listing datasets: {str(e)}"}

    def import_dataset(self, name: str) -> dict[str, Any]:
        """Import a dataset by name.

        Args:
            name: Dataset filename (e.g., 'data.csv')

        Returns:
            Dictionary with 'content' and 'name' keys, or 'error' if failed
        """
        # Validate name to prevent path traversal
        if "/" in name or "\\" in name or name.startswith("."):
            return {"error": f"Invalid dataset name: {name}"}

        file_path = self.datasets_dir / name

        # Ensure the resolved path is still within datasets directory
        try:
            resolved = file_path.resolve()
            if not str(resolved).startswith(str(self.datasets_dir)):
                return {"error": f"Access denied: {name}"}
        except Exception:
            return {"error": f"Invalid dataset name: {name}"}

        if not file_path.exists():
            return {"error": f"Dataset not found: {name}"}

        if not file_path.is_file():
            return {"error": f"Not a file: {name}"}

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            return {"content": content, "name": name}
        except Exception as e:
            return {"error": f"Error reading dataset: {str(e)}"}

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool with the given arguments."""
        tools = {
            "list_datasets": self.list_datasets,
            "import_dataset": self.import_dataset,
        }

        if tool_name not in tools:
            return {"error": f"Unknown tool: {tool_name}"}

        handler = tools[tool_name]

        try:
            result = handler(**arguments)
            return result
        except TypeError as e:
            return {"error": f"Invalid arguments: {str(e)}"}
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}


@serve.deployment(num_replicas=1)
@serve.ingress(app)
class MCPServeDeployment:
    """Ray Serve deployment for MCP datasets server."""

    def __init__(self, datasets_directory: str):
        """Initialize the MCP server deployment.

        Args:
            datasets_directory: Path to the datasets directory
        """
        self.server = DatasetsMCPServer(datasets_directory)

    @app.post("/tools/call")
    async def call_tool(self, request: Request) -> JSONResponse:
        """Handle MCP tool calls via HTTP.

        Request format:
        {
            "tool": "read_file",
            "arguments": {"path": "/path/to/file"}
        }
        """
        try:
            body = await request.json()
            tool_name = body.get("tool")
            arguments = body.get("arguments", {})

            if not tool_name:
                raise HTTPException(status_code=400, detail="Missing 'tool' field")

            result = self.server.call_tool(tool_name, arguments)
            return JSONResponse(content=result)

        except Exception as e:
            return JSONResponse(
                status_code=500, content={"error": f"Server error: {str(e)}"}
            )

    @app.get("/health")
    async def health(self):
        """Health check endpoint."""
        return {"status": "healthy"}


def start_mcp_server(datasets_directory: str, port: int = 8265) -> Any | None:
    """Start the MCP datasets server as a Ray Serve deployment.

    Args:
        datasets_directory: Path to the datasets directory
        port: Port for Ray Serve (default: 8265)

    Returns:
        Deployment handle or None if already running
    """
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)

    try:
        from ray.serve._private.api import _get_global_client

        _get_global_client()

        try:
            existing_apps = serve.status().applications
            if "mcp-datasets" in existing_apps:
                print(
                    f"✓ MCP Datasets Server already running at http://localhost:{port}/mcp"
                )
                return None
        except Exception:
            pass

    except Exception:
        serve.start(detached=True, http_options={"host": "0.0.0.0", "port": port})

    deployment = MCPServeDeployment.bind(datasets_directory=datasets_directory)

    serve.run(
        deployment,
        name="mcp-datasets",
        route_prefix="/mcp",
    )

    print(f"✓ MCP Datasets Server running at http://localhost:{port}/mcp")
    print(f"  Datasets directory: {datasets_directory}")
    print(f"  Health check: http://localhost:{port}/mcp/health")

    return deployment


if __name__ == "__main__":
    examples_dir = Path(__file__).parent
    datasets_dir = os.getenv("DATASETS_DIR", str(examples_dir / "datasets"))
    port = int(os.getenv("MCP_PORT", "8000"))

    print(f"Starting MCP Datasets Server on port {port}...")
    start_mcp_server(datasets_dir, port=port)

    print("\nServer is running. Press Ctrl+C to stop.")
    try:
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        serve.shutdown()
