"""Token-Efficient Agent with Autonomous Code Execution

This agent autonomously explores and executes Python code to analyze datasets.
It uses OpenAI's function calling to execute code as a discoverable tool.
"""

import json
import os

# Import Ray code interpreter from main package
# This file is in: examples/analyzer/token_efficient_agent/
# We need to import from: src/ray_agents/
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

import ray
from openai import OpenAI

project_root = Path(__file__).parent.parent.parent.parent
src_path = project_root / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from ray_agents.code_interpreter import execute_code as ray_execute_code  # noqa: E402


class TokenEfficientAgent:
    """Agent that autonomously executes code for data analysis."""

    EXECUTE_CODE_TOOL = {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Execute Python code in a sandboxed environment. Variables persist across executions within the same session. Use this to explore MCP tools, access datasets, and perform analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute. Always print() results you want to see.",
                    }
                },
                "required": ["code"],
            },
        },
    }

    def __init__(
        self,
        session_id: str,
        datasets_path: str,
        servers_path: str,
        dockerfile_path: str | None = None,
        image: str | None = None,
        model: str = "gpt-4o",
        max_iterations: int = 15,
    ):
        """Initialize the token-efficient agent.

        Args:
            session_id: Unique identifier for this analysis session
            datasets_path: Path to datasets directory on host
            servers_path: Path to MCP servers directory on host
            dockerfile_path: Optional path to custom Dockerfile (will build image)
            image: Optional pre-built Docker image name (e.g., 'token-efficient-agent')
            model: OpenAI model to use
            max_iterations: Maximum number of tool calls per user message
        """
        self.session_id = session_id
        self.client = OpenAI()
        self.model = model
        self.max_iterations = max_iterations

        # Setup volume mounts (only servers - datasets accessed via MCP)
        self.datasets_path = str(Path(datasets_path).resolve())
        self.servers_path = str(Path(servers_path).resolve())
        self.volumes = {
            self.servers_path: {"bind": "/mnt/servers", "mode": "ro"},
        }

        self.image = image
        self.dockerfile = None
        if not image and dockerfile_path and os.path.exists(dockerfile_path):
            with open(dockerfile_path) as f:
                self.dockerfile = f.read()

        self.conversation_history: list[dict[str, Any]] = []

        self.system_prompt = """You are a data analysis assistant that autonomously explores and analyzes data.

Environment:
- Sandboxed container with Python, pandas, numpy, matplotlib
- /mnt/servers/ contains MCP tool modules you can import and use
- Variables and imports persist across executions
- Headless (no GUI) - always print() results you want to see

Key points:
- Datasets are NOT in the container filesystem
- Explore /mnt/servers/ to discover available MCP tools
- To import MCP modules: sys.path.append('/mnt') then import servers.MODULE_NAME
- MCP tools are async functions - you MUST use asyncio.run() to call them
  Example: result = asyncio.run(some_async_function())

Important reminders:
- Once you import a module or define a variable, it persists - don't re-import unnecessarily
- Always check the type/structure of returned data before using it (e.g., print type or keys)
- If you get a NameError, the module wasn't imported in the current or previous execution

Start by exploring what tools are available, then figure out how to access and analyze data."""

    def chat(self, user_message: str) -> Generator[str, None, None]:
        """Chat with the agent - it will autonomously explore and execute code.

        Args:
            user_message: The user's question

        Yields:
            Status messages and final response
        """
        self.conversation_history.append({"role": "user", "content": user_message})

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        *self.conversation_history,
                    ],
                    tools=[self.EXECUTE_CODE_TOOL],
                    tool_choice="auto",
                    temperature=0,
                )
            except Exception as e:
                yield f"\n[Error calling OpenAI: {e}]\n"
                return

            message = response.choices[0].message

            self.conversation_history.append(message.model_dump(exclude_unset=True))

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "execute_code":
                        args = json.loads(tool_call.function.arguments)
                        code = args.get("code", "")

                        yield f"\n[Executing code]\n```python\n{code}\n```\n"

                        result = self._execute_code(code)
                        if (
                            result["status"] == "success"
                            and result.get("exit_code", 0) == 0
                        ):
                            output = result.get("stdout", "").strip()
                            if output:
                                yield f"Output:\n{output}\n"
                            else:
                                yield "[No output - did you forget to print()?]\n"
                        else:
                            error = result.get("stderr") or result.get(
                                "error", "Unknown error"
                            )
                            yield f"[Error]\n{error}\n"

                        # Add tool result to history (simplified for better learning)
                        if (
                            result["status"] == "success"
                            and result.get("exit_code", 0) == 0
                        ):
                            output = result.get("stdout", "").strip()
                            if output:
                                result_content = f"SUCCESS\nOutput:\n{output}"
                            else:
                                result_content = (
                                    "No output. You must use print() to see results."
                                )
                        else:
                            error = result.get("stderr") or result.get(
                                "error", "Unknown error"
                            )
                            result_content = f"ERROR\n{error}"

                        tool_result = {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_content,
                        }
                        self.conversation_history.append(tool_result)
            else:
                if message.content:
                    yield f"\n{message.content}\n"
                break

        if iteration >= self.max_iterations:
            yield f"\n[Reached maximum iterations ({self.max_iterations})]\n"

    def _execute_code(self, code: str) -> dict[str, Any]:
        """Execute code using Ray.

        Args:
            code: Python code to execute

        Returns:
            Execution result dictionary
        """
        try:
            kwargs = {
                "code": code,
                "session_id": self.session_id,
                "volumes": self.volumes,
                "timeout": 300,
            }

            if self.image:
                kwargs["image"] = self.image
            elif self.dockerfile:
                kwargs["dockerfile"] = self.dockerfile

            result = ray.get(ray_execute_code.remote(**kwargs))
            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "exit_code": 1,
            }

    def clear_history(self):
        """Clear conversation history (session variables persist in sandbox)."""
        self.conversation_history = []
