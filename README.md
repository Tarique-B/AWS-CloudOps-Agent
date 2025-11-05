# AWS AI Assistant

Powered by Strands Agent and AWS Bedrock.

## Overview

An AWS Assistant application with a FastAPI backend and Streamlit frontend. The agent can interact with AWS services through natural language queries.

## Architecture

- **agent.py**: FastAPI server with `/ping` and `/invocations` endpoints
- **app.py**: Streamlit chat interface
- **models.py**: Pydantic models for API schemas

## Quick Start

### Option 1: Run Both Services Separately (Recommended for Development)

**Terminal 1 - Start API Server:**
```bash
python agent.py
```
Or:
```bash
uvicorn agent:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Start Streamlit App:**
```bash
streamlit run app.py
```

### Option 2: Use Helper Script (Linux/Mac)

```bash
chmod +x run.sh
./run.sh
```

### Option 3: Use Helper Script (Windows)

```bash
run.bat
```

## Configuration

- **API_BASE_URL**: Set environment variable to change API endpoint (default: `http://localhost:8000`)
- **BEDROCK_MODEL_ID**: Set environment variable to change Bedrock model (default: `anthropic.claude-3-sonnet-20240229-v1:0`)

## API Endpoints

- `GET /ping` - Health check and status
- `POST /invocations` - Invoke agent with prompt (supports streaming)

## Requirements

See `requirements.txt` for all dependencies.

## AWS Credentials

Make sure AWS credentials are configured via:
- AWS CLI (`aws configure`)
- Environment variables
- IAM roles (if running on EC2)
