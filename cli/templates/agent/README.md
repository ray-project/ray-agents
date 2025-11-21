# Ray Agent Template

A template for building and deploying agents with Ray Serve.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment:**
   ```bash
   # Edit .env file with your API keys and configuration
   ```

3. **Implement your agent:**
   ```python
   # Edit agent.py - modify the Agent class:
   # - Add initialization code in __init__()
   # - Implement your logic in process()
   ```

4. **Run your agent:**
   ```bash
   python agent.py
   ```

5. **Test your agent:**
   ```bash
   curl -X POST http://localhost:8000/process \
     -H "Content-Type: application/json" \
     -d '{"data": {"message": "hello"}, "session_id": "test"}'
   ```

## API Endpoints

- **POST /process** - Main agent endpoint
- **GET /health** - Health check
- **GET /docs** - Interactive API documentation

## Architecture

- **Agent class** - Your business logic (implement this)
- **AgentDeployment class** - Ray Serve wrapper (don't modify)
- **deploy_agent()** - Deployment function (don't modify)

## Customization

Focus on the `Agent` class in `agent.py`:

```python
class Agent:
    def __init__(self):
        # Add your initialization code here
        # - Load models
        # - Initialize clients
        # - Set up databases
    
    def process(self, data: dict, session_id: str = "default") -> dict:
        # Implement your agent logic here
        # - Process the input data
        # - Return results as a dictionary
```

## Examples

**Chat Agent:**
```python
def process(self, data: dict, session_id: str = "default") -> dict:
    message = data["message"]
    response = self.generate_response(message)
    return {"response": response}
```

**Code Review Agent:**
```python
def process(self, data: dict, session_id: str = "default") -> dict:
    code = data["code"]
    issues = self.analyze_code(code)
    return {"issues": issues, "score": 85}
```

**Web Scraper Agent:**
```python
def process(self, data: dict, session_id: str = "default") -> dict:
    url = data["url"]
    content = self.scrape_website(url)
    return {"content": content, "status": "success"}
```