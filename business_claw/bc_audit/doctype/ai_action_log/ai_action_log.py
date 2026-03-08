# -*- coding: utf-8 -*-
# Copyright (c) 2024, Business Claw Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class AIActionLog(Document):
	"""
	AI Action Log DocType
	
	Records all MCP tool calls for audit and compliance.
	"""
	
	def before_insert(self):
		"""Set default values before insert."""
		if not self.timestamp:
			self.timestamp = frappe.utils.now_datetime()
		
		if not self.user:
			self.user = frappe.session.user
	
	def after_insert(self):
		"""Actions after insert."""
		# Notify if high risk
		if self.risk_level in ("High", "Critical"):
			self._notify_admins()
	
	def _notify_admins(self):
		"""Notify administrators of high-risk actions."""
		try:
			# Get system managers
			admins = frappe.db.get_list(
				"Has Role",
				filters={"role": "System Manager", "parenttype": "User"},
				fields=["parent"]
			)
			
			for admin in admins:
				if admin.parent != self.user:
					frappe.get_doc({
						"doctype": "Notification Log",
						"for_user": admin.parent,
						"type": "Alert",
						"document_type": "AI Action Log",
						"document_name": self.name,
						"subject": f"High Risk AI Action: {self.tool_name}",
						"email_content": f"""
							<p>A high-risk AI action was performed:</p>
							<p><strong>Tool:</strong> {self.tool_name}</p>
							<p><strong>User:</strong> {self.user}</p>
							<p><strong>Risk Level:</strong> {self.risk_level}</p>
							<p><strong>Reference:</strong> {self.reference_doctype} {self.reference_name}</p>
						"""
					}).insert(ignore_permissions=True)
		except Exception:
			pass  # Don't fail if notification fails
