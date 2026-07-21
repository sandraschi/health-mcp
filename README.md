# health-mcp

Multi-source health data fusion MCP server. Ingests from Visual State Machines
(devices-mcp camera watchers), Apple Health exports, and manual entries. Stores
in SQLite, exposes trends and queries via FastMCP 3.4+ tools.

**Topics:** `mcp`, `health`, `fastmcp`, `vsm`, `quantified-self`, `pet-health`

## What it does

- **Log health metrics** — weight, heart rate, sleep, meals, steps, BP, mood, symptoms
- **Import Apple Health** — parse `export.xml` (zip or raw) from iOS Health app
- **Receive VSM events** — camera-based state machine events from devices-mcp
  (scale reading, fridge open/close, dog bowl empty, bedroom wake detection)
- **Trend analysis** — average, min, max, direction over any time window
- **Pet health** — feeding schedules, activity events from VSM
- **Prefab UI dashboard** — rich in-chat summary card

## Quick Start

```powershell
uv sync
uv run health-mcp             # stdio (for Claude Desktop, Cursor)
uv run health-mcp --http      # HTTP on :10902
```

## MCP Client Config

```json
"mcpServers": {
  "health-mcp": {
    "command": "uv",
    "args": ["--directory", "D:/Dev/repos/health-mcp", "run", "health-mcp"]
  }
}
```

## Tools

| Tool | Operations |
|------|-----------|
| `health_data` | log_record, query, trend, import_apple_health, get_stats, log_vsm_event |
| `show_health_dashboard` | Rich Prefab UI card with recent stats |

## Ports

| Service | Port |
|---------|------|
| MCP HTTP transport | 10902 |

## VSM Event Integration

health-mcp consumes events from devices-mcp's Visual State Machine watchers:

```
devices-mcp: camera sees scale reading ──► health-mcp logs weight
devices-mcp: camera sees dog bowl empty ──► health-mcp logs pet_feeding
devices-mcp: camera sees bedroom door open ──► health-mcp logs sleep_end
```

Send events via the `health_data(operation="log_vsm_event", ...)` tool.

## Apple Health Import

```python
# From MCP agent:
health_data(
    operation="import_apple_health",
    file_path="C:/Users/sandra/Downloads/export.zip"
)
```

Extracts and parses `export.xml`, mapping HK types to health-mcp metrics.

## Data Storage

SQLite at `~/.health-mcp/health.db`. WAL mode, thread-safe.
