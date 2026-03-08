# -*- coding: utf-8 -*-
"""
Business Claw - Response Formatters

Formats responses according to JSON-RPC 2.0 and MCP specifications.
"""

import json
from typing import Any, Dict, Optional


def create_success_response(request_id: str, result: Any) -> Dict:
	"""
	Create a successful JSON-RPC response.
	
	Args:
		request_id: The request ID from the original request
		result: The result data
		
	Returns:
		JSON-RPC 2.0 response dict
	"""
	return {
		"jsonrpc": "2.0",
		"result": result,
		"id": request_id
	}


def create_error_response(
	request_id: Optional[str],
	code: int,
	message: str,
	data: Optional[Any] = None
) -> Dict:
	"""
	Create an error JSON-RPC response.
	
	Args:
		request_id: The request ID from the original request
		code: Error code (JSON-RPC standard codes)
		message: Error message
		data: Optional additional error data
		
	Returns:
		JSON-RPC 2.0 error response dict
		
	Standard JSON-RPC error codes:
		-32700: Parse error
		-32600: Invalid Request
		-32601: Method not found
		-32602: Invalid params
		-32603: Internal error
	"""
	error = {
		"code": code,
		"message": message
	}
	
	if data is not None:
		error["data"] = data
	
	return {
		"jsonrpc": "2.0",
		"error": error,
		"id": request_id
	}


def create_approval_required_response(
	request_id: str,
	approval_request: Dict,
	summary: str
) -> Dict:
	"""
	Create a response indicating approval is required.
	
	Args:
		request_id: The request ID from the original request
		approval_request: The created approval request document
		summary: Human-readable summary of the action
		
	Returns:
		JSON-RPC response with approval_required status
	"""
	return create_success_response(request_id, {
		"content": [
			{
				"type": "text",
				"text": json.dumps({
					"status": "approval_required",
					"approval_request": approval_request.get("name"),
					"summary": summary,
					"message": (
						"This action requires approval. "
						f"Approval request {approval_request.get('name')} has been created. "
						"An authorized user must approve this request before execution."
					)
				}, default=str)
			}
		]
	})


def create_tool_result(
	data: Any,
	warnings: Optional[list] = None,
	next_actions: Optional[list] = None
) -> Dict:
	"""
	Create a standardized tool result.
	
	Args:
		data: The main result data
		warnings: Optional list of warning messages
		next_actions: Optional list of recommended next actions
		
	Returns:
		Standardized result dict
	"""
	result = {
		"success": True,
		"data": data
	}
	
	if warnings:
		result["warnings"] = warnings
	
	if next_actions:
		result["next_actions"] = next_actions
	
	return result


def create_document_result(
	doc: Dict,
	action: str,
	message: Optional[str] = None
) -> Dict:
	"""
	Create a result for document operations.
	
	Args:
		doc: The document dict
		action: The action performed (created, updated, submitted, etc.)
		message: Optional custom message
		
	Returns:
		Document operation result dict
	"""
	doctype = doc.get("doctype")
	name = doc.get("name")
	docstatus = doc.get("docstatus", 0)
	
	status_map = {
		0: "Draft",
		1: "Submitted",
		2: "Cancelled"
	}
	
	return {
		"success": True,
		"doctype": doctype,
		"name": name,
		"docstatus": docstatus,
		"status": status_map.get(docstatus, "Unknown"),
		"action": action,
		"message": message or f"{doctype} {name} {action} successfully",
		"url": f"/app/{doctype}/{name}"
	}


def create_list_result(
	items: list,
	total_count: int,
	page: int = 1,
	page_size: int = 20
) -> Dict:
	"""
	Create a result for list operations.
	
	Args:
		items: List of items
		total_count: Total number of items available
		page: Current page number
		page_size: Number of items per page
		
	Returns:
		List result dict with pagination info
	"""
	return {
		"success": True,
		"data": items,
		"pagination": {
			"total": total_count,
			"page": page,
			"page_size": page_size,
			"total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 0
		}
	}
