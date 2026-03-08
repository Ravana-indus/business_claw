# -*- coding: utf-8 -*-
"""
Business Claw - Document Tools

Generic CRUD tools for documents with permission checks and guardrails.
"""

import json
import frappe
from frappe import _
from typing import Dict, List, Optional, Any
from ..bc_mcp.router import tool
from ..bc_mcp.response import create_document_result, create_list_result


def _parse_child_tables(data: Dict) -> Dict:
    """
    Parse any string fields that contain JSON arrays (for child tables).
    
    This handles the case where child table data is passed as JSON strings
    instead of actual arrays (which can happen when data comes from external APIs).
    """
    parsed_data = {}
    
    for key, value in data.items():
        if isinstance(value, str) and value.startswith('['):
            # Try to parse as JSON array
            try:
                parsed_value = json.loads(value)
                # Only use it if it's actually a list
                if isinstance(parsed_value, list):
                    parsed_data[key] = parsed_value
                    continue
            except json.JSONDecodeError:
                pass
        
        if isinstance(value, dict):
            # Recursively parse nested dicts
            parsed_data[key] = _parse_child_tables(value)
        else:
            parsed_data[key] = value
    
    return parsed_data


# ============================================================================
# Read Tools
# ============================================================================

@tool(
	name="doc.get",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType of the document"
			},
			"name": {
				"type": "string",
				"description": "Name/ID of the document"
			}
		},
		"required": ["doctype", "name"]
	},
	risk_level="low",
	description="Get a single document by name. Returns full document data."
)
def doc_get(doctype: str, name: str) -> Dict:
	"""
	Get a single document by name.
	
	Returns the document with all fields, respecting field-level permissions.
	"""
	# Get document
	doc = frappe.get_doc(doctype, name)
	
	# Check read permission
	doc.check_permission("read")
	
	# Apply field-level read permissions
	doc.apply_fieldlevel_read_permissions()
	
	return {
		"success": True,
		"data": doc.as_dict()
	}


@tool(
	name="doc.list",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType to list"
			},
			"filters": {
				"type": "object",
				"description": "Filter conditions (e.g., {'status': 'Open'})"
			},
			"fields": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Fields to return (default: name and title)"
			},
			"order_by": {
				"type": "string",
				"description": "Sort order (e.g., 'creation desc')"
			},
			"limit": {
				"type": "integer",
				"description": "Maximum number of results (default: 20, max: 100)"
			},
			"offset": {
				"type": "integer",
				"description": "Offset for pagination"
			}
		},
		"required": ["doctype"]
	},
	risk_level="low",
	description="List documents with optional filters, fields, and pagination."
)
def doc_list(
	doctype: str,
	filters: Optional[Dict] = None,
	fields: Optional[List[str]] = None,
	order_by: str = "creation desc",
	limit: int = 20,
	offset: int = 0
) -> Dict:
	"""
	List documents with filters and pagination.
	
	Returns a paginated list of documents.
	"""
	# Enforce limit
	limit = min(limit, 100)
	
	# Default fields
	if not fields:
		fields = ["name"]
		# Try to get title field
		meta = frappe.get_meta(doctype)
		if meta.title_field:
			fields.append(meta.title_field)
	
	# Get total count
	total_count = frappe.db.count(doctype, filters=filters)
	
	# Get documents
	docs = frappe.get_list(
		doctype,
		filters=filters,
		fields=fields,
		order_by=order_by,
		limit_start=offset,
		limit_page_length=limit
	)
	
	return create_list_result(docs, total_count, (offset // limit) + 1 if limit > 0 else 1, limit)


@tool(
	name="doc.search",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType to search in"
			},
			"text": {
				"type": "string",
				"description": "Search text"
			},
			"fields": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Fields to search in (default: name and title)"
			},
			"limit": {
				"type": "integer",
				"description": "Maximum results (default: 20)"
			}
		},
		"required": ["doctype", "text"]
	},
	risk_level="low",
	description="Search for documents by text in specified fields."
)
def doc_search(
	doctype: str,
	text: str,
	fields: Optional[List[str]] = None,
	limit: int = 20
) -> Dict:
	"""
	Search for documents by text.
	
	Performs a text search across specified fields.
	"""
	limit = min(limit, 100)
	
	# Default search fields
	if not fields:
		fields = ["name"]
		meta = frappe.get_meta(doctype)
		if meta.title_field:
			fields.append(meta.title_field)
	
	# Build search filters
	search_filters = []
	for field in fields:
		search_filters.append([doctype, field, "like", f"%{text}%"])
	
	# Use or_filters for any match
	docs = frappe.get_list(
		doctype,
		or_filters=search_filters,
		fields=fields,
		limit=limit
	)
	
	return {
		"success": True,
		"data": docs,
		"query": text,
		"fields_searched": fields
	}


