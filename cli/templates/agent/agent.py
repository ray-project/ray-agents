"""Agent template for Ray Serve deployment."""

import ray
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ray import serve

load_dotenv()


class ProcessRequest(BaseModel):
    """Input data structure for HTTP requests to the agent."""

    data: dict
    session_id: str = "default"


class ProcessResponse(BaseModel):
    """Output data structure returned by the agent to HTTP clients."""

    result: dict
    session_id: str


class Agent:
    """Your agent's core logic."""

    def __init__(self):
        """Initialize your agent."""

        # Add your initialization code

        pass

    def process(self, data: dict, session_id: str = "default") -> dict:
        """Main entry point for your agent's functionality.

        This method contains your core business logic. Clients send requests
        to the /process HTTP endpoint, which calls this method with the data.
        Implement your agent's behavior here (chat, analysis, scraping, etc.).
        """

        # Replace with your agent's functionality

        return {
            "message": "Agent processed your request",
            "input_data": data,
            "session_id": session_id,
        }


# HTTP wrapper for Ray Serve deployment
app = FastAPI(title="Ray Agent", description="Agent deployed on Ray Serve")


@serve.deployment(num_replicas=1, ray_actor_options={"num_cpus": 1})
@serve.ingress(app)
class AgentDeployment:
    """Ray Serve deployment wrapper."""

    def __init__(self):
        """Initialize the deployment with agent instance."""
        self.agent = Agent()

    @app.post("/process", response_model=ProcessResponse)
    async def process_endpoint(self, request: ProcessRequest) -> ProcessResponse:
        """HTTP endpoint that receives client requests and forwards them to your agent.

        Clients make POST requests to /process with data, this endpoint validates
        the input, calls your agent's process() method, and returns the result
        as an HTTP response. This is the bridge between HTTP and your agent logic.
        """
        try:
            result = self.agent.process(request.data, request.session_id)
            return ProcessResponse(result=result, session_id=request.session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/health")
    async def health_check(self):
        """Health check endpoint."""
        return {"status": "healthy"}


def deploy_agent(port: int = 8000):
    """Deploy the agent on Ray Serve."""
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)

    serve.start(detached=True, http_options={"host": "0.0.0.0", "port": port})
    deployment = AgentDeployment.bind()
    serve.run(deployment, name="ray-agent", route_prefix="/")

    print(f"Agent deployed on http://localhost:{port}")
    print(f"Process: http://localhost:{port}/process")
    print(f"Health: http://localhost:{port}/health")
    print(f"Docs: http://localhost:{port}/docs")

    return deployment


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Deploy Agent on Ray Serve")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on")
    args = parser.parse_args()

    try:
        deploy_agent(args.port)
        print("Agent running. Press Ctrl+C to stop.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Shutting down...")
        serve.shutdown()
        ray.shutdown()
    except Exception as e:
        print(f"Error: {e}")
        serve.shutdown()
        ray.shutdown()
