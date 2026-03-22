# -*- coding: utf-8 -*-
"""
Business Claw - MCP Client

Client for calling the Business Claw MCP server (bc_mcp) tools.
"""

import frappe
import json
import requests
from typing import Any, Dict, List, Optional
from frappe.utils import get_url


class MCPClient:
    """
    Client for interacting with the Business Claw MCP server.

    This client calls the local bc_mcp server which routes to the ToolRouter.
    """

    def __init__(self, site_url: str = None, api_key: str = None):
        """
        Initialize MCP Client.

        Args:
            site_url: Frappe site URL (defaults to current site)
            api_key: API key for authentication (defaults to session user)
        """
        self.site_url = site_url or get_url()
        self.api_key = api_key
        self.endpoint = (
            f"{self.site_url}/api/method/business_claw.bc_mcp.server.handle_request"
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _make_request(self, method: str, params: Dict = None) -> Dict:
        """
        Make a JSON-RPC request to the MCP server.

        Args:
            method: MCP method name
            params: Method parameters

        Returns:
            Response data from MCP server
        """
        request_id = frappe.generate_hash(length=8)

        payload = {"jsonrpc": "2.0", "id": request_id, "method": method}

        if params:
            payload["params"] = params

        try:
            response = requests.post(
                self.endpoint, json=payload, headers=self._get_headers(), timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            frappe.log_error(f"MCP Client Error: {str(e)}", "Agent Runner MCP Client")
            raise

    def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """
        Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        result = self._make_request(
            "tools/call", params={"name": tool_name, "arguments": arguments}
        )

        if "error" in result:
            error_msg = result["error"].get("message", "Unknown error")
            raise Exception(f"MCP tool error: {error_msg}")

        content = result.get("result", {}).get("content", [])
        if content and content[0].get("type") == "text":
            return json.loads(content[0]["text"])

        if result.get("result", {}).get("isError"):
            raise Exception(
                result.get("result", {})
                .get("content", [{"text": "Unknown error"}])[0]
                .get("text", "Unknown error")
            )

        return result.get("result", {})

    def list_tools(self) -> List[Dict]:
        """
        List available MCP tools.

        Returns:
            List of tool definitions
        """
        result = self._make_request("tools/list")

        if "error" in result:
            error_msg = result["error"].get("message", "Unknown error")
            raise Exception(f"MCP tools/list error: {error_msg}")

        return result.get("result", {}).get("tools", [])

    def initialize(self) -> Dict:
        """
        Initialize MCP connection and get server info.

        Returns:
            Server capabilities and info
        """
        result = self._make_request("initialize")

        if "error" in result:
            error_msg = result["error"].get("message", "Unknown error")
            raise Exception(f"MCP initialize error: {error_msg}")

        return result.get("result", {})


_mcp_client_instance: Optional[MCPClient] = None


def get_mcp_client(site_url: str = None, api_key: str = None) -> MCPClient:
    """
    Factory function to get or create MCP client instance.

    Args:
        site_url: Optional site URL
        api_key: Optional API key

    Returns:
        MCPClient instance
    """
    global _mcp_client_instance

    if _mcp_client_instance is None:
        _mcp_client_instance = MCPClient(site_url, api_key)

    return _mcp_client_instance


def reset_mcp_client():
    """Reset the MCP client instance (for testing or reconnection)."""
    global _mcp_client_instance
    _mcp_client_instance = None
