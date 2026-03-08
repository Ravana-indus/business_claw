# -*- coding: utf-8 -*-
"""
Business Claw - System Tools

Foundation and system-level tools for health checks, capabilities, and user info.
"""

import frappe
from frappe import _
from typing import Dict, List
from ..bc_mcp.router import tool


# ============================================================================
# System Tools
# ============================================================================

@tool(
	name="system.ping",
	schema={
		"type": "object",
		"properties": {},
		"required": []
	},
	risk_level="low",
	description="Check if the MCP server is running and responsive. Returns server status and time."
)
def ping() -> Dict:
	"""
	Check if the MCP server is running.
	
	Returns server status, time, and version information.
	"""
	from frappe.utils import now_datetime
	
	return {
		"ok": True,
		"server_time": now_datetime().isoformat(),
		"version": "1.0.0",
		"frappe_version": frappe.__version__
	}


@tool(
	name="system.get_capabilities",
	schema={
		"type": "object",
		"properties": {},
		"required": []
	},
	risk_level="low",
	description="Get the capabilities and limits of this MCP server."
)
def get_capabilities() -> Dict:
	"""
	Get server capabilities and limits.
	
	Returns information about enabled modules, tools, and rate limits.
	"""
	from ..bc_mcp.router import ToolRouter
	
	router = ToolRouter()
	tools = router.get_tool_definitions()
	
	# Get installed apps
	installed_apps = frappe.get_installed_apps()
	
	# Check for ERPNext modules
	modules = []
	if "erpnext" in installed_apps:
		modules = [
			"accounts", "stock", "selling", "buying",
			"hr", "projects", "support", "crm", "manufacturing"
		]
	
	return {
		"server": "business-claw",
		"version": "1.0.0",
		"tools_count": len(tools),
		"modules": modules,
		"limits": {
			"max_list_results": 100,
			"max_bulk_create": 50,
			"request_timeout": 30
		},
		"installed_apps": installed_apps
	}


@tool(
	name="system.get_current_user",
	schema={
		"type": "object",
		"properties": {},
		"required": []
	},
	risk_level="low",
	description="Get information about the currently authenticated user."
)
def get_current_user() -> Dict:
	"""
	Get current user information.
	
	Returns user details, roles, and employee info if applicable.
	"""
	user = frappe.session.user
	
	user_doc = frappe.get_doc("User", user)
	
	# Get roles
	roles = [r.role for r in user_doc.roles]
	
	# Get employee if linked
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	
	# Get default company
	default_company = frappe.defaults.get_user_default("Company", user)
	
	return {
		"user": user,
		"full_name": user_doc.full_name,
		"email": user_doc.email,
		"roles": roles,
		"employee": employee,
		"company": default_company,
		"language": user_doc.language,
		"time_zone": user_doc.time_zone
	}


@tool(
	name="system.get_companies",
	schema={
		"type": "object",
		"properties": {},
		"required": []
	},
	risk_level="low",
	description="Get list of companies the user has access to."
)
def get_companies() -> List[Dict]:
	"""
	Get list of accessible companies.
	
	Returns companies the current user has permission to access.
	"""
	companies = frappe.get_list(
		"Company",
		fields=["name", "company_name", "abbr", "country", "default_currency"],
		limit=100
	)
	
	return {
		"success": True,
		"data": companies
	}


@tool(
	name="system.get_defaults",
	schema={
		"type": "object",
		"properties": {
			"company": {
				"type": "string",
				"description": "Company to get defaults for (optional)"
			}
		},
		"required": []
	},
	risk_level="low",
	description="Get ERP default settings like currency, fiscal year, etc."
)
def get_defaults(company: str = None) -> Dict:
	"""
	Get ERP default settings.
	
	Returns default currency, fiscal year, and other system defaults.
	"""
	from frappe.utils import now_datetime
	
	if not company:
		company = frappe.defaults.get_user_default("Company")
	
	defaults = {
		"company": company,
		"currency": frappe.defaults.get_user_default("Currency"),
		"country": frappe.db.get_value("Company", company, "country") if company else None,
		"fiscal_year": frappe.db.get_value("Fiscal Year", {
			"disabled": 0,
			"year_start_date": ("<=", now_datetime().date())
		}, "name"),
		"date_format": frappe.db.get_single_value("System Settings", "date_format"),
		"time_zone": frappe.db.get_single_value("System Settings", "time_zone")
	}
	
	return {
		"success": True,
		"data": defaults
	}
