# E2Next AI

AI-powered assistant for ERPNext using the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

This Frappe app runs an MCP server that exposes ERPNext data as tools, allowing AI assistants (Claude Desktop, Cursor, etc.) to query your ERP system.

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app e2next_ai
```

## MCP Server

### Auto-Start

The MCP server auto-starts in both development and production:

- **Development** (`bench start`): registered in the `Procfile`
- **Production** (supervisor): registered in `config/supervisor.conf`

The server listens on `127.0.0.1:8001` and is reverse-proxied through nginx at `/mcp/`.

### Manual Start

```bash
# SSE transport (default) — starts HTTP server on port 8001
bench mcp-server

# Custom host/port
bench mcp-server --host 0.0.0.0 --port 9001

# stdio transport (for local pipe-based clients)
bench mcp-server --transport stdio
```

### Production Setup

After modifying configs, reload supervisor and nginx:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo nginx -t && sudo systemctl reload nginx
```

### Connecting from AI Clients

| Environment | SSE URL |
|-------------|---------|
| Local (dev) | `http://localhost:8001/mcp/sse` |
| Production | `https://your-domain.com/mcp/sse` |

**Cursor** — go to Settings > MCP Servers > Add Server:

| Field | Value |
|-------|-------|
| Name | `e2next-ai` |
| Type | `sse` |
| URL | `https://your-domain.com/mcp/sse` |

Or add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "e2next-ai": {
      "url": "https://your-domain.com/mcp/sse"
    }
  }
}
```

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "e2next-ai": {
      "url": "https://your-domain.com/mcp/sse"
    }
  }
}
```

> Replace `your-domain.com` with your actual domain (e.g. `testpwa.mke.bd`).

## Available Tools

### `get_customer_outstanding`

Returns the outstanding (unpaid) amount for a customer.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `customer_name` | string | Yes | Customer ID (e.g. `"CUST-0001"`) |

**Example output:**

```json
{
  "customer_name": "CUST-0001",
  "outstanding_amount": 25000.0
}
```

---

### `get_customer_ledger`

Returns recent general ledger entries for a customer.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `customer_name` | string | Yes | — | Customer ID |
| `limit` | int | No | `50` | Max entries to return |

**Example output:**

```json
{
  "customer_name": "CUST-0001",
  "total_entries": 3,
  "entries": [
    {
      "posting_date": "2025-03-15",
      "voucher_type": "Sales Invoice",
      "voucher_no": "SINV-0042",
      "debit": 15000.0,
      "credit": 0.0,
      "remarks": "Against Sales Invoice SINV-0042"
    },
    {
      "posting_date": "2025-03-10",
      "voucher_type": "Payment Entry",
      "voucher_no": "PE-0018",
      "debit": 0.0,
      "credit": 10000.0,
      "remarks": "Payment received"
    }
  ]
}
```

---

### `get_top_customers`

Returns top customers ranked by outstanding amount or total revenue.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | int | No | `10` | Number of customers |
| `sort_by` | string | No | `"outstanding"` | `"outstanding"` or `"revenue"` |

**Example output:**

```json
{
  "sort_by": "outstanding",
  "total_results": 3,
  "customers": [
    {
      "customer_name": "CUST-0001",
      "customer_label": "Acme Corp",
      "total_revenue": 500000.0,
      "outstanding_amount": 75000.0,
      "invoice_count": 12
    }
  ]
}
```

---

### `get_sales_summary`

Returns an aggregated sales summary for a date range. Defaults to the current fiscal year.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `from_date` | string | No | Fiscal year start | Start date (`YYYY-MM-DD`) |
| `to_date` | string | No | Fiscal year end | End date (`YYYY-MM-DD`) |

**Example output:**

```json
{
  "from_date": "2025-04-01",
  "to_date": "2026-03-25",
  "total_invoices": 156,
  "total_sales": 2500000.0,
  "total_net": 2118644.0,
  "total_taxes": 381356.0,
  "total_outstanding": 320000.0,
  "total_collected": 2180000.0,
  "unique_customers": 45
}
```

---

### `get_top_selling_items`

Returns top selling items ranked by revenue. Defaults to the current fiscal year.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | int | No | `10` | Number of items |
| `from_date` | string | No | Fiscal year start | Start date (`YYYY-MM-DD`) |
| `to_date` | string | No | Fiscal year end | End date (`YYYY-MM-DD`) |

**Example output:**

```json
{
  "from_date": "2025-04-01",
  "to_date": "2026-03-25",
  "total_results": 3,
  "items": [
    {
      "item_code": "ITEM-001",
      "item_name": "Widget Pro",
      "uom": "Nos",
      "total_qty": 500.0,
      "total_revenue": 750000.0,
      "invoice_count": 45
    }
  ]
}
```

## Project Structure

```
e2next_ai/
├── commands.py                    # bench CLI commands
└── mcp_server/
    ├── __init__.py
    ├── server.py                  # MCP server + tool registration
    └── tools/
        ├── __init__.py
        ├── customer.py            # Customer tools (outstanding, ledger, top)
        └── sales.py               # Sales tools (summary, top items)
```

## Adding New Tools

1. Create or update a file in `mcp_server/tools/` with the business logic
2. Register the tool in `mcp_server/server.py` with the `@mcp.tool()` decorator

```python
# In mcp_server/tools/purchase.py
import frappe

def get_purchase_summary() -> dict:
    ...

# In mcp_server/server.py
@mcp.tool()
def get_purchase_summary() -> dict:
    """Get purchase summary."""
    _init_frappe()
    from e2next_ai.mcp_server.tools.purchase import get_purchase_summary as _impl
    return _impl()
```

## Contributing

This app uses `pre-commit` for code formatting and linting:

```bash
cd apps/e2next_ai
pre-commit install
```

Tools used: ruff, eslint, prettier, pyupgrade.

## License

MIT
