"""Base classes for Ray Agents framework."""

from abc import ABC, abstractmethod
from typing import Any


class RayAgent(ABC):
    """Abstract base class for all Ray Agents.

    All agents must inherit from this class and implement the required methods.
    This ensures a consistent interface across all agents in the framework.
    """

    def __init__(self):  # noqa: B027
        """Initialize the agent.

        Subclasses should call super().__init__() and add their own initialization.
        """
        pass

    @abstractmethod
    def run(self, data: dict[str, Any]) -> dict[str, Any]:
        """Main entry point for agent execution.

        This method MUST be implemented by all agents.

        Args:
            data: Input data from the client request

        Returns:
            Dict containing the agent's response

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Agents must implement the run() method")

    def get_info(self) -> dict[str, Any]:
        """Get agent information and metadata.

        This method provides basic agent information. Can be overridden
        by subclasses to provide more detailed information.

        Returns:
            Dict containing agent name, version, and other metadata
        """
        return {
            "name": self.__class__.__name__,
            "version": "1.0.0",
            "framework": "ray-agents",
        }

    def validate_input(self, data: dict[str, Any]) -> bool:
        """Validate input data before processing.

        Optional method that agents can override to add input validation.

        Args:
            data: Input data to validate

        Returns:
            True if data is valid, False otherwise
        """
        return isinstance(data, dict)

    def handle_error(self, error: Exception) -> dict[str, Any]:
        """Handle errors that occur during agent execution.

        Optional method that agents can override for custom error handling.

        Args:
            error: The exception that occurred

        Returns:
            Dict containing error information
        """
        return {
            "error": str(error),
            "type": error.__class__.__name__,
            "agent": self.__class__.__name__,
        }
