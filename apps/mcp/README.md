# OpenAgentSearch MCP (FastMCP)

This app uses `fastmcp` as a thin wrapper over OpenAgentSearch API.

Exposed tools:
- `openagentsearch.search`
- `openagentsearch.extract`

Runtime:
```bash
uv run --project apps/mcp python -m app.main
```

Environment:
- `OAS_API_BASE_URL` (default: `http://api:8000`)
- `OAS_API_TIMEOUT_SECONDS` (default: `20`)
- `OAS_AUTH_HEADER_NAME` (optional)
- `OAS_AUTH_HEADER_VALUE` (optional)

Each tool call can override auth header with `auth_header_name` and `auth_header_value`.

