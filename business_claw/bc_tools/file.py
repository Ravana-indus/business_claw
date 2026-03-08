# -*- coding: utf-8 -*-
"""
Business Claw - File Tools

Tools for file operations - upload, list, download, delete.
"""

import frappe
from frappe import _
from typing import Dict, List, Optional
from ..bc_mcp.router import tool


@tool(
	name="file.upload",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType to attach file to"
			},
			"docname": {
				"type": "string",
				"description": "Document name to attach file to"
			},
			"filename": {
				"type": "string",
				"description": "Name of the file"
			},
			"content_base64": {
				"type": "string",
				"description": "Base64 encoded file content"
			},
			"is_private": {
				"type": "boolean",
				"description": "Make file private (default: true)"
			}
		},
		"required": ["doctype", "docname", "filename", "content_base64"]
	},
	risk_level="medium",
	description="Upload a file and attach it to a document."
)
def file_upload(
	doctype: str,
	docname: str,
	filename: str,
	content_base64: str,
	is_private: bool = True
) -> Dict:
	"""
	Upload a file and attach to a document.
	
	The file content must be base64 encoded.
	"""
	import base64
	
	# Check permission on parent document
	doc = frappe.get_doc(doctype, docname)
	doc.check_permission("write")
	
	# Decode base64 content
	try:
		content = base64.b64decode(content_base64)
	except Exception as e:
		return {
			"success": False,
			"error": f"Invalid base64 content: {str(e)}"
		}
	
	# Create file
	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": filename,
		"attached_to_doctype": doctype,
		"attached_to_name": docname,
		"is_private": is_private,
		"content": content
	})
	file_doc.insert()
	
	return {
		"success": True,
		"file_url": file_doc.file_url,
		"file_name": file_doc.name,
		"is_private": file_doc.is_private,
		"message": f"File '{filename}' uploaded successfully"
	}


@tool(
	name="file.list",
	schema={
		"type": "object",
		"properties": {
			"doctype": {
				"type": "string",
				"description": "DocType to list files for"
			},
			"docname": {
				"type": "string",
				"description": "Document name to list files for"
			}
		},
		"required": ["doctype", "docname"]
	},
	risk_level="low",
	description="List files attached to a document."
)
def file_list(doctype: str, docname: str) -> Dict:
	"""
	List files attached to a document.
	"""
	# Check permission on parent document
	doc = frappe.get_doc(doctype, docname)
	doc.check_permission("read")
	
	files = frappe.get_list(
		"File",
		filters={
			"attached_to_doctype": doctype,
			"attached_to_name": docname
		},
		fields=["name", "file_name", "file_url", "is_private", "file_size", "modified"],
		order_by="modified desc"
	)
	
	return {
		"success": True,
		"data": files,
		"count": len(files)
	}


@tool(
	name="file.download",
	schema={
		"type": "object",
		"properties": {
			"file_url": {
				"type": "string",
				"description": "URL of the file to download"
			}
		},
		"required": ["file_url"]
	},
	risk_level="low",
	description="Download a file. Returns base64 encoded content."
)
def file_download(file_url: str) -> Dict:
	"""
	Download a file.
	
	Returns the file content as base64 encoded string.
	"""
	import base64
	
	# Get file document
	file_doc = frappe.get_doc("File", {"file_url": file_url})
	
	# Check permission
	if file_doc.attached_to_doctype and file_doc.attached_to_name:
		doc = frappe.get_doc(file_doc.attached_to_doctype, file_doc.attached_to_name)
		doc.check_permission("read")
	elif not file_doc.is_private:
		# Public file - allow access
		pass
	else:
		# Private file without attachment - check if user has permission
		frappe.has_permission("File", "read", file_doc, throw=True)
	
	# Get file content
	content = file_doc.get_content()
	
	return {
		"success": True,
		"file_name": file_doc.file_name,
		"content_base64": base64.b64encode(content).decode("utf-8"),
		"file_size": len(content)
	}


@tool(
	name="file.delete",
	schema={
		"type": "object",
		"properties": {
			"file_url": {
				"type": "string",
				"description": "URL of the file to delete"
			}
		},
		"required": ["file_url"]
	},
	risk_level="high",
	description="Delete a file. REQUIRES APPROVAL."
)
def file_delete(file_url: str) -> Dict:
	"""
	Delete a file.
	
	This is a high-risk action that requires approval.
	"""
	# Get file document
	file_doc = frappe.get_doc("File", {"file_url": file_url})
	
	# Check permission
	if file_doc.attached_to_doctype and file_doc.attached_to_name:
		doc = frappe.get_doc(file_doc.attached_to_doctype, file_doc.attached_to_name)
		doc.check_permission("write")
	else:
		frappe.has_permission("File", "delete", file_doc, throw=True)
	
	# Delete file
	file_name = file_doc.file_name
	file_doc.delete()
	
	return {
		"success": True,
		"file_url": file_url,
		"message": f"File '{file_name}' deleted successfully"
	}
