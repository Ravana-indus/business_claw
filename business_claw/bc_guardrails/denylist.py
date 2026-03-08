# -*- coding: utf-8 -*-
"""
Business Claw - DocType Denylist

Defines which DocTypes are restricted from AI operations.
"""

import frappe
from typing import List, Set


# Core denylist - DocTypes that are never accessible via MCP
DENYLIST: Set[str] = {
	# Security sensitive
	"User",
	"Role",
	"API Key",
	"AI API Key",
	"Auth Log",
	"Access Log",
	"Error Log",
	"Activity Log",
	
	# Payroll sensitive
	"Salary Slip",
	"Salary Structure",
	"Salary Structure Assignment",
	"Payroll Entry",
	"Payroll Employee Detail",
	"Salary Component",
	
	# PII protection
	"Employee",
	"Employee Attendance Tool",
	
	# Financial integrity
	"GL Entry",
	"Payment Ledger Entry",
	"Stock Ledger Entry",
	"Serial No",
	"Batch",
	
	# System tables
	"Singles",
	"DocType",
	"DocField",
	"DocPerm",
	"Custom Field",
	"Property Setter",
	
	# Configuration
	"System Settings",
	"Company",
	"Global Defaults",
	
	# Sessions
	"Session",
	"Sessions",
}

# DocTypes that require approval even for read
APPROVAL_REQUIRED_READ: Set[str] = {
	# Add DocTypes that need approval for reading
}

# DocTypes that are read-only via MCP
READONLY_ALLOWLIST: Set[str] = {
	# These can be read but not modified
	"Account",
	"Cost Center",
	"Finance Book",
	"Warehouse",
	"Item Group",
	"Customer Group",
	"Supplier Group",
	"Territory",
	"Sales Partner",
	"Sales Person",
}


def is_doctype_allowed(doctype: str) -> bool:
	"""
	Check if a DocType is allowed for MCP operations.
	
	Args:
		doctype: The DocType name to check
		
	Returns:
		True if allowed, False if denied
	"""
	return doctype not in DENYLIST


def assert_doctype_allowed(doctype: str):
	"""
	Assert that a DocType is allowed for MCP operations.
	
	Args:
		doctype: The DocType name to check
		
	Raises:
		frappe.PermissionError: If DocType is not allowed
	"""
	if not is_doctype_allowed(doctype):
		frappe.throw(
			f"Access to DocType '{doctype}' is not allowed via MCP",
			frappe.PermissionError
		)


def is_readonly_doctype(doctype: str) -> bool:
	"""
	Check if a DocType is read-only via MCP.
	
	Args:
		doctype: The DocType name to check
		
	Returns:
		True if read-only, False if write allowed
	"""
	return doctype in READONLY_ALLOWLIST


def get_denylist() -> List[str]:
	"""
	Get the list of denied DocTypes.
	
	Returns:
		List of denied DocType names
	"""
	return list(DENYLIST)


def get_readonly_doctypes() -> List[str]:
	"""
	Get the list of read-only DocTypes.
	
	Returns:
		List of read-only DocType names
	"""
	return list(READONLY_ALLOWLIST)


def add_to_denylist(doctype: str):
	"""
	Add a DocType to the denylist at runtime.
	
	Args:
		doctype: DocType to add
	"""
	DENYLIST.add(doctype)


def remove_from_denylist(doctype: str):
	"""
	Remove a DocType from the denylist at runtime.
	
	Args:
		doctype: DocType to remove
	"""
	DENYLIST.discard(doctype)
