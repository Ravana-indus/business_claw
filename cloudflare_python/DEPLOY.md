# Deploy FrappeMCP to Cloudflare Workers (Python)

## Prerequisites

1. Cloudflare account
2. Wrangler CLI: `npm install -g wrangler`
3. Python 3.11+

## Quick Deploy

```bash
# Navigate to project
cd frappe-bench/apps/business_claw/cloudflare_python

# Set environment variables
export FRAPPE_URL="https://your-erpnext.com"
export FRAPPE_API_KEY="your-api-key"
export FRAPPE_API_SECRET="your-api-secret"

# Or set as secrets
wrangler secret put FRAPPE_API_KEY
wrangler secret put FRAPPE_API_SECRET

# Deploy
wrangler deploy
```

## Configuration

Edit `wrangler.toml`:
```toml
name = "frappemcp-python"
main = "src/index.py"
compatibility_date = "2024-11-01"

[vars]
FRAPPE_URL = "https://your-erpnext.com"
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Health check |
| `/health` | Health check |
| `/mcp` | MCP JSON-RPC endpoint |
| `/sse` | SSE endpoint for tools list |

## Usage

### Direct API Call
```bash
curl -X POST https://frappemcp-python.your-account.workers.dev/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### With mcp-remote (Claude Desktop)
```json
{
  "mcpServers": {
    "frappemcp": {
      "command": "npx",
      "args": ["mcp-remote", "https://frappemcp-python.your-account.workers.dev/mcp"]
    }
  }
}
```

## Tools Available

- get_document
- create_document
- update_document
- delete_document
- list_documents
- get_count
- search_documents
- get_doctype_meta
- get_doctype_fields
- submit_document
- cancel_document
- list_doctypes
