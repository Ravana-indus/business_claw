"""
FrappeMCP - Cloudflare Workers Python Implementation
A remote MCP server for ERPNext on Cloudflare Workers
"""

import asyncio
import json
from typing import Any, Optional

import httpx


class Config:
    """Server configuration from environment."""
    
    def __init__(self, env: dict):
        self.frappe_url = env.get("FRAPPE_URL", "")
        self.api_key = env.get("FRAPPE_API_KEY", "")
        self.api_secret = env.get("FRAPPE_API_SECRET", "")
    
    def get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"token {self.api_key}:{self.api_secret}",
        }


class FrappeClient:
    """Client for Frappe/ERPNext API."""
    
    def __init__(self, config: Config):
        self.config = config
    
    async def request(self, method: str, endpoint: str, data: Optional[dict] = None, params: Optional[dict] = None) -> dict:
        url = f"{self.config.frappe_url}{endpoint}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(3):
                try:
                    response = await client.request(method=method, url=url, json=data, params=params, headers=self.config.get_headers())
                    response.raise_for_status()
                    return response.json()
                except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException):
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)
        return {}
    
    async def get_document(self, doctype: str, name: str) -> dict:
        return await self.request("GET", f"/api/resource/{doctype}/{name}")
    
    async def create_document(self, doctype: str, data: dict) -> dict:
        return await self.request("POST", f"/api/resource/{doctype}", data=data)
    
    async def update_document(self, doctype: str, name: str, data: dict) -> dict:
        return await self.request("PUT", f"/api/resource/{doctype}/{name}", data=data)
    
    async def delete_document(self, doctype: str, name: str) -> dict:
        return await self.request("DELETE", f"/api/resource/{doctype}/{name}")
    
    async def list_documents(self, doctype: str, filters: Optional[dict] = None, fields: Optional[str] = None, limit: int = 20, order_by: str = "modified desc") -> dict:
        params = {"fields": fields or "[\"name\"]", "limit": limit, "order_by": order_by}
        if filters:
            params["filters"] = json.dumps(filters)
        return await self.request("GET", f"/api/resource/{doctype}", params=params)
    
    async def get_count(self, doctype: str, filters: Optional[dict] = None) -> dict:
        params = {}
        if filters:
            params["filters"] = json.dumps(filters)
        return await self.request("GET", f"/api/method/frappe.client.get_count", params=params)
    
    async def search_documents(self, doctype: str, query: str, limit: int = 20) -> dict:
        return await self.request("POST", "/api/method/frappe.client.validate_and_search", data={"doctype": doctype, "query": query, "limit": limit})
    
    async def get_doctype_meta(self, doctype: str) -> dict:
        return await self.request("POST", "/api/method/frappe.model.meta.get_meta", data={"doctype": doctype})
    
    async def get_doctype_fields(self, doctype: str) -> dict:
        return await self.request("POST", "/api/method/frappe.model.user_settings.get_for", data={"doctype": doctype})
    
    async def submit_document(self, doctype: str, name: str) -> dict:
        return await self.request("POST", "/api/method/frappe.client.submit", data={"doctype": doctype, "name": name})
    
    async def cancel_document(self, doctype: str, name: str) -> dict:
        return await self.request("POST", "/api/method/frappe.client.cancel", data={"doctype": doctype, "name": name})
    
    async def list_doctypes(self, module: str = "") -> dict:
        params = {"module": module} if module else {}
        return await self.request("GET", "/api/method/frappe.model.meta.get_doctype_list", params=params)


