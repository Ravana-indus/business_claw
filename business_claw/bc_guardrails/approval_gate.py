# -*- coding: utf-8 -*-
"""
Business Claw - Approval Gate

Handles approval workflow for high-risk actions.
"""

import frappe
from typing import Dict, Optional
from frappe import _
from frappe.utils import now_datetime, add_to_date

from .risk_scorer import calculate_risk_level, get_approval_timeout


def requires_approval(tool_name: str, payload: Dict) -> bool:
	"""
	Check if a tool call requires approval.
	
	Args:
		tool_name: Name of the tool being called
		payload: The arguments passed to the tool
		
	Returns:
		True if approval is required
	"""
	risk_level = calculate_risk_level(tool_name, payload)
	return risk_level in ("high", "critical")


def create_approval_request(
	tool_name: str,
	arguments: Dict,
	user: str,
	summary: str
) -> Dict:
	"""
	Create an approval request for a high-risk action.
	
	Args:
		tool_name: Name of the tool to execute
		arguments: Tool arguments
		user: User requesting the action
		summary: Human-readable summary of the action
		
	Returns:
		The created approval request document
	"""
	import json
	
	risk_level = calculate_risk_level(tool_name, arguments)
	timeout_hours = get_approval_timeout(risk_level)
	
	# Create approval request
	doc = frappe.get_doc({
		"doctype": "AI Approval Request",
		"status": "Pending",
		"requested_by": user,
		"requested_at": now_datetime(),
		"tool_name": tool_name,
		"action_summary": summary,
		"payload": json.dumps(arguments, default=str),
		"risk_level": risk_level,
		"expires_at": add_to_date(now_datetime(), hours=timeout_hours),
		"linked_doctype": arguments.get("doctype"),
		"linked_docname": arguments.get("name")
	})
	doc.insert(ignore_permissions=True)
	
	# Notify approvers
	_notify_approvers(doc)
	
	return {
		"name": doc.name,
		"status": doc.status,
		"risk_level": risk_level,
		"expires_at": doc.expires_at
	}


def approve_request(approval_request: str, approver: str) -> Dict:
	"""
	Approve an approval request.
	
	Args:
		approval_request: Name of the approval request
		approver: User approving the request
		
	Returns:
		Result dict with execution status
	"""
	doc = frappe.get_doc("AI Approval Request", approval_request)
	
	# Check if already processed
	if doc.status != "Pending":
		return {
			"success": False,
			"error": f"Approval request already {doc.status.lower()}"
		}
	
	# Check if expired
	if doc.expires_at and now_datetime() > doc.expires_at:
		doc.status = "Expired"
		doc.save()
		return {
			"success": False,
			"error": "Approval request has expired"
		}
	
	# Check if approver has permission
	if not _can_approve(approver, doc):
		return {
			"success": False,
			"error": "You don't have permission to approve this request"
		}
	
	# Update approval request
	doc.status = "Approved"
	doc.approved_by = approver
	doc.approved_at = now_datetime()
	doc.save()
	
	# Execute the action
	result = _execute_approved_action(doc)
	
	return {
		"success": True,
		"approval_request": approval_request,
		"executed": result.get("success", False),
		"result": result
	}


def reject_request(approval_request: str, rejector: str, reason: str) -> Dict:
	"""
	Reject an approval request.
	
	Args:
		approval_request: Name of the approval request
		rejector: User rejecting the request
		reason: Reason for rejection
		
	Returns:
		Result dict
	"""
	doc = frappe.get_doc("AI Approval Request", approval_request)
	
	# Check if already processed
	if doc.status != "Pending":
		return {
			"success": False,
			"error": f"Approval request already {doc.status.lower()}"
		}
	
	# Check if rejector has permission
	if not _can_approve(rejector, doc):
		return {
			"success": False,
			"error": "You don't have permission to reject this request"
		}
	
	# Update approval request
	doc.status = "Rejected"
	doc.approved_by = rejector
	doc.approved_at = now_datetime()
	doc.rejection_reason = reason
	doc.save()
	
	return {
		"success": True,
		"approval_request": approval_request,
		"status": "rejected"
	}


