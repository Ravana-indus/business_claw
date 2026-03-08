# Deploying FrappeMCP to Cloudflare Workers

This guide covers deploying FrappeMCP as a remote MCP server on Cloudflare Workers.

## Prerequisites

1. **Cloudflare Account** - Sign up at [cloudflare.com](https://cloudflare.com)
2. **Wrangler CLI** - Install via `npm install -g wrangler`
3. **Node.js** - v18+ recommended

## Architecture

```
┌─────────────────┐     SSE      ┌──────────────────┐     API      ┌────────────┐
│  AI Agent       │ ◄──────────► │  Cloudflare      │ ◄─────────► │  ERPNext   │
│  (Claude,       │              │  Workers         │              │  Server    │
│   OpenClaw,     │              │  (FrappeMCP)    │              │            │
│   etc.)         │              │                  │              │            │
└─────────────────┘              └──────────────────┘              └────────────┘
```

## Step 1: Prepare the Project

```bash
# Navigate to cloudflare directory
cd business_claw/bc_mcp/cloudflare

# Install dependencies
npm install
```

## Step 2: Configure Environment

Edit `wrangler.toml`:

```toml
name = "frappemcp"
main = "src/index.ts"
compatibility_date = "2024-01-01"

# Add your ERPNext credentials
[vars]
FRAPPE_URL = "https://your-erpnext-site.com"
```

Or set via secrets (recommended for production):

```bash
wrangler secret put FRAPPE_API_KEY
wrangler secret put FRAPPE_API_SECRET
```

## Step 3: Test Locally

```bash
npm run dev
```

This starts a local dev server at `http://localhost:8787`

## Step 4: Deploy to Cloudflare

### Deploy to Staging
```bash
npm run deploy:staging
```

### Deploy to Production
```bash
npm run deploy:production
```

## Step 5: Connect AI Agents

### Option 1: Workers AI Playground (Easiest)
1. Go to [playground.ai.cloudflare.com](https://playground.ai.cloudflare.com)
2. Enter your MCP server URL: `https://frappemcp.your-account.workers.dev/sse`
3. Click Connect and authenticate

### Option 2: Claude Desktop with mcp-remote

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "frappemcp": {
      "command": "npx",
      "args": ["mcp-remote", "https://frappemcp.your-account.workers.dev/sse"]
    }
  }
}
```

### Option 3: Direct SSE Connection

```javascript
const response = await fetch('https://frappemcp.your-account.workers.dev/sse', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    jsonrpc: '2.0',
    method: 'tools/list'
  })
});
```

## Available Tools

| Tool | Description |
|------|-------------|
| `get_document` | Fetch a document |
| `create_document` | Create a new document |
| `update_document` | Update a document |
| `delete_document` | Delete a document |
| `list_documents` | List documents with filters |
| `search_documents` | Search across DocTypes |
| `get_doctype_meta` | Get DocType metadata |
| `submit_document` | Submit a document |
| `cancel_document` | Cancel a document |

## Authentication

For production, implement Cloudflare Access or API token authentication:

```typescript
// Add to src/index.ts
async function authenticate(request: Request): Promise<boolean> {
  const token = request.headers.get('Authorization');
  return token === `Bearer ${env.API_TOKEN}`;
}
```

## Scaling & Performance

1. **KV Cache** - Cache frequently accessed metadata
2. **Durable Objects** - For stateful sessions
3. **Workers AI** - Optional AI capabilities

## Troubleshooting

### 504 Gateway Timeout
- Increase timeout in wrangler.toml
- Or use Durable Objects for async processing

### CORS Errors
- Add proper CORS headers in response

### Rate Limiting
- Implement per-user rate limiting with KV

## Cost Estimation

- **Free Tier**: 100,000 requests/day
- **Paid**: $5/10GB egress, $0.15/million requests

## Next Steps

1. Add more tools from the full Python implementation
2. Implement session state with Durable Objects
3. Add authentication (OAuth/CF Access)
4. Set up monitoring with Cloudflare Analytics
