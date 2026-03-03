# OpenAgentSearch

OpenAgentSearch is an open, self-hosted agentic web search service.

This repository currently implements milestone **M1**:
- monorepo bootstrap (`apps/api`, `apps/mcp`, `infra`)
- Docker stack (`searxng`, `redis`, `api`)
- optional browser service via Compose profile
- smoke tests for stack wiring

## Prerequisites

- Docker Desktop (with `docker compose`)
- Python 3.11+ (for local tests)
- `uv` (Python package manager)

## Start the default stack

```bash
docker compose up -d --build
```

Services:
- API: `http://localhost:8000/health`
- SearXNG: `http://localhost:8080/search?format=json&q=agent`

## Start with optional browser service

```bash
docker compose --profile browser up -d --build
```

## Run tests

Install/sync Python environments with `uv`:

```bash
uv sync --project apps/api
uv sync --project apps/mcp
```

Run basic M1 tests:

```bash
uv run python -m unittest discover -s tests -v
```

Run Docker integration smoke test (starts/stops containers):

```bash
set OAS_RUN_DOCKER_TESTS=1
uv run python -m unittest tests.test_m1_stack_integration -v
```

## Current milestone status

- M1 done
- `/v1/search`, `/v1/extract`, and MCP tools are planned for later milestones
