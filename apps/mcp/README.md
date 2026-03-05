# OpenAgentSearch MCP (FastMCP)

This app uses `fastmcp` as a thin wrapper over OpenAgentSearch API.

Exposed tools:
- `openagentsearch.search`
- `openagentsearch.extract`

`openagentsearch.search` supports search controls:
- `categories` (e.g. `["general", "science"]`)
- `engines` (e.g. `["duckduckgo", "google"]`)
- `language` (`all`, `en`, `ko-kr`, ...)
- `time_range` (`day`, `month`, `year`)
- `safesearch` (`0`, `1`, `2`)

Runtime:
```bash
uv run --project apps/mcp python -m app.main
```

Environment:
- `OAS_API_BASE_URL` (default: `http://localhost:8000`)
- `OAS_API_TIMEOUT_SECONDS` (default: `20`)
- `OAS_AUTH_HEADER_NAME` (optional)
- `OAS_AUTH_HEADER_VALUE` (optional)

Each tool call can override auth header with `auth_header_name` and `auth_header_value`.

## Practical MCP Connection Guide

### 1) Prerequisites

- OpenAgentSearch API must already be running
- Python 3.11+
- `uv` installed and available in `PATH`

### 2) Sync dependencies for this folder

From repository root:

```bash
uv sync --project apps/mcp --frozen --no-dev
```

Fallback (if frozen install is not possible in your environment):

```bash
uv sync --project apps/mcp
```

### 3) Local smoke test

```bash
uv run --project apps/mcp python -m app.main
```

If server starts cleanly, stop with `Ctrl+C`.

### 4) `mcp.json` config

Use absolute path for `--project` to avoid path resolution issues in desktop clients.

Windows example:

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

`OAS_API_BASE_URL` rule:
- MCP client on host OS -> `http://localhost:8000`
- MCP client in same Docker network -> `http://api:8000`

### 5) Verification checklist

- API health is OK at `http://localhost:8000/health`
- MCP client restarted after config change
- Tools are visible:
  - `openagentsearch.search`
  - `openagentsearch.extract`

### 6) Common issues

- `uv` not found -> install `uv` and reopen terminal/client.
- `No module named fastmcp`/`httpx` -> run `uv sync --project apps/mcp`.
- MCP tools not showing -> verify JSON format and absolute `--project` path.
- API call failures -> verify `OAS_API_BASE_URL` and API container status.

