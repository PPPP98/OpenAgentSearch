# OpenAgentSearch

OpenAgentSearch is a self-hosted web search API with MCP tools.

Korean documentation: [README.ko.md](README.ko.md)

## Why This Project Exists

I needed web search and page extraction for agent workflows, but did not want:
- black-box hosted services
- expensive per-call costs
- tightly coupled vendor-specific tooling

This project provides a transparent, self-hosted foundation that is easy to run, easy to integrate, and easy to control.

## Key Advantages

- Practical API split: fast web search and deep page extraction are exposed separately.
- Agent-ready MCP support: `openagentsearch.search` and `openagentsearch.extract` via FastMCP.
- Cost and latency control: Redis-backed caching for repeated queries and extraction.
- Safety by default: SSRF checks, domain policy controls, and per-domain rate limiting.
- Simple operations: one Docker Compose stack for local or small-team deployment.

It is built for users who want:
- A simple HTTP API for search and page extraction
- MCP tools that can be plugged into agent workflows
- Local control over caching, rate limits, and domain policy

## What You Can Do

- Search the web with `POST /v1/search`
- Extract clean markdown from a URL with `POST /v1/extract`
- Use MCP tools `openagentsearch.search` and `openagentsearch.extract`

## Quick Start

Requirements:
- Docker Desktop (with `docker compose`)
- Python 3.11+
- `uv` package manager

Start the stack:

```bash
docker compose up -d --build
```

Check services:
- API health: `http://localhost:8000/health`
- API metrics: `http://localhost:8000/internal/metrics`
- SearXNG sample query: `http://localhost:8080/search?format=json&q=agent`

Stop the stack:

```bash
docker compose down
```

Optional browser container:

```bash
docker compose --profile browser up -d --build
```

## First API Calls

### 1) Fast search only

```bash
curl -X POST "http://localhost:8000/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "open source search engine",
    "mode": "speed",
    "limit": 5
  }'
```

### 2) Search plus extraction of top results

```bash
curl -X POST "http://localhost:8000/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "llm agent memory architecture",
    "mode": "balanced",
    "limit": 5,
    "extract_top_n": 2,
    "max_extract_chars": 6000
  }'
```

### 3) Extract a single page

```bash
curl -X POST "http://localhost:8000/v1/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_chars": 20000
  }'
```

## API Reference

### `POST /v1/search`

Request fields:
- `query` (string, required)
- `mode` (`speed` or `balanced`, default `speed`)
- `limit` (1..50, default `10`)
- `page` (>=1, default `1`)
- `categories` (string[], optional)
- `engines` (string[], optional)
- `extract_top_n` (0..20, default `3`)
- `max_extract_chars` (1..200000, default `6000`)

Response fields:
- `query`, `mode`, `limit`, `page`
- `results[]` items include `url`, `title`, `snippet`, `source`, and `score`
- `extract` is present when extraction succeeds in balanced mode
- `extract_error` is present when extraction fails
- `cached` (whether this response came from cache)

### `POST /v1/extract`

Request fields:
- `url` (string, required)
- `max_chars` (1..200000, default `20000`)

Response fields:
- `url`
- `markdown`
- `passages[]`
- `title`
- `content_hash`
- `cached`

### Common error codes

- `400`: invalid input or blocked request validation
- `403`: blocked by domain policy
- `429`: domain rate limit exceeded
- `502`: upstream fetch/provider error

## MCP Server

This repository uses FastMCP as a thin wrapper over the API.

Run MCP server:

```bash
uv run --project apps/mcp python -m app.main
```

Exposed tools:
- `openagentsearch.search`
- `openagentsearch.extract`

MCP environment variables:
- `OAS_API_BASE_URL` (default: `http://api:8000`)
- `OAS_API_TIMEOUT_SECONDS` (default: `20`)
- `OAS_AUTH_HEADER_NAME` (optional)
- `OAS_AUTH_HEADER_VALUE` (optional)

Per-call auth override is supported by providing:
- `auth_header_name`
- `auth_header_value`

## Configuration

Main API environment variables:
- `REDIS_URL` (example: `redis://redis:6379/0`)
- `SEARXNG_BASE_URL` (default: `http://searxng:8080`)
- `SEARXNG_TIMEOUT_SECONDS` (default: `12`)
- `SEARCH_CACHE_TTL_SECONDS` (default: `120`)
- `EXTRACT_CACHE_TTL_SECONDS` (default: `600`)
- `DOMAIN_POLICY_FILE` (path to domain policy file)
- `EXTRACT_RATE_LIMIT_ENABLED` (default: `true`)
- `EXTRACT_RATE_LIMIT_TOKENS_PER_SEC` (default: `1.0`)
- `EXTRACT_RATE_LIMIT_BURST` (default: `3`)
- `OAS_DISABLE_RATE_LIMIT` (default: `false`)

Domain policy sample:
- `infra/domain_policies.json`

## Testing

Install project environments:

```bash
uv sync --project apps/api
uv sync --project apps/mcp
```

Run unit tests:

```bash
uv run python -m unittest discover -s tests -v
```

Run integration tests (Docker required):

PowerShell:

```powershell
$env:OAS_RUN_DOCKER_TESTS='1'
uv run python -m unittest tests.test_m1_stack_integration -v
```

Bash:

```bash
OAS_RUN_DOCKER_TESTS=1 uv run python -m unittest tests.test_m1_stack_integration -v
```

## Project Layout

- `apps/api` - FastAPI service
- `apps/mcp` - FastMCP service
- `infra` - infra and policy config
- `tests` - unit and integration tests
- `plan/PLAN_v1.md` - milestone plan and progress notes
