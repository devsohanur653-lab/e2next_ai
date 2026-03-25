# E2Next AI - Deployment Guide

Step-by-step guide to get the MCP server running and connected to Cursor/Claude Desktop.

---

## How It Works

```
Cursor / Claude Desktop
        |
        | HTTPS request
        v
   https://testpwa.mke.bd/mcp/sse
        |
        v
   Nginx (port 443)
        |
        | proxy_pass (location /mcp)
        v
   MCP Server (127.0.0.1:8001)
        |
        | Frappe ORM
        v
   ERPNext Database (MariaDB)
```

---

## Install on Another Bench Server (Quick)

If you're installing this app on a **different** ERPNext/Frappe bench server:

```bash
cd /home/frappe-user/frappe-bench
bench get-app <YOUR_GIT_REPO_URL> --branch develop
bench --site <site-name> install-app e2next_ai
```

Then continue with **Step 4** (Supervisor) and **Step 5** (Nginx) below.

---

## Step 1: Verify the MCP Python Package

The `mcp` package must be installed in the bench Python environment.

```bash
# Check if installed
/home/frappe-user/frappe-bench/env/bin/pip show mcp

# If not installed, run:
/home/frappe-user/frappe-bench/env/bin/pip install mcp
```

---

## Step 2: Verify the Bench Command Works

```bash
cd /home/frappe-user/frappe-bench
bench mcp-server --help
```

Expected output:

```
Usage: bench  mcp-server [OPTIONS]

  Start the E2Next AI MCP server.

Options:
  --transport [stdio|sse]  MCP transport type
  --host TEXT              Host to bind SSE server (default: 127.0.0.1)
  --port INTEGER           Port for SSE server (default: 8001)
  --help                   Show this message and exit.
```

---

## Step 3: Test the MCP Server Locally

Start it manually first to make sure it works:

```bash
cd /home/frappe-user/frappe-bench
bench mcp-server
```

You should see output like:

```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8001
```

Test it from the same server:

```bash
curl -N http://127.0.0.1:8001/sse
```

You should see SSE event stream output (starting with `event:` and `data:` lines). Press `Ctrl+C` to stop.

If this fails, check:
- Is port 8001 already in use? `ss -tlnp | grep 8001`
- Is the Frappe site set? `cat /home/frappe-user/frappe-bench/sites/currentsite.txt`

---

## Step 4: Reload Supervisor (Production Auto-Start)

The MCP server has already been added to `config/supervisor.conf`. Tell supervisor to pick it up:

```bash
sudo supervisorctl reread
sudo supervisorctl update
```

Verify it's running:

```bash
sudo supervisorctl status
```

You should see a line like:

```
frappe-bench-web:frappe-bench-mcp-server   RUNNING   pid 12345, uptime 0:00:05
```

If it says `FATAL` or `STOPPED`, check the logs:

```bash
cat /home/frappe-user/frappe-bench/logs/mcp-server.log
cat /home/frappe-user/frappe-bench/logs/mcp-server.error.log
```

---

## Step 5: Reload Nginx

The nginx config has already been updated with the `/mcp` proxy. Test and reload:

```bash
# Test config syntax first (IMPORTANT - do this before reload)
sudo nginx -t
```

Expected output:

```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

If the test passes, reload:

```bash
sudo systemctl reload nginx
```

If the test FAILS, check the error message. The config file is at:

```
/home/frappe-user/frappe-bench/config/nginx.conf
```

---

## Step 6: Test the Public URL

From your local machine (or any browser), test:

```bash
curl -N https://testpwa.mke.bd/mcp/sse
```

You should see SSE event stream data. If you get:

| Error | Cause | Fix |
|-------|-------|-----|
| `404 Page not found` (HTML) | Nginx is sending request to Frappe, not MCP server | Nginx not reloaded, or `/mcp` location block missing |
| `502 Bad Gateway` | Nginx can't reach MCP server | MCP server not running on port 8001, check supervisor |
| `Connection refused` | Nginx not running | `sudo systemctl start nginx` |
| SSL error | Certificate issue | Check letsencrypt cert for your domain |

---

## Step 7: Connect from Cursor

1. Open Cursor
2. Go to **Settings** (gear icon) > **MCP Servers**
3. Click **Add new MCP Server**
4. Fill in:

| Field | Value |
|-------|-------|
| Name | `e2next-ai` |
| Type | `sse` |
| URL | `https://testpwa.mke.bd/mcp/sse` |

