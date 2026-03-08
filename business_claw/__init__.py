# -*- coding: utf-8 -*-
"""
Business Claw - MCP Server for ERPNext

Enables AI assistants to interact with ERPNext data and business processes
in a controlled, audited, and safe manner.
"""

__version__ = "1.0.0"
__title__ = "Business Claw"
__author__ = "Business Claw Team"

app_name = "business_claw"
app_title = "Business Claw"
app_publisher = "Business Claw Team"
app_description = "MCP Server for ERPNext - AI Assistant Integration"
app_icon = "octicon octicon-beaker"
app_color = "grey"
app_email = "admin@businessclaw.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_js = "/assets/business_claw/js/business_claw.js"
# app_include_css = "/assets/business_claw/css/business_claw.css"

# include js, css files in header of web template
# web_include_js = "/assets/business_claw/js/business_claw.js"
# web_include_css = "/assets/business_claw/css/business_claw.css"

# include custom scss in every website theme
# website_theme_scss = "business_claw/public/scss/website.scss"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "business_claw.install.before_install"
# after_install = "business_claw.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "business_claw.uninstall.before_uninstall"
# after_uninstall = "business_claw.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "business_claw.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": ["business_claw.tasks.all"],
# 	"daily": ["business_claw.tasks.daily"],
# 	"hourly": ["business_claw.tasks.hourly"],
# 	"weekly": ["business_claw.tasks.weekly"],
# 	"monthly": ["business_claw.tasks.monthly"],
# }

# Testing
# -------

# before_tests = "business_claw.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "business_claw.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "business_claw.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["business_claw.utils.before_request"]
# after_request = ["business_claw.utils.after_request"]

# Job Events
# ----------
# before_job = ["business_claw.utils.before_job"]
# after_job = ["business_claw.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"business_claw.auth.validate"
# ]