class MCPHandler:
    """Handle MCP protocol requests."""
    
    def __init__(self, client: FrappeClient):
        self.client = client
    
    async def handle_request(self, method: str, params: dict) -> dict:
        if method == "tools/list":
            return self.list_tools()
        elif method == "tools/call":
            return await self.call_tool(params.get("name"), params.get("arguments", {}))
        elif method == "resources/list":
            return self.list_resources()
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def list_tools(self) -> dict:
        return {
            "tools": [
                {"name": "get_document", "description": "Fetch a document", "inputSchema": {"type": "object", "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}}, "required": ["doctype", "name"]}},
                {"name": "create_document", "description": "Create a document", "inputSchema": {"type": "object", "properties": {"doctype": {"type": "string"}, "data": {"type": "object"}}, "required": ["doctype", "data"]}},
                {"name": "update_document", "description": "Update a document", "inputSchema": {"type": "object", "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}, "data": {"type": "object"}}, "required": ["doctype", "name", "data"]}},
                {"name": "delete_document", "description": "Delete a document", "inputSchema": {"type": "object", "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}}, "required": ["doctype", "name"]}},
                {"name": "list_documents", "description": "List documents", "inputSchema": {"type": "object", "properties": {"doctype": {"type": "string"}, "filters": {"type": "object"}, "limit": {"type": "number"}}, "required": ["doctype"]}},
                {"name": "get_count", "description": "Count documents", "inputSchema": {"type": "object", "properties": {"doctype": {"type": "string"}, "filters": {"type": "object"}}, "required": ["doctype"]}},
                {"name": "search_documents", "description": "Search documents", "inputSchema": {"type": "object", "properties": {"doctype": {"type": "string"}, "query": {"type": "string"}, "limit": {"type": "number"}}, "required": ["query"]}},
                {"name": "get_doctype_meta", "description": "Get DocType metadata", "inputSchema": {"type": "object", "properties": {"doctype": {"type": "string"}}, "required": ["doctype"]}},
                {"name": "get_doctype_fields", "description": "Get DocType fields", "inputSchema": {"type": "object", "properties": {"doctype": {"type": "string"}}, "required": ["doctype"]}},
                {"name": "submit_document", "description": "Submit a document", "inputSchema": {"type": "object", "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}}, "required": ["doctype", "name"]}},
                {"name": "cancel_document", "description": "Cancel a document", "inputSchema": {"type": "object", "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}}, "required": ["doctype", "name"]}},
                {"name": "list_doctypes", "description": "List DocTypes", "inputSchema": {"type": "object", "properties": {"module": {"type": "string"}}}},
            ]
        }
    
    async def call_tool(self, name: str, args: dict) -> dict:
        result = None
        if name == "get_document":
            result = await self.client.get_document(args["doctype"], args["name"])
        elif name == "create_document":
            result = await self.client.create_document(args["doctype"], args["data"])
        elif name == "update_document":
            result = await self.client.update_document(args["doctype"], args["name"], args["data"])
        elif name == "delete_document":
            result = await self.client.delete_document(args["doctype"], args["name"])
        elif name == "list_documents":
            result = await self.client.list_documents(args["doctype"], args.get("filters"), None, args.get("limit", 20))
        elif name == "get_count":
            result = await self.client.get_count(args["doctype"], args.get("filters"))
        elif name == "search_documents":
            result = await self.client.search_documents(args.get("doctype", ""), args["query"], args.get("limit", 20))
        elif name == "get_doctype_meta":
            result = await self.client.get_doctype_meta(args["doctype"])
        elif name == "get_doctype_fields":
            result = await self.client.get_doctype_fields(args["doctype"])
        elif name == "submit_document":
            result = await self.client.submit_document(args["doctype"], args["name"])
        elif name == "cancel_document":
            result = await self.client.cancel_document(args["doctype"], args["name"])
        elif name == "list_doctypes":
            result = await self.client.list_doctypes(args.get("module", ""))
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    
    def list_resources(self) -> dict:
        return {"resources": [{"uri": "mcp://server/info", "name": "Server Info", "description": "MCP Server Info"}]}


async def on_fetch(request: Any, env: dict) -> Response:
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    msg_id = body.get("id")
    
    config = Config(env)
    client = FrappeClient(config)
    handler = MCPHandler(client)
    
    try:
        result = await handler.handle_request(method, params)
        return Response(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}), headers={"Content-Type": "application/json"})
    except Exception as e:
        return Response(json.dumps({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(e)}}), headers={"Content-Type": "application/json"}, status=500)


def on_request(request: Request, env: dict, ctx: Any) -> Response:
    url = request.url.path
    
    if url in ["/health", "/"]:
        return Response(json.dumps({"status": "healthy", "service": "FrappeMCP", "version": "1.0.0"}), headers={"Content-Type": "application/json"})
    
    if url in ["/mcp", "/api/mcp"]:
        return on_fetch(request, env)
    
    if url == "/sse":
        handler = MCPHandler(FrappeClient(Config(env)))
        return Response(json.dumps(handler.list_tools()), headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"})
    
    return Response("Not Found", status=404)
