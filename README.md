# OpenAgentSearch

Self-hosted web search and extraction platform for agent workflows.
This project was implemented with vibe coding.

Korean documentation: [README.ko.md](README.ko.md)

> OpenAgentSearch combines SearXNG search with extraction, safety controls, and MCP tools.

## Quick Start (2 min)

```bash
git clone https://github.com/PPPP98/OpenAgentSearch.git
cd OpenAgentSearch
docker compose up -d --build
```

Then check:

- API health: `http://localhost:8000/health`
- API metrics: `http://localhost:8000/internal/metrics`

## Table of Contents

- [Project Overview](#project-overview)
- [Key Advantages](#key-advantages)
- [End-to-End Setup](#end-to-end-setup)
- [Operations and Configuration](#operations-and-configuration)
- [API Quick Reference](#api-quick-reference)
- [MCP Quick Reference](#mcp-quick-reference)
- [Project Layout](#project-layout)

## Project Overview

OpenAgentSearch is a personal OSS project focused on a practical, controllable search layer for agents.

Why I built it:

- I needed web search and page extraction in one place
- I wanted to avoid black-box hosted APIs and rising per-call costs
- I wanted a clean MCP interface for agent clients

This project uses `SearXNG` as a search provider, then adds the missing production layer:

- Structured extraction (`markdown`, `passages`, `content_hash`)
- Caching and safety controls
- MCP tools for direct agent integration

## Key Advantages

- Split API modes: `speed` (SERP only) and `balanced` (SERP + extraction)
- Structured extraction output for downstream LLM pipelines
- Redis caching for both query and extraction responses
- Security baseline: SSRF checks, domain policy, per-domain rate limiting
- FastMCP thin-wrapper design for easy MCP integration
- Simple deployment with Docker Compose

## End-to-End Setup

### A. Prerequisites

1. Docker Desktop with `docker compose`
2. Python 3.11+
3. `uv`
4. Git

### B. Clone

```bash
git clone https://github.com/PPPP98/OpenAgentSearch.git
cd OpenAgentSearch
```

### C. Start Services (Local or Hosted)

1. Start stack:

```bash
docker compose up -d --build
```

2. Check status:

```bash
docker compose ps
```

3. Verify service health:

- API health: `http://localhost:8000/health`
- API metrics: `http://localhost:8000/internal/metrics`
- SearXNG sample: `http://localhost:8080/search?format=json&q=agent`

4. Stop services:

```bash
docker compose down
```

### D. Verify API

1. Search (speed mode):

```bash
curl -X POST "http://localhost:8000/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "latest ai news",
    "mode": "speed",
    "limit": 5
  }'
```

2. Extract a URL:

```bash
curl -X POST "http://localhost:8000/v1/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_chars": 20000
  }'
```

### E. Hosting Notes

Default ports:

| Port | Service | Note |
|---|---|---|
| `8000` | OpenAgentSearch API | Public entry (recommended behind reverse proxy) |
| `8080` | SearXNG | Keep private if possible |

Recommended production setup:

- Expose only API behind reverse proxy (Nginx/Caddy)
- Enable HTTPS/TLS
- Restrict unnecessary firewall ports
- Keep SearXNG internal to private network

### F. Connect MCP

1. Run MCP server:

```bash
uv run --project apps/mcp python -m app.main
```

2. Environment variables:

- `OAS_API_BASE_URL`
- `OAS_API_TIMEOUT_SECONDS`
- `OAS_AUTH_HEADER_NAME` (optional)
- `OAS_AUTH_HEADER_VALUE` (optional)

3. Set `OAS_API_BASE_URL` based on where the MCP client runs:

- client on host OS: `http://localhost:8000`
- client in same Docker network: `http://api:8000`

4. Example MCP config:

```json
{
  "mcpServers": {
    "openagentsearch": {
      "command": "uv",
      "args": ["run", "--project", "apps/mcp", "python", "-m", "app.main"],
      "env": {
        "OAS_API_BASE_URL": "http://localhost:8000",
        "OAS_API_TIMEOUT_SECONDS": "20"
      }
    }
  }
}
```

5. Confirm the following tools are visible:

- `openagentsearch.search`
- `openagentsearch.extract`

## Operations and Configuration

Main API environment variables:

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | - | Redis connection string (example: `redis://redis:6379/0`) |
| `SEARXNG_BASE_URL` | `http://searxng:8080` | SearXNG base URL |
| `SEARXNG_TIMEOUT_SECONDS` | `12` | Upstream timeout |
| `SEARCH_CACHE_TTL_SECONDS` | `120` | Search cache TTL |
| `EXTRACT_CACHE_TTL_SECONDS` | `600` | Extract cache TTL |
| `DOMAIN_POLICY_FILE` | - | Domain policy file path |
| `EXTRACT_RATE_LIMIT_ENABLED` | `true` | Enable per-domain rate limiting |
| `EXTRACT_RATE_LIMIT_TOKENS_PER_SEC` | `1.0` | Token refill rate per second |
| `EXTRACT_RATE_LIMIT_BURST` | `3` | Burst token size |
| `OAS_DISABLE_RATE_LIMIT` | `false` | Force-disable rate limiting |

Sample policy file:

- `infra/domain_policies.json`

## API Quick Reference

`POST /v1/search`

- Input: `query`, `mode`, `limit`, `page`, `categories`, `engines`, `extract_top_n`, `max_extract_chars`
- Output: `query`, `mode`, `limit`, `page`, `results[]`, `cached`
- `results[].extract` can be included in `balanced` mode

`POST /v1/extract`

- Input: `url`, `max_chars`
- Output: `url`, `markdown`, `passages[]`, `title`, `content_hash`, `cached`

Common error codes:

- `400` Invalid input or request validation error
- `403` Blocked by domain policy
- `429` Domain rate limit exceeded
- `502` Upstream/provider/fetch failure

## MCP Quick Reference

Tools:

- `openagentsearch.search`
- `openagentsearch.extract`

`openagentsearch.search` main args:

- `query`, `mode`, `limit`, `page`, `extract_top_n`, `max_extract_chars`

`openagentsearch.extract` main args:

- `url`, `max_chars`

Per-call auth header override:

- `auth_header_name`
- `auth_header_value`

## Project Layout

- `apps/api`: FastAPI service
- `apps/mcp`: FastMCP service
- `infra`: infrastructure and policy files
- `tests`: unit and integration tests
- `plan/PLAN_v1.md`: milestone and progress notes

