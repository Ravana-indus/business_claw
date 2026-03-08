# -*- coding: utf-8 -*-
"""
Business Claw - Tool Router

Routes tool calls to appropriate handlers and manages the tool registry.
"""

import frappe
from typing import Any, Dict, List, Optional, Callable
from functools import wraps


class ToolRouter:
	"""
	Manages tool registration, validation, and execution.
	"""
	
	_registry: Dict[str, Dict] = {}
	_initialized = False
	
	def __init__(self):
		if not ToolRouter._initialized:
			self._load_tools()
			ToolRouter._initialized = True
	
	def _load_tools(self):
		"""Load all tools from the tools module."""
		# Import all tool modules to register them
		from ..bc_tools import (
			system,
			meta,
			doc,
			workflow,
			file as file_tools
		)
		
		# Business tools (optional - may not exist in all installations)
		try:
			from ..bc_tools import crm, sales, finance, stock, project
		except ImportError:
			pass
	
	def register_tool(
		self,
		name: str,
		handler: Callable,
		schema: Dict,
		risk_level: str = "low",
		requires_approval: bool = False,
		description: str = ""
	):
		"""
		Register a tool in the registry.
		
		Args:
			name: Tool name (e.g., "doc.get")
			handler: Function to execute the tool
			schema: JSON Schema for input validation
			risk_level: Risk level (low, medium, high, critical)
			requires_approval: Whether this tool always requires approval
			description: Human-readable description
		"""
		ToolRouter._registry[name] = {
			"handler": handler,
			"schema": schema,
			"risk_level": risk_level,
			"requires_approval": requires_approval,
			"description": description
		}
	
	def get_tool(self, name: str) -> Optional[Dict]:
		"""Get tool definition by name."""
		return ToolRouter._registry.get(name)
	
	def get_tool_definitions(self) -> List[Dict]:
		"""
		Get all tool definitions in MCP format.
		
		Returns list of tool definitions for tools/list method.
		"""
		tools = []
		for name, tool in ToolRouter._registry.items():
			tools.append({
				"name": name,
				"description": tool["description"],
				"inputSchema": tool["schema"]
			})
		return tools
	
	def validate_arguments(self, tool_name: str, arguments: Dict) -> Dict:
		"""
		Validate arguments against tool schema.
		
		Returns:
			{"valid": True} or {"valid": False, "error": "message"}
		"""
		tool = self.get_tool(tool_name)
		if not tool:
			return {"valid": False, "error": f"Tool not found: {tool_name}"}
		
		schema = tool["schema"]
		required = schema.get("required", [])
		properties = schema.get("properties", {})
		
		# Check required fields
		for field in required:
			if field not in arguments:
				return {
					"valid": False,
					"error": f"Missing required field: {field}"
				}
		
		# Validate field types (basic validation)
		for field, value in arguments.items():
			if field in properties:
				prop = properties[field]
				expected_type = prop.get("type")
				
				if expected_type == "string" and not isinstance(value, str):
					return {
						"valid": False,
						"error": f"Field {field} must be a string"
					}
				elif expected_type == "number" and not isinstance(value, (int, float)):
					return {
						"valid": False,
						"error": f"Field {field} must be a number"
					}
				elif expected_type == "boolean" and not isinstance(value, bool):
					return {
						"valid": False,
						"error": f"Field {field} must be a boolean"
					}
				elif expected_type == "object" and not isinstance(value, dict):
					return {
						"valid": False,
						"error": f"Field {field} must be an object"
					}
				elif expected_type == "array" and not isinstance(value, list):
					return {
						"valid": False,
						"error": f"Field {field} must be an array"
					}
		
		return {"valid": True}
	
	def execute_tool(self, tool_name: str, arguments: Dict, user: str) -> Any:
		"""
		Execute a tool with the given arguments.
		
		Args:
			tool_name: Name of the tool to execute
			arguments: Tool arguments
			user: User executing the tool
			
		Returns:
			Tool execution result
		"""
		tool = self.get_tool(tool_name)
		if not tool:
			raise ValueError(f"Tool not found: {tool_name}")
		
		handler = tool["handler"]
		
		# Execute the handler
		return handler(**arguments)


def tool(
	name: str,
	schema: Dict,
	risk_level: str = "low",
	requires_approval: bool = False,
	description: str = ""
):
	"""
	Decorator to register a function as an MCP tool.
	
	Usage:
		@tool(
			name="doc.get",
			schema={
				"type": "object",
				"properties": {
					"doctype": {"type": "string"},
					"name": {"type": "string"}
				},
				"required": ["doctype", "name"]
			},
			risk_level="low",
			description="Get a document by name"
		)
		def doc_get(doctype: str, name: str) -> dict:
			...
	"""
	def decorator(func: Callable) -> Callable:
		@wraps(func)
		def wrapper(*args, **kwargs):
			return func(*args, **kwargs)
		
		# Register the tool
		router = ToolRouter()
		router.register_tool(
			name=name,
			handler=func,
			schema=schema,
			risk_level=risk_level,
			requires_approval=requires_approval,
			description=description or func.__doc__ or ""
		)
		
		return wrapper
	
	return decorator
