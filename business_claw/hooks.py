# -*- coding: utf-8 -*-
"""
Business Claw - App Hooks

This file contains all the hooks for the Business Claw app.
Hooks are used to integrate with Frappe's core functionality.
"""

from . import __version__ as app_version

app_name = "business_claw"
app_title = "Business Claw"
app_publisher = "Business Claw Team"
app_description = "MCP Server for ERPNext - AI Assistant Integration"
app_icon = "octicon octicon-shield"
app_color = "#4A90D9"
app_email = "admin@businessclaw.com"
app_license = "MIT"

# Includes in <head>
# ------------------

app_include_js = "/assets/business_claw/js/business_claw.js"
app_include_css = "/assets/business_claw/css/business_claw.css"

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": [
		"business_claw.bc_audit.logger.cleanup_old_logs"
	],
	"daily": [
		"business_claw.bc_audit.logger.daily_summary"
	]
}

# Permission Query Conditions
# ---------------------------

permission_query_conditions = {}

has_permission = {}

# Authentication Hooks
# --------------------

auth_hooks = [
	"business_claw.bc_mcp.auth.validate_mcp_request"
]

# Whitelisted Methods
# --------------------
# MCP Server endpoint is whitelisted in the module

# Before Install
# --------------

before_install = "business_claw.install.before_install"

# After Install
# -------------

after_install = "business_claw.install.after_install"

# Fixtures
# -----------
# Load custom fixtures

fixtures = []

# API Rate Limiting
# -----------------

api_rate_limit = {
	"limit": 100,
	"window": 60
}