@tool(
	name="doc.get_children",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "Parent DocType"
			},
			"name": {
				"type": "string",
				"description": "Parent document name"
			},
			"child_field": {
				"type": "string",
				"description": "Child table fieldname"
			}
		},
		"required": ["doctype", "name", "child_field"]
	},
	risk_level="low",
	description="Get child table rows from a document."
)
def doc_get_children(doctype: str, name: str, child_field: str) -> Dict:
	"""
	Get child table rows from a document.
	
	Returns all rows from the specified child table field.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	
	if not hasattr(doc, child_field):
		return {
			"success": False,
			"error": f"No field '{child_field}' in {doctype}"
		}
	
	children = doc.get(child_field)
	
	return {
		"success": True,
		"data": [child.as_dict() for child in children],
		"count": len(children)
	}


@tool(
	name="doc.get_linked",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "Source DocType"
			},
			"name": {
				"type": "string",
				"description": "Source document name"
			},
			"link_doctype": {
				"type": "string",
				"description": "Target DocType to find links to"
			},
			"limit": {
				"type": "integer",
				"description": "Maximum results (default: 20)"
			}
		},
		"required": ["doctype", "name", "link_doctype"]
	},
	risk_level="low",
	description="Get documents linked to a specific document."
)
def doc_get_linked(
	doctype: str,
	name: str,
	link_doctype: str,
	limit: int = 20
) -> Dict:
	"""
	Get documents linked to a specific document.
	
	Finds all documents of link_doctype that reference this document.
	"""
	limit = min(limit, 100)
	
	# Find link fields from link_doctype to doctype
	meta = frappe.get_meta(link_doctype)
	link_fields = []
	
	for field in meta.fields:
		if field.fieldtype == "Link" and field.options == doctype:
			link_fields.append(field.fieldname)
	
	if not link_fields:
		return {
			"success": True,
			"data": [],
			"message": f"No link fields from {link_doctype} to {doctype}"
		}
	
	# Build filters
	or_filters = []
	for fieldname in link_fields:
		or_filters.append([link_doctype, fieldname, "=", name])
	
	docs = frappe.get_list(
		link_doctype,
		or_filters=or_filters,
		fields=["name"],
		limit=limit
	)
	
	return {
		"success": True,
		"data": docs,
		"link_fields": link_fields
	}


# ============================================================================
# Create / Update Tools
# ============================================================================

@tool(
	name="doc.create",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType to create"
			},
			"data": {
				"type": "object",
				"description": "Document data (field: value pairs)"
			},
			"submit": {
				"type": "boolean",
				"description": "Submit after creation (requires approval)"
			}
		},
		"required": ["doctype", "data"]
	},
	risk_level="medium",
	description="Create a new document. Optionally submit if submittable DocType."
)
def doc_create(doctype: str, data: Dict, submit: bool = False) -> Dict:
	"""
	Create a new document.
	
	Creates a draft document. If submit=True, will require approval.
	
	Supports child tables - if child table data is passed as JSON strings,
	they will be automatically parsed.
	"""
	# Parse any JSON string fields (for child tables)
	parsed_data = _parse_child_tables(data)
	
	# Create document
	doc = frappe.get_doc({"doctype": doctype, **parsed_data})
	
	# Check create permission
	doc.check_permission("create")
	
	# Insert as draft
	doc.insert()
	
	result = create_document_result(doc.as_dict(), "created")
	
	# Handle submit if requested
	if submit and doc.meta.is_submittable:
		result["submit_requested"] = True
		result["message"] = f"{doctype} {doc.name} created as draft. Submit requires approval."
	
	return result


@tool(
	name="doc.update",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType of document to update"
			},
			"name": {
				"type": "string",
				"description": "Name of document to update"
			},
			"data": {
				"type": "object",
				"description": "Fields to update (field: value pairs)"
			}
		},
		"required": ["doctype", "name", "data"]
	},
	risk_level="medium",
	description="Update an existing document. Only works on draft documents."
)
def doc_update(doctype: str, name: str, data: Dict) -> Dict:
	"""
	Update an existing document.
	
	Only works on draft (docstatus=0) documents.
	"""
	doc = frappe.get_doc(doctype, name)
	
	# Check write permission
	doc.check_permission("write")
	
	# Check if document is draft
	if doc.docstatus != 0:
		return {
			"success": False,
			"error": "Can only update draft documents",
			"docstatus": doc.docstatus
		}
	
	# Update fields
	doc.update(data)
	doc.save()
	
	return create_document_result(doc.as_dict(), "updated")


@tool(
	name="doc.upsert",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType"
			},
			"key_fields": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Fields to use for finding existing document"
			},
			"data": {
				"type": "object",
				"description": "Document data"
			}
		},
		"required": ["doctype", "key_fields", "data"]
	},
	risk_level="medium",
	description="Create or update a document based on key fields."
)
def doc_upsert(doctype: str, key_fields: List[str], data: Dict) -> Dict:
	"""
	Create or update a document.
	
	Uses key_fields to find existing document. Creates if not found.
	"""
	# Build filters from key fields
	filters = {}
	for field in key_fields:
		if field in data:
			filters[field] = data[field]
	
	if not filters:
		return {
			"success": False,
			"error": "No key field values provided"
		}
	
	# Check if document exists
	existing = frappe.db.get_value(doctype, filters, "name")
	
	if existing:
		# Update existing
		return doc_update(doctype, existing, data)
	else:
		# Create new
		return doc_create(doctype, data)


# ============================================================================
# Submit / Cancel / Delete Tools (High Risk - Approval Gated)
# ============================================================================

@tool(
	name="doc.submit",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType of document to submit"
			},
			"name": {
				"type": "string",
				"description": "Name of document to submit"
			}
		},
		"required": ["doctype", "name"]
	},
	risk_level="high",
	description="Submit a document. REQUIRES APPROVAL. Only works on draft documents."
)
def doc_submit(doctype: str, name: str) -> Dict:
	"""
	Submit a document.
	
	This is a high-risk action that requires approval.
	"""
	doc = frappe.get_doc(doctype, name)
	
	# Check submit permission
	doc.check_permission("submit")
	
	# Check if document is draft
	if doc.docstatus != 0:
		return {
			"success": False,
			"error": "Can only submit draft documents",
			"docstatus": doc.docstatus
		}
	
	# Submit
	doc.submit()
	
	return create_document_result(doc.as_dict(), "submitted")


@tool(
	name="doc.cancel",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType of document to cancel"
			},
			"name": {
				"type": "string",
				"description": "Name of document to cancel"
			}
		},
		"required": ["doctype", "name"]
	},
	risk_level="high",
	description="Cancel a submitted document. REQUIRES APPROVAL."
)
def doc_cancel(doctype: str, name: str) -> Dict:
	"""
	Cancel a submitted document.
	
	This is a high-risk action that requires approval.
	"""
	doc = frappe.get_doc(doctype, name)
	
	# Check cancel permission
	doc.check_permission("cancel")
	
	# Check if document is submitted
	if doc.docstatus != 1:
		return {
			"success": False,
			"error": "Can only cancel submitted documents",
			"docstatus": doc.docstatus
		}
	
	# Cancel
	doc.cancel()
	
	return create_document_result(doc.as_dict(), "cancelled")


@tool(
	name="doc.delete",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType of document to delete"
			},
			"name": {
				"type": "string",
				"description": "Name of document to delete"
			}
		},
		"required": ["doctype", "name"]
	},
	risk_level="high",
	description="Delete a document. REQUIRES APPROVAL. Only works on draft documents."
)
def doc_delete(doctype: str, name: str) -> Dict:
	"""
	Delete a document.
	
	This is a high-risk action that requires approval.
	"""
	doc = frappe.get_doc(doctype, name)
	
	# Check delete permission
	doc.check_permission("delete")
	
	# Check if document is draft
	if doc.docstatus != 0:
		return {
			"success": False,
			"error": "Can only delete draft documents",
			"docstatus": doc.docstatus
		}
	
	# Delete
	doc.delete()
	
	return {
		"success": True,
		"doctype": doctype,
		"name": name,
		"action": "deleted",
		"message": f"{doctype} {name} deleted successfully"
	}
