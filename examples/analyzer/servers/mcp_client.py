"""MCP Client for communicating with MCP servers.

This module provides a client for interacting with MCP servers.
Supports both stdio (subprocess) and HTTP transports.
"""

import json
import subprocess
import urllib.error
import urllib.request
from typing import Any


class MCPClient:
    """Client for communicating with MCP servers via stdio."""

    def __init__(
        self,
        server_command: list[str] | None = None,
        cwd: str | None = None,
        http_endpoint: str | None = None,
    ):
        """Initialize MCP client.

        Args:
            server_command: Command to start the MCP server (stdio mode)
            cwd: Working directory for the server process (stdio mode)
            http_endpoint: HTTP endpoint for MCP server (HTTP mode)
        """
        self.server_command = server_command
        self.cwd = cwd
        self.http_endpoint = http_endpoint
        self._process: subprocess.Popen | None = None

        if not server_command and not http_endpoint:
            raise ValueError("Must provide either server_command or http_endpoint")

    def start(self) -> None:
        """Start the MCP server process."""
        if self._process is None:
            self._process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,  # Unbuffered
                cwd=self.cwd,
            )
            import time

            time.sleep(0.5)  # Allow server startup

    def stop(self) -> None:
        """Stop the MCP server process."""
        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool

        Returns:
            Result from the tool execution

        Raises:
            RuntimeError: If communication fails
        """
        if self.http_endpoint:
            return self._call_tool_http(tool_name, arguments)
        else:
            return self._call_tool_stdio(tool_name, arguments)

    def _call_tool_http(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call tool via HTTP."""
        request_data = {
            "tool": tool_name,
            "arguments": arguments,
        }

        try:
            data = json.dumps(request_data).encode("utf-8")
            req = urllib.request.Request(
                f"{self.http_endpoint}/tools/call",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise RuntimeError(f"HTTP error {e.code}: {error_body}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to call MCP tool via HTTP: {str(e)}") from e

    def _call_tool_stdio(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call tool via stdio."""
        if not self._process:
            raise RuntimeError("MCP server not started. Call start() first.")

        request = {
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        try:
            request_json = json.dumps(request) + "\n"
            self._process.stdin.write(request_json)
            self._process.stdin.flush()

            response_line = self._process.stdout.readline()
            if not response_line:
                raise RuntimeError("No response from MCP server")

            response = json.loads(response_line.strip())

            if "error" in response:
                raise RuntimeError(f"MCP server error: {response['error']}")

            return response.get("result", {})

        except Exception as e:
            raise RuntimeError(f"Failed to call MCP tool: {str(e)}") from e

    def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server.

        Returns:
            List of tool definitions
        """
        if not self._process:
            raise RuntimeError("MCP server not started. Call start() first.")

        request = {"method": "tools/list", "params": {}}

        try:
            request_json = json.dumps(request) + "\n"
            self._process.stdin.write(request_json)
            self._process.stdin.flush()

            response_line = self._process.stdout.readline()
            if not response_line:
                raise RuntimeError("No response from MCP server")

            response = json.loads(response_line.strip())

            if "error" in response:
                raise RuntimeError(f"MCP server error: {response['error']}")

            return response.get("result", {}).get("tools", [])

        except Exception as e:
            raise RuntimeError(f"Failed to list MCP tools: {str(e)}") from e

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


_datasets_client: MCPClient | None = None


def get_datasets_client(http_endpoint: str | None = None) -> MCPClient:
    """Get or create the datasets MCP client.

    Args:
        http_endpoint: HTTP endpoint for MCP server (e.g., 'http://localhost:8265/mcp')
                      If None, will try to detect Ray Serve endpoint

    Returns:
        MCPClient instance for the datasets server
    """
    global _datasets_client
    if _datasets_client is None:
        if http_endpoint is None:
            import os

            in_docker = os.path.exists("/.dockerenv")

            if not in_docker and os.path.exists("/proc/1/cgroup"):
                try:
                    with open("/proc/1/cgroup") as f:
                        in_docker = "docker" in f.read()
                except Exception:
                    pass

            if in_docker:
                http_endpoint = "http://host.docker.internal:8265/mcp"
            else:
                http_endpoint = "http://localhost:8265/mcp"

        _datasets_client = MCPClient(http_endpoint=http_endpoint)

    return _datasets_client


async def call_mcp_tool(
    server: str, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Call an MCP tool on the specified server.

    This is the central function that all tool wrappers use to communicate
    with MCP servers.

    Args:
        server: Name of the MCP server (e.g., 'datasets')
        tool_name: Name of the tool to call
        arguments: Arguments for the tool

    Returns:
        Result from the tool execution
    """
    if server == "datasets":
        client = get_datasets_client()
        return client.call_tool(tool_name, arguments)
    else:
        raise ValueError(f"Unknown MCP server: {server}")