Or manually edit `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "e2next-ai": {
      "url": "https://testpwa.mke.bd/mcp/sse"
    }
  }
}
```

After adding, Cursor should show a green dot next to the server name. You can verify by asking Cursor:

> "What tools are available from e2next-ai?"

It should list:
- `get_customer_outstanding`
- `get_customer_ledger`
- `get_top_customers`
- `get_sales_summary`
- `get_top_selling_items`

---

## Step 8: Connect from Claude Desktop

Edit `claude_desktop_config.json`:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "e2next-ai": {
      "url": "https://testpwa.mke.bd/mcp/sse"
    }
  }
}
```

Restart Claude Desktop after saving.

---

## Quick Reference: Commands Cheat Sheet

```bash
# ── Start/Stop MCP Server ──────────────────────────
sudo supervisorctl start frappe-bench-web:frappe-bench-mcp-server
sudo supervisorctl stop frappe-bench-web:frappe-bench-mcp-server
sudo supervisorctl restart frappe-bench-web:frappe-bench-mcp-server

# ── Check Status ───────────────────────────────────
sudo supervisorctl status | grep mcp

# ── View Logs ──────────────────────────────────────
tail -f /home/frappe-user/frappe-bench/logs/mcp-server.log
tail -f /home/frappe-user/frappe-bench/logs/mcp-server.error.log

# ── Reload After Config Changes ───────────────────
sudo supervisorctl reread && sudo supervisorctl update
sudo nginx -t && sudo systemctl reload nginx

# ── Test Locally ───────────────────────────────────
curl -N http://127.0.0.1:8001/sse

# ── Test Publicly ──────────────────────────────────
curl -N https://testpwa.mke.bd/mcp/sse
```

---

## Files Modified (Reference)

These files have already been modified. This section is for reference only.

### `config/supervisor.conf` — added MCP server process

```ini
[program:frappe-bench-mcp-server]
command=/home/frappe-user/.local/bin/bench mcp-server
priority=4
autostart=true
autorestart=true
stdout_logfile=/home/frappe-user/frappe-bench/logs/mcp-server.log
stderr_logfile=/home/frappe-user/frappe-bench/logs/mcp-server.error.log
user=frappe-user
directory=/home/frappe-user/frappe-bench
killasgroup=true
startretries=10
```

Also added `frappe-bench-mcp-server` to the `[group:frappe-bench-web]` programs list.

### `config/nginx.conf` — added MCP upstream and location

```nginx
# Added at the top alongside other upstreams:
upstream frappe-bench-mcp-server {
    server 127.0.0.1:8001 fail_timeout=0;
}

# Added inside the HTTPS server block (port 443), before location /:
location /mcp {
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 86400s;
    chunked_transfer_encoding off;

    proxy_pass http://frappe-bench-mcp-server;
}
```

Key nginx settings for SSE:
- `proxy_buffering off` — prevents nginx from buffering SSE events
- `proxy_cache off` — no caching of event stream
- `proxy_read_timeout 86400s` — keeps SSE connection alive for 24 hours
- `Connection ''` — prevents premature connection close
- `chunked_transfer_encoding off` — required for SSE

### `Procfile` — added for development mode

```
mcp_server: bench mcp-server
```

---

## Troubleshooting

### MCP server starts but tools return errors

The Frappe site must be set:

```bash
cat /home/frappe-user/frappe-bench/sites/currentsite.txt
# Should output: site1.local
```

If empty or missing:

```bash
bench use site1.local
```

### Supervisor says "no such process"

After editing `supervisor.conf`, you must run:

```bash
sudo supervisorctl reread
sudo supervisorctl update
```

### nginx -t fails with "upstream not found"

Make sure the `upstream frappe-bench-mcp-server` block is at the **top** of `config/nginx.conf`, alongside the other upstream blocks.

### Connection works locally but not from Cursor

Check if your server firewall allows inbound HTTPS (port 443). The MCP server itself only needs to be reachable on `127.0.0.1:8001` — nginx handles the public-facing connection.

### bench setup nginx / bench setup supervisor overwrites my changes

This can happen when bench regenerates configs. After regeneration, you'll need to re-add:
- The MCP upstream + location block in `config/nginx.conf`
- The MCP program + group entry in `config/supervisor.conf`

Consider keeping a backup of your additions so you can quickly re-apply them.
