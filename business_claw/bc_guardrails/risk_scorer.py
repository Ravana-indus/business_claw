# -*- coding: utf-8 -*-
"""
Business Claw - Risk Scorer

Calculates risk levels for tool calls based on action type and payload.
"""

from typing import Dict, Literal

RiskLevel = Literal["low", "medium", "high", "critical"]


# High-risk actions that always require approval
HIGH_RISK_ACTIONS = {
	"doc.submit",
	"doc.cancel",
	"doc.delete",
	"workflow.apply",
	"file.delete"
}

# Critical DocTypes for submit/cancel operations
CRITICAL_DOCTYPES = {
	"Payment Entry",
	"Journal Entry",
	"Stock Entry",
	"Purchase Invoice",
	"Sales Invoice"
}

# Amount threshold for approval (in company currency)
APPROVAL_AMOUNT_THRESHOLD = 10000


def calculate_risk_level(tool_name: str, payload: Dict) -> RiskLevel:
	"""
	Calculate the risk level for a tool call.
	
	Args:
		tool_name: Name of the tool being called
		payload: The arguments passed to the tool
		
	Returns:
		Risk level: "low", "medium", "high", or "critical"
	"""
	# Critical: Submit/cancel on financial documents
	if tool_name in ("doc.submit", "doc.cancel"):
		doctype = payload.get("doctype", "")
		if doctype in CRITICAL_DOCTYPES:
			return "critical"
		return "high"
	
	# High: Delete operations
	if tool_name == "doc.delete":
		return "high"
	
	# High: Workflow actions
	if tool_name == "workflow.apply":
		return "high"
	
	# High: File delete
	if tool_name == "file.delete":
		return "high"
	
	# Medium: Create/Update operations
	if tool_name in ("doc.create", "doc.update", "doc.upsert"):
		# Check for amount threshold
		data = payload.get("data", {})
		amount = _extract_amount(data)
		if amount and amount > APPROVAL_AMOUNT_THRESHOLD:
			return "high"
		return "medium"
	
	# Medium: File upload
	if tool_name == "file.upload":
		return "medium"
	
	# Low: Read operations
	return "low"


def _extract_amount(data: Dict) -> float:
	"""
	Extract monetary amount from document data.
	
	Args:
		data: Document data dict
		
	Returns:
		Amount as float, or 0 if not found
	"""
	amount_fields = [
		"grand_total",
		"total",
		"amount",
		"paid_amount",
		"total_amount"
	]
	
	for field in amount_fields:
		if field in data:
			try:
				return float(data[field])
			except (ValueError, TypeError):
				continue
	
	return 0


def get_risk_description(risk_level: RiskLevel) -> str:
	"""
	Get a human-readable description for a risk level.
	
	Args:
		risk_level: The risk level
		
	Returns:
		Description string
	"""
	descriptions = {
		"low": "Low risk - Read-only or informational operation",
		"medium": "Medium risk - Creates or modifies draft documents",
		"high": "High risk - Submits, cancels, or deletes documents",
		"critical": "Critical risk - Financial or irreversible operations"
	}
	return descriptions.get(risk_level, "Unknown risk level")


def should_notify_admin(risk_level: RiskLevel) -> bool:
	"""
	Check if admin should be notified for a risk level.
	
	Args:
		risk_level: The risk level
		
	Returns:
		True if admin should be notified
	"""
	return risk_level in ("high", "critical")


def get_approval_timeout(risk_level: RiskLevel) -> int:
	"""
	Get the timeout in hours for approval requests.
	
	Args:
		risk_level: The risk level
		
	Returns:
		Timeout in hours
	"""
	timeouts = {
		"low": 0,  # No approval needed
		"medium": 0,  # No approval needed
		"high": 24,  # 24 hours
		"critical": 48  # 48 hours
	}
	return timeouts.get(risk_level, 24)
