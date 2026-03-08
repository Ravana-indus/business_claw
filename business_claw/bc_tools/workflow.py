# -*- coding: utf-8 -*-
"""
Business Claw - Workflow Tools

Tools for interacting with Frappe workflows.
"""

import frappe
from frappe import _
from typing import Dict, List, Optional
from ..bc_mcp.router import tool
from ..bc_mcp.response import create_document_result


@tool(
	name="workflow.get_state",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType of the document"
			},
			"name": {
				"type": "string",
				"description": "Name of the document"
			}
		},
		"required": ["doctype", "name"]
	},
	risk_level="low",
	description="Get the current workflow state of a document."
)
def workflow_get_state(doctype: str, name: str) -> Dict:
	"""
	Get current workflow state of a document.
	
	Returns the current state and available transitions.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	
	# Check if workflow exists
	workflow = frappe.db.get_value(
		"Workflow",
		{"document_type": doctype, "is_active": 1},
		"name"
	)
	
	if not workflow:
		return {
			"success": True,
			"data": {
				"has_workflow": False,
				"docstatus": doc.docstatus,
				"message": f"No active workflow for {doctype}"
			}
		}
	
	# Get workflow state field
	state_field = frappe.db.get_value("Workflow", workflow, "workflow_state_field")
	current_state = doc.get(state_field) if state_field else None
	
	# Get available transitions
	from frappe.model.workflow import get_transitions
	transitions = get_transitions(doc)
	
	return {
		"success": True,
		"data": {
			"has_workflow": True,
			"workflow_name": workflow,
			"state_field": state_field,
			"current_state": current_state,
			"docstatus": doc.docstatus,
			"available_transitions": [
				{
					"action": t.action,
					"next_state": t.next_state,
					"state": t.state
				}
				for t in transitions
			]
		}
	}


@tool(
	name="workflow.apply",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType of the document"
			},
			"name": {
				"type": "string",
				"description": "Name of the document"
			},
			"action": {
				"type": "string",
				"description": "Workflow action to apply (e.g., 'Approve', 'Reject')"
			}
		},
		"required": ["doctype", "name", "action"]
	},
	risk_level="high",
	description="Apply a workflow action to a document. REQUIRES APPROVAL for certain transitions."
)
def workflow_apply(doctype: str, name: str, action: str) -> Dict:
	"""
	Apply a workflow action.
	
	This may require approval depending on the transition.
	"""
	from frappe.model.workflow import apply_workflow
	
	doc = frappe.get_doc(doctype, name)
	
	# Check permission
	doc.check_permission("write")
	
	# Apply workflow action
	try:
		apply_workflow(doc, action)
		
		# Reload to get updated state
		doc.reload()
		
		return {
			"success": True,
			"doctype": doctype,
			"name": name,
			"action": action,
			"new_state": doc.get(
				frappe.db.get_value(
					"Workflow",
					{"document_type": doctype, "is_active": 1},
					"workflow_state_field"
				)
			),
			"docstatus": doc.docstatus,
			"message": f"Workflow action '{action}' applied successfully"
		}
	except Exception as e:
		return {
			"success": False,
			"error": str(e)
		}


@tool(
	name="workflow.get_transitions",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType of the document"
			},
			"name": {
				"type": "string",
				"description": "Name of the document"
			}
		},
		"required": ["doctype", "name"]
	},
	risk_level="low",
	description="Get available workflow transitions for a document."
)
def workflow_get_transitions(doctype: str, name: str) -> Dict:
	"""
	Get available workflow transitions.
	
	Returns list of actions the user can take on this document.
	"""
	from frappe.model.workflow import get_transitions
	
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	
	transitions = get_transitions(doc)
	
	return {
		"success": True,
		"data": [
			{
				"action": t.action,
				"next_state": t.next_state,
				"current_state": t.state,
				"allowed": t.allowed if hasattr(t, 'allowed') else None
			}
			for t in transitions
		]
	}
