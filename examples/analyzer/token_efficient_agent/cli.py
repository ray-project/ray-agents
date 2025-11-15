"""Interactive CLI for Token-Efficient Agent

Provides a terminal-based interface for chatting with the data analysis agent.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import ray
from dotenv import load_dotenv

logging.getLogger("ray.serve").setLevel(logging.ERROR)
logging.getLogger("ray").setLevel(logging.ERROR)

env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment from {env_path}")

from agent import TokenEfficientAgent  # noqa: E402


def print_header():
    """Print CLI header."""
    print("\n" + "=" * 70)
    print("  Token-Efficient Data Analysis Agent")
    print("=" * 70)
    print("\nCommands:")
    print("  /exit - Quit the CLI")
    print("  /clear - Clear conversation history")
    print("  /help - Show this help")
    print("\nType your message and press Enter to chat with the agent.")
    print("=" * 70 + "\n")


def main():
    """Main CLI loop."""
    parser = argparse.ArgumentParser(description="Token-Efficient Agent CLI")
    parser.add_argument(
        "--image",
        type=str,
        help="Pre-built Docker image name (e.g., 'token-efficient-agent'). If not provided, will build from Dockerfile.",
    )
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found")
        print("Please set it in the .env file at the project root")
        sys.exit(1)

    examples_dir = Path(__file__).parent.parent
    datasets_path = examples_dir / "datasets"
    servers_path = examples_dir / "servers"
    dockerfile_path = Path(__file__).parent / "Dockerfile"

    if not datasets_path.exists():
        print(f"Error: Datasets directory not found at {datasets_path}")
        sys.exit(1)
    if not servers_path.exists():
        print(f"Error: Servers directory not found at {servers_path}")
        sys.exit(1)

    # Must be added before Ray initialization
    sys.path.insert(0, str(examples_dir))

    print("Initializing Ray...")
    import warnings

    warnings.filterwarnings("ignore")

    ray.init(
        ignore_reinit_error=True,
        include_dashboard=False,
        runtime_env={"working_dir": str(examples_dir)},
        logging_level="ERROR",  # Suppress INFO logs
        log_to_driver=False,  # Don't send worker logs to driver
    )
    print("Ray initialized!\n")

    print("Starting MCP Datasets Server...")
    from mcp_serve import start_mcp_server

    # Start MCP datasets server on host
    start_mcp_server(str(datasets_path), port=8265)
    print()

    print("Creating agent...")
    agent = TokenEfficientAgent(
        session_id="cli-session",
        datasets_path=str(datasets_path),
        servers_path=str(servers_path),
        dockerfile_path=str(dockerfile_path) if dockerfile_path.exists() else None,
        image=args.image,
    )
    print("Agent ready!\n")

    print_header()

    try:
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            if user_input == "/exit":
                print("\nGoodbye!")
                break
            elif user_input == "/clear":
                agent.clear_history()
                print("\n[Conversation history cleared]")
                continue
            elif user_input == "/help":
                print_header()
                continue

            print("\nAgent: ", end="", flush=True)
            try:
                chunk_count = 0
                for chunk in agent.chat(user_input):
                    print(chunk, end="", flush=True)
                    chunk_count += 1
                if chunk_count == 0:
                    print("[No response received]")
                print()  # New line after response
            except KeyboardInterrupt:
                print("\n\n[Interrupted]")
                continue
            except Exception as e:
                print(f"\n\nError: {e}")
                import traceback

                traceback.print_exc()
                continue

    except KeyboardInterrupt:
        print("\n\nGoodbye!")

    finally:
        print("\nShutting down...")
        ray.shutdown()


if __name__ == "__main__":
    main()