def _can_approve(user: str, approval_request) -> bool:
	"""
	Check if a user can approve a request.
	
	Args:
		user: User to check
		approval_request: Approval request document
		
	Returns:
		True if user can approve
	"""
	# User who requested cannot approve their own request
	if user == approval_request.requested_by:
		return False
	
	# Check for specific approver roles
	approver_roles = frappe.db.get_single_value(
		"Business Claw Settings",
		"approver_roles"
	)
	
	if approver_roles:
		roles = [r.strip() for r in approver_roles.split(",")]
		user_roles = frappe.get_roles(user)
		return any(role in user_roles for role in roles)
	
	# Default: System Managers can approve
	return "System Manager" in frappe.get_roles(user)


def _notify_approvers(approval_request):
	"""
	Notify potential approvers about a new approval request.
	
	Args:
		approval_request: The approval request document
	"""
	try:
		# Get approvers
		approvers = _get_approvers()
		
		if not approvers:
			return
		
		# Create notification
		for approver in approvers:
			if approver != approval_request.requested_by:
				frappe.get_doc({
					"doctype": "Notification Log",
					"for_user": approver,
					"type": "Alert",
					"document_type": "AI Approval Request",
					"document_name": approval_request.name,
					"subject": f"AI Action Approval Required: {approval_request.action_summary}",
					"email_content": f"""
						<p>An AI assistant has requested approval for the following action:</p>
						<p><strong>Action:</strong> {approval_request.tool_name}</p>
						<p><strong>Summary:</strong> {approval_request.action_summary}</p>
						<p><strong>Risk Level:</strong> {approval_request.risk_level}</p>
						<p><strong>Requested By:</strong> {approval_request.requested_by}</p>
						<p>Please review and approve or reject this request.</p>
					"""
				}).insert(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(f"Failed to notify approvers: {str(e)}", "Business Claw")


def _get_approvers() -> list:
	"""
	Get list of users who can approve requests.
	
	Returns:
		List of user emails
	"""
	# Get approver roles from settings
	approver_roles = frappe.db.get_single_value(
		"Business Claw Settings",
		"approver_roles"
	)
	
	if approver_roles:
		roles = [r.strip() for r in approver_roles.split(",")]
	else:
		roles = ["System Manager"]
	
	# Get users with these roles
	approvers = []
	for role in roles:
		users = frappe.db.get_list(
			"Has Role",
			filters={"role": role, "parenttype": "User"},
			fields=["parent"]
		)
		approvers.extend([u.parent for u in users])
	
	return list(set(approvers))


def _execute_approved_action(approval_request) -> Dict:
	"""
	Execute an approved action.
	
	Args:
		approval_request: The approval request document
		
	Returns:
		Execution result
	"""
	import json
	from ..bc_mcp.router import ToolRouter
	
	try:
		router = ToolRouter()
		arguments = json.loads(approval_request.payload)
		
		result = router.execute_tool(
			approval_request.tool_name,
			arguments,
			approval_request.requested_by
		)
		
		# Update action log if exists
		if approval_request.action_log:
			frappe.db.set_value(
				"AI Action Log",
				approval_request.action_log,
				{
					"execution_status": "Executed",
					"approved_by": approval_request.approved_by
				}
			)
		
		return {"success": True, "result": result}
		
	except Exception as e:
		frappe.log_error(
			f"Failed to execute approved action: {str(e)}",
			"Business Claw"
		)
		
		# Update action log if exists
		if approval_request.action_log:
			frappe.db.set_value(
				"AI Action Log",
				approval_request.action_log,
				{
					"execution_status": "Failed",
					"error_message": str(e)
				}
			)
		
		return {"success": False, "error": str(e)}
