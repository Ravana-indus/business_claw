# -*- coding: utf-8 -*-
"""
Business Claw - MCP Server

HTTP endpoint that implements the Model Context Protocol (MCP) for ERPNext.
This server exposes tools that AI assistants can call to interact with ERPNext.
Supports both HTTP POST and SSE (Server-Sent Events) transport.
"""

import json
import frappe
from typing import Any, Dict, List, Optional
from .router import ToolRouter
from .auth import authenticate_request
from .response import (
	create_success_response,
	create_error_response,
	create_approval_required_response
)
from ..bc_audit.logger import log_action
from ..bc_guardrails.policy import PolicyEngine
from werkzeug.wrappers import Response as WerkzeugResponse


def _make_json_response(data: Dict) -> WerkzeugResponse:
	"""
	Convert a dict to a Werkzeug Response with proper JSON content-type.
	
	This bypasses Frappe's automatic wrapping in {"message": ...}.
	"""
	return WerkzeugResponse(
		json.dumps(data),
		status=200,
		content_type="application/json"
	)


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def handle_request():
	"""
	Main MCP endpoint handler.
	
	Handles JSON-RPC 2.0 requests and routes them to appropriate tools.
	Supports both HTTP POST and SSE (Server-Sent Events) transport.
	
	For SSE (GET request):
	- Returns an event stream with the endpoint URL
	
	For HTTP (POST request):
	{
		"jsonrpc": "2.0",
		"method": "tools/call",
		"params": {
			"name": "tool_name",
			"arguments": {...}
		},
		"id": "request-id"
	}
	"""
	# Import werkzeug Response
	from werkzeug.wrappers import Response
	
	# Handle SSE connection (GET request)
	if frappe.request.method == "GET":
		return _handle_sse_connection()
	
	# Handle regular JSON-RPC request (POST)
	try:
		# Parse request body
		request_data = _get_request_data()
		
		# Validate JSON-RPC structure
		_validate_jsonrpc(request_data)
		
		# Authenticate the request
		user = authenticate_request()
		if not user:
			return _make_json_response(create_error_response(
				request_data.get("id"),
				-32600,
				"Invalid authentication credentials"
			))
		
		# Set user context
		frappe.set_user(user)
		
		# Extract tool call details
		method = request_data.get("method")
		params = request_data.get("params", {})
		request_id = request_data.get("id")
		
		# Handle different MCP methods
		if method == "tools/list":
			return _make_json_response(_handle_list_tools(request_id))
		elif method == "tools/call":
			return _make_json_response(_handle_tool_call(request_id, params, user))
		elif method == "initialize":
			return _make_json_response(_handle_initialize(request_id))
		else:
			return _make_json_response(create_error_response(
				request_id,
				-32601,
				f"Method not found: {method}"
			))
			
	except json.JSONDecodeError:
		return _make_json_response(create_error_response(None, -32700, "Parse error: Invalid JSON"))
	except Exception as e:
		frappe.log_error(f"MCP Server Error: {str(e)}", "Business Claw")
		return _make_json_response(create_error_response(
			None,
			-32603,
			"Internal error"
		))


def _handle_sse_connection():
	"""
	Handle SSE (Server-Sent Events) connection for MCP transport.
	
	Returns an event stream with the message endpoint URL.
	"""
	# Import werkzeug Response for SSE support
	from werkzeug.wrappers import Response
	
	# Authenticate the request
	user = authenticate_request()
	if not user:
		return Response(
			'{"error": "Authentication required"}',
			status=403,
			content_type="application/json"
		)
	
	# Set user context
	frappe.set_user(user)
	
	# Get the base URL for the message endpoint
	base_url = frappe.utils.get_url()
	message_endpoint = f"{base_url}/api/method/business_claw.bc_mcp.server.handle_request"
	
	# Create SSE response
	endpoint_event = f"event: endpoint\ndata: {message_endpoint}\n\n"
	response = Response(
		endpoint_event,
		status=200,
		content_type="text/event-stream",
		headers=[
			("Cache-Control", "no-cache"),
			("Connection", "keep-alive"),
			("X-Accel-Buffering", "no")
		]
	)
	
	return response


