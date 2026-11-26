# LendUp Evidence and Incident Service

Python 3.12 / FastAPI microservice for evidence management, incident resolution and assisted image analysis.

## Status

Initial scaffold only. The health endpoint and its test are included. Business endpoints, independent persistence, authentication, Cloudinary, Gemini, RabbitMQ and inter-service contracts are not yet implemented.

## Local development

```bash
python -m venv .venv
# Activate the virtual environment for your operating system.
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs or http://localhost:8000/health.

Run tests with `python -m pytest -q`.

## Configuration

Copy .env.example to .env before configuring integrations or running `docker compose up --build`. Never commit credentials. Select an available Gemini model for the project's quota.

## Architecture

- domain: entities, repository contracts, domain events
- application: use cases and services
- infrastructure: persistence, external adapters, messaging and HTTP clients
- interfaces: REST API
- shared: configuration

Keep the monolith REST contracts when migrating. Evidence owns its data; other contexts must be accessed through agreed service contracts or events. AI analysis only supports human decisions and must not automatically resolve incidents or affect guarantees.

GitFlow: main, develop, feature branches.
