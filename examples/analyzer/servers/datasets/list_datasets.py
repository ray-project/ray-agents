"""List datasets tool wrapper for datasets MCP server."""

from typing import Any

from ..mcp_client import call_mcp_tool


async def list_datasets() -> dict[str, Any]:
    """List available datasets.

    Returns:
        Dictionary containing:
        - datasets: List of dataset names (filenames only, no paths)
        - error: Error message (if failed)

    Example:
        >>> result = await list_datasets()
        >>> if "datasets" in result:
        ...     for name in result["datasets"]:
        ...         print(name)
    """
    return await call_mcp_tool("datasets", "list_datasets", {})
