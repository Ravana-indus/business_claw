# -*- coding: utf-8 -*-
"""
Business Claw - Audit Logger

Logs all MCP actions for audit and compliance purposes.
"""

import frappe
import json
import hashlib
from typing import Dict, Optional, Any
from frappe import _
from frappe.utils import now_datetime, add_to_date


def log_action(
	tool_name: str,
	request_json: Dict,
	response_json: Dict,
	risk_level: str = "low",
	approval_required: bool = False,
	reference_doctype: str = None,
	reference_name: str = None,
	conversation_id: str = None
) -> str:
	"""
	Log an MCP action to the AI Action Log.
	
	Args:
		tool_name: Name of the tool executed
		request_json: Request arguments
		response_json: Response data
		risk_level: Risk level of the action
		approval_required: Whether approval was required
		reference_doctype: Related DocType
		reference_name: Related document name
		conversation_id: Optional conversation/session ID
		
	Returns:
		Name of the created log entry
	"""
	try:
		# Create hash of request/response for integrity
		request_hash = _compute_hash(request_json)
		response_hash = _compute_hash(response_json)
		
		# Truncate large JSON data
		request_str = _truncate_json(request_json)
		response_str = _truncate_json(response_json)
		
		# Determine execution status
		execution_status = "Executed"
		if response_json.get("status") == "approval_required":
			execution_status = "Pending"
		elif not response_json.get("success", True):
			execution_status = "Failed"
		
		# Create log entry
		doc = frappe.get_doc({
			"doctype": "AI Action Log",
			"user": frappe.session.user,
			"timestamp": now_datetime(),
			"conversation_id": conversation_id,
			"tool_name": tool_name,
			"request_hash": request_hash,
			"request_json": request_str,
			"response_hash": response_hash,
			"response_json": response_str,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"risk_level": risk_level,
			"approval_required": approval_required,
			"execution_status": execution_status,
			"error_message": response_json.get("error") if not response_json.get("success") else None
		})
		
		doc.insert(ignore_permissions=True)
		
		return doc.name
		
	except Exception as e:
		# Don't fail the main action if logging fails
		frappe.log_error(
			f"Failed to log MCP action: {str(e)}",
			"Business Claw Audit"
		)
		return None


def cleanup_old_logs(days: int = 90):
	"""
	Cleanup old action logs.
	
	Args:
		days: Number of days to keep logs (default: 90)
	"""
	try:
		cutoff_date = add_to_date(now_datetime(), days=-days)
		
		# Delete old logs
		frappe.db.delete(
			"AI Action Log",
			{"timestamp": ["<", cutoff_date]}
		)
		
		frappe.db.commit()
		
	except Exception as e:
		frappe.log_error(
			f"Failed to cleanup old logs: {str(e)}",
			"Business Claw Audit"
		)


def daily_summary():
	"""
	Generate daily summary of MCP actions.
	
	This is called by the scheduler.
	"""
	try:
		from frappe.utils import nowdate
		
		# Get today's stats
		stats = frappe.db.sql("""
			SELECT 
				tool_name,
				risk_level,
				execution_status,
				COUNT(*) as count
			FROM `tabAI Action Log`
			WHERE DATE(timestamp) = %s
			GROUP BY tool_name, risk_level, execution_status
			ORDER BY count DESC
		""", (nowdate(),), as_dict=True)
		
		# Get approval stats
		approval_stats = frappe.db.sql("""
			SELECT 
				status,
				COUNT(*) as count
			FROM `tabAI Approval Request`
			WHERE DATE(requested_at) = %s
			GROUP BY status
		""", (nowdate(),), as_dict=True)
		
		# Log summary
		frappe.log_error(
			f"Daily MCP Summary:\n"
			f"Actions: {json.dumps(stats, indent=2)}\n"
			f"Approvals: {json.dumps(approval_stats, indent=2)}",
			"Business Claw Daily Summary"
		)
		
	except Exception as e:
		frappe.log_error(
			f"Failed to generate daily summary: {str(e)}",
			"Business Claw Audit"
		)


def get_user_actions(user: str, limit: int = 50) -> list:
	"""
	Get recent actions for a user.
	
	Args:
		user: User to get actions for
		limit: Maximum number of actions to return
		
	Returns:
		List of action logs
	"""
	return frappe.get_list(
		"AI Action Log",
		filters={"user": user},
		fields=[
			"name", "timestamp", "tool_name", "risk_level",
			"reference_doctype", "reference_name", "execution_status"
		],
		order_by="timestamp desc",
		limit=limit
	)


def get_document_history(doctype: str, name: str, limit: int = 20) -> list:
	"""
	Get action history for a document.
	
	Args:
		doctype: DocType of the document
		name: Name of the document
		limit: Maximum number of actions to return
		
	Returns:
		List of action logs
	"""
	return frappe.get_list(
		"AI Action Log",
		filters={
			"reference_doctype": doctype,
			"reference_name": name
		},
		fields=[
			"name", "timestamp", "user", "tool_name", "risk_level",
			"execution_status", "approval_required"
		],
		order_by="timestamp desc",
		limit=limit
	)


def _compute_hash(data: Any) -> str:
	"""
	Compute SHA256 hash of data.
	
	Args:
		data: Data to hash
		
	Returns:
		Hex string of hash
	"""
	json_str = json.dumps(data, sort_keys=True, default=str)
	return hashlib.sha256(json_str.encode()).hexdigest()


def _truncate_json(data: Any, max_length: int = 10000) -> str:
	"""
	Truncate JSON string to max length.
	
	Args:
		data: Data to truncate
		max_length: Maximum length
		
	Returns:
		Truncated JSON string
	"""
	json_str = json.dumps(data, default=str)
	if len(json_str) > max_length:
		return json_str[:max_length] + "... [truncated]"
	return json_str