def _get_request_data() -> Dict:
	"""Extract and parse request body."""
	if frappe.request and frappe.request.data:
		return json.loads(frappe.request.data)
	return frappe.local.form_dict


def _validate_jsonrpc(request_data: Dict):
	"""Validate JSON-RPC 2.0 request structure."""
	if not isinstance(request_data, dict):
		raise ValueError("Request must be a JSON object")
	
	if request_data.get("jsonrpc") != "2.0":
		raise ValueError("Invalid JSON-RPC version")
	
	if not request_data.get("method"):
		raise ValueError("Method is required")


def _handle_list_tools(request_id: str) -> Dict:
	"""Handle tools/list method - return available tools."""
	router = ToolRouter()
	tools = router.get_tool_definitions()
	
	return create_success_response(request_id, {
		"tools": tools
	})


def _handle_tool_call(request_id: str, params: Dict, user: str) -> Dict:
	"""
	Handle tools/call method - execute a tool.
	
	Params format:
	{
		"name": "tool_name",
		"arguments": {...}
	}
	"""
	tool_name = params.get("name")
	arguments = params.get("arguments", {})
	
	if not tool_name:
		return create_error_response(
			request_id,
			-32602,
			"Tool name is required"
		)
	
	# Get tool from registry
	router = ToolRouter()
	tool = router.get_tool(tool_name)
	
	if not tool:
		return create_error_response(
			request_id,
			-32601,
			f"Tool not found: {tool_name}"
		)
	
	# Validate arguments against schema
	validation_result = router.validate_arguments(tool_name, arguments)
	if not validation_result["valid"]:
		return create_error_response(
			request_id,
			-32602,
			f"Invalid arguments: {validation_result['error']}"
		)
	
	# Check guardrails
	policy = PolicyEngine()
	guardrail_result = policy.check_tool_allowed(tool_name, arguments, user)
	
	if not guardrail_result["allowed"]:
		return create_error_response(
			request_id,
			-32600,
			f"Action not allowed: {guardrail_result['reason']}"
		)
	
	# Check if approval is required
	if guardrail_result.get("requires_approval"):
		# Create approval request
		approval_request = policy.create_approval_request(
			tool_name=tool_name,
			arguments=arguments,
			user=user,
			summary=guardrail_result.get("summary", "")
		)
		
		# Log the pending action
		log_action(
			tool_name=tool_name,
			request_json=arguments,
			response_json={"status": "approval_required"},
			risk_level=guardrail_result.get("risk_level", "high"),
			approval_required=True,
			reference_doctype=arguments.get("doctype"),
			reference_name=arguments.get("name")
		)
		
		return create_approval_required_response(
			request_id,
			approval_request,
			guardrail_result.get("summary", "")
		)
	
	# Execute the tool
	try:
		result = router.execute_tool(tool_name, arguments, user)
		
		# Log successful action
		log_action(
			tool_name=tool_name,
			request_json=arguments,
			response_json=result,
			risk_level=guardrail_result.get("risk_level", "low"),
			approval_required=False,
			reference_doctype=result.get("doctype") or arguments.get("doctype"),
			reference_name=result.get("name") or arguments.get("name")
		)
		
		return create_success_response(request_id, {
			"content": [
				{
					"type": "text",
					"text": json.dumps(result, default=str)
				}
			]
		})
		
	except frappe.PermissionError as e:
		return create_error_response(
			request_id,
			-32600,
			f"Permission denied: {str(e)}"
		)
	except Exception as e:
		frappe.log_error(
			f"Tool execution error: {tool_name}\nArguments: {arguments}\nError: {str(e)}",
			"Business Claw Tool Error"
		)
		return create_error_response(
			request_id,
			-32603,
			f"Tool execution failed: {str(e)}"
		)


def _handle_initialize(request_id: str) -> Dict:
	"""Handle initialize method - return server capabilities."""
	return create_success_response(request_id, {
		"protocolVersion": "2024-11-05",
		"capabilities": {
			"tools": {
				"listChanged": False
			}
		},
		"serverInfo": {
			"name": "business-claw",
			"version": "1.0.0"
		}
	})
