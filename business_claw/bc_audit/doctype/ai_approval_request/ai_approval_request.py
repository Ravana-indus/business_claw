# -*- coding: utf-8 -*-
# Copyright (c) 2024, Business Claw Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class AIApprovalRequest(Document):
	"""
	AI Approval Request DocType
	
	Manages approval workflow for high-risk AI actions.
	"""
	
	def validate(self):
		"""Validate the approval request."""
		if self.status == "Pending" and self.expires_at:
			if now_datetime() > self.expires_at:
				self.status = "Expired"
	
	def on_update(self):
		"""Handle status changes."""
		if self.has_value_changed("status"):
			if self.status == "Approved":
				self._on_approval()
			elif self.status == "Rejected":
				self._on_rejection()
	
	def _on_approval(self):
		"""Handle approval."""
		# Notify requester
		self._notify_requester(
			subject=f"AI Action Approved: {self.tool_name}",
			message=f"Your request to {self.action_summary} has been approved."
		)
	
	def _on_rejection(self):
		"""Handle rejection."""
		# Notify requester
		reason = f" Reason: {self.rejection_reason}" if self.rejection_reason else ""
		self._notify_requester(
			subject=f"AI Action Rejected: {self.tool_name}",
			message=f"Your request to {self.action_summary} has been rejected.{reason}"
		)
	
	def _notify_requester(self, subject: str, message: str):
		"""Notify the requester."""
		try:
			frappe.get_doc({
				"doctype": "Notification Log",
				"for_user": self.requested_by,
				"type": "Alert",
				"document_type": "AI Approval Request",
				"document_name": self.name,
				"subject": subject,
				"email_content": f"<p>{message}</p>"
			}).insert(ignore_permissions=True)
		except Exception:
			pass
	
	@frappe.whitelist()
	def approve(self, approver: str = None):
		"""
		Approve this request.
		
		Args:
			approver: User approving (defaults to current user)
		"""
		if self.status != "Pending":
			frappe.throw(_("Can only approve pending requests"))
		
		self.status = "Approved"
		self.approved_by = approver or frappe.session.user
		self.approved_at = now_datetime()
		self.save()
		
		return {"success": True, "message": "Request approved"}
	
	@frappe.whitelist()
	def reject(self, reason: str, rejector: str = None):
		"""
		Reject this request.
		
		Args:
			reason: Reason for rejection
			rejector: User rejecting (defaults to current user)
		"""
		if self.status != "Pending":
			frappe.throw(_("Can only reject pending requests"))
		
		self.status = "Rejected"
		self.approved_by = rejector or frappe.session.user
		self.approved_at = now_datetime()
		self.rejection_reason = reason
		self.save()
		
		return {"success": True, "message": "Request rejected"}
