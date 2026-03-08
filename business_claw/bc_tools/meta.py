# -*- coding: utf-8 -*-
"""
Business Claw - Meta Tools

DocType introspection and schema discovery tools.
"""

import frappe
from frappe import _
from typing import Dict, List, Optional
from ..bc_mcp.router import tool


# ============================================================================
# Meta/Schema Tools
# ============================================================================

@tool(
	name="meta.list_doctypes",
	schema={
		"type": "object",
		"properties": {
			"module": {
				"type": "string",
				"description": "Filter by module name (e.g., 'Accounts', 'Stock')"
			},
			"searchable_only": {
				"type": "boolean",
				"description": "Only return searchable DocTypes (default: true)"
			}
		},
		"required": []
	},
	risk_level="low",
	description="List available DocTypes, optionally filtered by module."
)
def list_doctypes(module: str = None, searchable_only: bool = True) -> Dict:
	"""
	List available DocTypes.
	
	Returns a list of DocTypes the user has permission to access.
	"""
	filters = {"issingle": 0}
	
	if module:
		filters["module"] = module
	
	if searchable_only:
		filters["istable"] = 0
	
	doctypes = frappe.get_list(
		"DocType",
		filters=filters,
		fields=["name", "module", "description"],
		order_by="module, name",
		limit=500
	)
	
	# Group by module
	grouped = {}
	for dt in doctypes:
		mod = dt.module
		if mod not in grouped:
			grouped[mod] = []
		grouped[mod].append({
			"name": dt.name,
			"description": dt.description
		})
	
	return {
		"success": True,
		"data": grouped,
		"total_count": len(doctypes)
	}


@tool(
	name="meta.get_doctype",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType name to get schema for"
			}
		},
		"required": ["doctype"]
	},
	risk_level="low",
	description="Get detailed schema information for a DocType including fields, links, and permissions."
)
def get_doctype(doctype: str) -> Dict:
	"""
	Get DocType schema and metadata.
	
	Returns fields, field types, links, naming rules, and permission summary.
	"""
	# Check permission
	if not frappe.has_permission(doctype, "read"):
		return {
			"success": False,
			"error": f"No permission to read {doctype}"
		}
	
	meta = frappe.get_meta(doctype)
	
	# Extract field information
	fields = []
	for field in meta.fields:
		field_info = {
			"fieldname": field.fieldname,
			"label": field.label,
			"fieldtype": field.fieldtype,
			"reqd": field.reqd,
			"read_only": field.read_only,
			"hidden": field.hidden,
			"default": field.default,
			"description": field.description
		}
		
		# Add link options for Link fields
		if field.fieldtype == "Link":
			field_info["options"] = field.options
		elif field.fieldtype == "Select":
			field_info["options"] = field.options.split("\n") if field.options else []
		
		fields.append(field_info)
	
	# Extract links to other DocTypes
	links = []
	for field in meta.fields:
		if field.fieldtype == "Link" and field.options:
			links.append({
				"fieldname": field.fieldname,
				"label": field.label,
				"links_to": field.options
			})
		elif field.fieldtype == "Dynamic Link":
			links.append({
				"fieldname": field.fieldname,
				"label": field.label,
				"dynamic": True
			})
	
	# Get permission summary
	permissions = []
	for perm in meta.permissions:
		permissions.append({
			"role": perm.role,
			"read": perm.permlevel_read if hasattr(perm, 'permlevel_read') else perm.read,
			"write": perm.permlevel_write if hasattr(perm, 'permlevel_write') else perm.write,
			"create": perm.create,
			"submit": perm.submit,
			"cancel": perm.cancel,
			"delete": perm.delete
		})
	
	return {
		"success": True,
		"data": {
			"name": doctype,
			"module": meta.module,
			"istable": meta.istable,
			"issingle": meta.issingle,
			"is_submittable": meta.is_submittable,
			"naming_series": meta.autoname,
			"title_field": meta.title_field,
			"fields": fields,
			"links": links,
			"permissions": permissions
		}
	}


@tool(
	name="meta.get_workflow",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType to get workflow for"
			}
		},
		"required": ["doctype"]
	},
	risk_level="low",
	description="Get workflow states and transitions for a DocType if configured."
)
def get_workflow(doctype: str) -> Dict:
	"""
	Get workflow configuration for a DocType.
	
	Returns states, transitions, and approval requirements.
	"""
	# Check if workflow is active for this DocType
	workflow = frappe.db.get_value(
		"Workflow",
		{"document_type": doctype, "is_active": 1},
		["name", "workflow_state_field"],
		as_dict=True
	)
	
	if not workflow:
		return {
			"success": True,
			"data": None,
			"message": f"No active workflow for {doctype}"
		}
	
	# Get states
	states = frappe.get_list(
		"Workflow Document State",
		filters={"parent": workflow.name},
		fields=["state", "doc_status", "update_field", "update_value"],
		order_by="idx"
	)
	
	# Get transitions
	transitions = frappe.get_list(
		"Workflow Transition",
		filters={"parent": workflow.name},
		fields=["state", "next_state", "action", "allowed", "condition"],
		order_by="idx"
	)
	
	return {
		"success": True,
		"data": {
			"workflow_name": workflow.name,
			"state_field": workflow.workflow_state_field,
			"states": states,
			"transitions": transitions
		}
	}


@tool(
	name="meta.get_print_formats",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType to get print formats for"
			}
		},
		"required": ["doctype"]
	},
	risk_level="low",
	description="Get available print formats for a DocType."
)
def get_print_formats(doctype: str) -> Dict:
	"""
	Get print formats for a DocType.
	
	Returns list of available print formats.
	"""
	print_formats = frappe.get_list(
		"Print Format",
		filters={"doc_type": doctype},
		fields=["name", "standard"],
		order_by="name"
	)
	
	# Add Standard format
	print_formats.insert(0, {"name": "Standard", "standard": "Yes"})
	
	return {
		"success": True,
		"data": print_formats
	}


@tool(
	name="meta.get_reports",
	schema={
		"type": "object",
		"properties": {
			"module": {
				"type": "string",
				"description": "Filter by module name"
			}
		},
		"required": []
	},
	risk_level="low",
	description="Get available reports, optionally filtered by module."
)
def get_reports(module: str = None) -> Dict:
	"""
	Get available reports.
	
	Returns list of reports the user can access.
	"""
	filters = {"disabled": 0}
	
	if module:
		filters["module"] = module
	
	reports = frappe.get_list(
		"Report",
		filters=filters,
		fields=["name", "report_type", "module", "ref_doctype"],
		order_by="module, name",
		limit=200
	)
	
	# Group by module
	grouped = {}
	for report in reports:
		mod = report.module
		if mod not in grouped:
			grouped[mod] = []
		grouped[mod].append({
			"name": report.name,
			"type": report.report_type,
			"doctype": report.ref_doctype
		})
	
	return {
		"success": True,
		"data": grouped,
		"total_count": len(reports)
	}
