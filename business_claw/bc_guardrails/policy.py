# -*- coding: utf-8 -*-
"""
Business Claw - Policy Engine

Central policy engine that coordinates denylist, risk scoring, and approval gates.
"""

import frappe
from typing import Dict, Any
from frappe import _

from .denylist import is_doctype_allowed, is_readonly_doctype
from .risk_scorer import calculate_risk_level, get_risk_description
from .approval_gate import requires_approval, create_approval_request


class PolicyEngine:
	"""
	Central policy engine for MCP operations.
	
	Coordinates:
	- DocType denylist checks
	- Risk level calculation
	- Approval requirements
	- Permission validation
	"""
	
	def check_tool_allowed(
		self,
		tool_name: str,
		arguments: Dict,
		user: str
	) -> Dict[str, Any]:
		"""
		Check if a tool call is allowed.
		
		Args:
			tool_name: Name of the tool
			arguments: Tool arguments
			user: User making the request
			
		Returns:
			Dict with:
			- allowed: bool
			- reason: str (if not allowed)
			- risk_level: str
			- requires_approval: bool
			- summary: str (if requires approval)
		"""
		# Extract doctype from arguments
		doctype = arguments.get("doctype")
		
		# Check denylist
		if doctype and not is_doctype_allowed(doctype):
			return {
				"allowed": False,
				"reason": f"Access to DocType '{doctype}' is not allowed via MCP",
				"risk_level": "critical"
			}
		
		# Check readonly doctypes
		if doctype and is_readonly_doctype(doctype):
			if tool_name not in self._get_readonly_tools():
				return {
					"allowed": False,
					"reason": f"DocType '{doctype}' is read-only via MCP",
					"risk_level": "high"
				}
		
		# Calculate risk level
		risk_level = calculate_risk_level(tool_name, arguments)
		
		# Check if approval is required
		needs_approval = requires_approval(tool_name, arguments)
		
		# Generate summary for approval
		summary = ""
		if needs_approval:
			summary = self._generate_summary(tool_name, arguments)
		
		return {
			"allowed": True,
			"risk_level": risk_level,
			"risk_description": get_risk_description(risk_level),
			"requires_approval": needs_approval,
			"summary": summary
		}
	
	def create_approval_request(
		self,
		tool_name: str,
		arguments: Dict,
		user: str,
		summary: str
	) -> Dict:
		"""
		Create an approval request for a tool call.
		
		Args:
			tool_name: Name of the tool
			arguments: Tool arguments
			user: User making the request
			summary: Action summary
			
		Returns:
			Approval request details
		"""
		return create_approval_request(tool_name, arguments, user, summary)
	
	def _get_readonly_tools(self) -> list:
		"""Get list of tools that are read-only."""
		return [
			"doc.get",
			"doc.list",
			"doc.search",
			"doc.get_children",
			"doc.get_linked",
			"meta.list_doctypes",
			"meta.get_doctype",
			"meta.get_workflow",
			"meta.get_print_formats",
			"meta.get_reports",
			"workflow.get_state",
			"workflow.get_transitions",
			"file.list",
			"file.download",
			"system.ping",
			"system.get_capabilities",
			"system.get_current_user",
			"system.get_companies",
			"system.get_defaults"
		]
	
	def _generate_summary(self, tool_name: str, arguments: Dict) -> str:
		"""
		Generate a human-readable summary of the action.
		
		Args:
			tool_name: Name of the tool
			arguments: Tool arguments
			
		Returns:
			Summary string
		"""
		doctype = arguments.get("doctype", "document")
		name = arguments.get("name", "")
		action = tool_name.split(".")[-1] if "." in tool_name else tool_name
		
		# Build summary based on tool type
		if tool_name == "doc.submit":
			return f"Submit {doctype} {name}"
		elif tool_name == "doc.cancel":
			return f"Cancel {doctype} {name}"
		elif tool_name == "doc.delete":
			return f"Delete {doctype} {name}"
		elif tool_name == "workflow.apply":
			action_name = arguments.get("action", "unknown")
			return f"Apply workflow action '{action_name}' on {doctype} {name}"
		elif tool_name == "file.delete":
			return f"Delete file {arguments.get('file_url', '')}"
		else:
			return f"{action.capitalize()} {doctype} {name}"


def check_permission(doctype: str, perm_type: str, docname: str = None) -> Dict:
	"""
	Check if user has permission on a DocType.
	
	Args:
		doctype: DocType to check
		perm_type: Permission type (read, write, create, submit, cancel, delete)
		docname: Optional document name for document-level check
		
	Returns:
		Dict with allowed and reason
	"""
	if not frappe.has_permission(doctype, perm_type, doc=docname):
		return {
			"allowed": False,
			"reason": f"User lacks {perm_type} permission on {doctype}"
		}
	
	return {"allowed": True}


def get_policy_summary() -> Dict:
	"""
	Get a summary of current policies.
	
	Returns:
		Dict with policy information
	"""
	from .denylist import get_denylist, get_readonly_doctypes
	
	return {
		"denylist_count": len(get_denylist()),
		"readonly_count": len(get_readonly_doctypes()),
		"approval_threshold": 10000,
		"risk_levels": ["low", "medium", "high", "critical"],
		"high_risk_actions": list(requires_approval.__globals__.get("HIGH_RISK_ACTIONS", set()))
	}
