# -*- coding: utf-8 -*-
"""
Business Claw - Installation

Installation hooks for the Business Claw app.
"""

import frappe
from frappe import _


def before_install():
	"""
	Runs before app installation.
	
	Checks prerequisites and prepares for installation.
	"""
	frappe.logger().info("Installing Business Claw - MCP Server for ERPNext")
	
	# Check Frappe version
	frappe_version = frappe.__version__
	frappe.logger().info(f"Frappe version: {frappe_version}")
	
	return True


def after_install():
	"""
	Runs after app installation.
	
	Creates default records and configurations.
	"""
	# Create default Business Claw Settings
	create_business_claw_settings()
	
	# Create AI API Key DocType if needed
	create_ai_api_key_doctype()
	
	frappe.logger().info("Business Claw installed successfully")


def create_business_claw_settings():
	"""
	Create default Business Claw Settings.
	"""
	if not frappe.db.exists("DocType", "Business Claw Settings"):
		return
	
	if not frappe.db.exists("Business Claw Settings", "Business Claw Settings"):
		doc = frappe.new_doc("Business Claw Settings")
		doc.approver_roles = "System Manager"
		doc.log_retention_days = 90
		doc.max_request_size = 10000
		doc.enable_rate_limiting = 1
		doc.rate_limit = 100
		doc.rate_limit_window = 60
		doc.save()


def create_ai_api_key_doctype():
	"""
	Create AI API Key DocType for API key management.
	"""
	if frappe.db.exists("DocType", "AI API Key"):
		return
	
	doc = frappe.new_doc("DocType")
	doc.name = "AI API Key"
	doc.module = "bc_audit"
	doc.custom = 1
	
	# Append fields as child documents
	doc.append("fields", {
		"fieldname": "user",
		"fieldtype": "Link",
		"label": "User",
		"options": "User",
		"reqd": 1
	})
	
	doc.append("fields", {
		"fieldname": "api_key",
		"fieldtype": "Data",
		"label": "API Key",
		"reqd": 1,
		"unique": 1
	})
	
	doc.append("fields", {
		"fieldname": "api_secret",
		"fieldtype": "Password",
		"label": "API Secret",
		"reqd": 1
	})
	
	doc.append("fields", {
		"fieldname": "description",
		"fieldtype": "Data",
		"label": "Description"
	})
	
	doc.append("fields", {
		"fieldname": "enabled",
		"fieldtype": "Check",
		"label": "Enabled",
		"default": 1
	})
	
	doc.append("fields", {
		"fieldname": "last_used",
		"fieldtype": "Datetime",
		"label": "Last Used",
		"read_only": 1
	})
	
	# Append permissions as child documents
	doc.append("permissions", {
		"role": "System Manager",
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1
	})
	
	doc.insert()
