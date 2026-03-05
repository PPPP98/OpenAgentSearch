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
- Deterministic reranking (title/snippet/domain/path/diversity signals)
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
    "limit": 5,
    "language": "en",
    "time_range": "month",
    "safesearch": 1
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

### F. Connect MCP (Step-by-Step)

This is the part many users miss. `apps/mcp` has its own Python dependencies, so you must sync that environment before connecting from your MCP client.

1. Start API first (required):

```bash
docker compose up -d --build
```

2. Install/sync MCP dependencies in `apps/mcp`:

```bash
uv sync --project apps/mcp --frozen --no-dev
```

If lock-based install fails in your environment, use:

```bash
uv sync --project apps/mcp
```

3. Smoke test MCP server locally:

```bash
uv run --project apps/mcp python -m app.main
```

If it starts without import/runtime errors, stop with `Ctrl+C`.

4. Set `OAS_API_BASE_URL` correctly for your runtime:

- MCP client on host OS: `http://localhost:8000`
- MCP client inside same Docker network: `http://api:8000`

5. Configure your MCP client (`mcp.json` or equivalent).

Important path rule:
- Use an absolute `--project` path so it works regardless of where the client process starts.
- On Windows, use either escaped backslashes (`\\`) or forward slashes (`/`).

Windows example (`C:/path/to/OpenAgentSearch`):

```json
{
  "mcpServers": {
    "openagentsearch": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "C:/path/to/OpenAgentSearch/apps/mcp",
        "python",
        "-m",
        "app.main"
      ],
      "env": {
        "OAS_API_BASE_URL": "http://localhost:8000",
        "OAS_API_TIMEOUT_SECONDS": "20"
      }
    }
  }
}
```

macOS/Linux example:

```json
{
  "mcpServers": {
    "openagentsearch": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/absolute/path/to/OpenAgentSearch/apps/mcp",
        "python",
        "-m",
        "app.main"
      ],
      "env": {
        "OAS_API_BASE_URL": "http://localhost:8000",
        "OAS_API_TIMEOUT_SECONDS": "20"
      }
    }
  }
}
```

6. Restart MCP client app completely, then confirm tools:

- `openagentsearch.search`
- `openagentsearch.extract`

7. Quick troubleshooting:

- `uv: command not found`: install `uv` and ensure it is in `PATH`.
- `No module named fastmcp` or `httpx`: run `uv sync --project apps/mcp`.
- Connection refused/timeouts: verify API health at `http://localhost:8000/health`.
- Tools do not appear after config edit: check JSON syntax and restart client app.

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
| `SEARCH_RERANK_TITLE_WEIGHT` | `1.5` | Query-title overlap weight |
| `SEARCH_RERANK_SNIPPET_WEIGHT` | `0.8` | Query-snippet overlap weight |
| `SEARCH_RERANK_DOMAIN_WEIGHT` | `0.5` | Domain prior weight |
| `SEARCH_RERANK_PATH_WEIGHT` | `0.35` | URL path quality weight |
| `SEARCH_RERANK_DIVERSITY_WEIGHT` | `0.35` | Same-domain diversity penalty weight |
| `SEARCH_RERANK_SOURCE_SCORE_WEIGHT` | `0.05` | Upstream score blending weight |
| `SEARCH_RERANK_DOMAIN_PRIORS_JSON` | - | Domain prior overrides as JSON object |

Sample policy file:

- `infra/domain_policies.json`

## API Quick Reference

`POST /v1/search`

- Input: `query`, `mode`, `limit`, `page`, `categories`, `engines`, `language`, `time_range`, `safesearch`, `extract_top_n`, `max_extract_chars`
- Output: `query`, `mode`, `limit`, `page`, `language`, `time_range`, `safesearch`, `results[]`, `cached`
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

- `query`, `mode`, `limit`, `page`, `categories`, `engines`, `language`, `time_range`, `safesearch`, `extract_top_n`, `max_extract_chars`

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
- `artifacts/search-compare`: benchmark inputs/results/reports
- `plan/PLAN_v2_search_quality_upgrade.md`: quality upgrade milestone checklist
