"""Import dataset tool wrapper for datasets MCP server."""

from typing import Any

from ..mcp_client import call_mcp_tool


async def import_dataset(name: str) -> dict[str, Any]:
    """Import a dataset by name.

    Args:
        name: Name of the dataset file (e.g., 'car_prices.csv')

    Returns:
        Dictionary containing:
        - content: File contents as string
        - name: Dataset name
        - error: Error message (if failed)

    Example:
        >>> result = await import_dataset("car_prices.csv")
        >>> if "content" in result:
        ...     print(f"Loaded {result['name']}: {len(result['content'])} bytes")
    """
    return await call_mcp_tool("datasets", "import_dataset", {"name": name})
