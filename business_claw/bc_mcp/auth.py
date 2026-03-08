# -*- coding: utf-8 -*-
"""
Business Claw - Authentication

Handles authentication for MCP requests using API keys or OAuth tokens.
"""

import frappe
from typing import Optional
from frappe import _


def authenticate_request() -> Optional[str]:
	"""
	Authenticate an MCP request.
	
	Supports multiple authentication methods:
	1. API Key/Secret via headers (X-Business-Claw-Key, X-Business-Claw-Secret)
	2. API Key only via header (X-API-Key) - looks up secret in database
	3. Bearer token via Authorization header
	
	Returns:
		User email if authenticated, None otherwise
	"""
	# Try API Key/Secret authentication (preferred)
	api_key = frappe.get_request_header("X-Business-Claw-Key")
	api_secret = frappe.get_request_header("X-Business-Claw-Secret")
	
	if api_key and api_secret:
		return _authenticate_api_key(api_key, api_secret)
	
	# Try single API Key header (X-API-Key)
	single_api_key = frappe.get_request_header("X-API-Key")
	if single_api_key:
		return _authenticate_single_api_key(single_api_key)
	
	# Try Bearer token authentication
	auth_header = frappe.get_request_header("Authorization")
	if auth_header and auth_header.startswith("Bearer "):
		token = auth_header[7:]  # Remove "Bearer " prefix
		return _authenticate_bearer_token(token)
	
	# Try Frappe session (for web requests)
	if frappe.session.user and frappe.session.user != "Guest":
		return frappe.session.user
	
	return None


def _authenticate_api_key(api_key: str, api_secret: str) -> Optional[str]:
	"""
	Authenticate using API Key/Secret.
	
	Validates against AI API Key DocType.
	"""
	# Check if AI API Key DocType exists
	if not frappe.db.exists("DocType", "AI API Key"):
		# Fall back to standard Frappe API Key
		return _authenticate_frappe_api_key(api_key, api_secret)
	
	# Validate AI API Key
	api_key_doc = frappe.db.get_value(
		"AI API Key",
		{"api_key": api_key, "api_secret": api_secret, "enabled": 1},
		["user", "name"],
		as_dict=True
	)
	
	if api_key_doc:
		return api_key_doc.user
	
	return None


def _authenticate_single_api_key(api_key: str) -> Optional[str]:
	"""
	Authenticate using only API Key (without secret).
	
	Validates against AI API Key DocType.
	"""
	# Check if AI API Key DocType exists
	if not frappe.db.exists("DocType", "AI API Key"):
		return None
	
	# Validate AI API Key
	api_key_doc = frappe.db.get_value(
		"AI API Key",
		{"api_key": api_key, "enabled": 1},
		["user", "name"],
		as_dict=True
	)
	
	if api_key_doc:
		return api_key_doc.user
	
	return None


def _authenticate_frappe_api_key(api_key: str, api_secret: str) -> Optional[str]:
	"""
	Fallback to Frappe's standard API Key authentication.
	"""
	user = frappe.db.get_value("User", {"api_key": api_key}, "name")
	
	if user:
		user_doc = frappe.get_doc("User", user)
		if user_doc.api_secret == api_secret:
			return user
	
	return None


def _authenticate_bearer_token(token: str) -> Optional[str]:
	"""
	Authenticate using Bearer token (OAuth).
	
	Validates against Frappe's OAuth tokens.
	"""
	# Check if token is valid OAuth access token
	token_doc = frappe.db.get_value(
		"OAuth Bearer Token",
		{"access_token": token},
		["user", "expires_in", "creation"],
		as_dict=True
	)
	
	if token_doc:
		# Check if token is expired
		from frappe.utils import now_datetime, add_to_date
		
		expires_at = add_to_date(
			token_doc.creation,
			seconds=token_doc.expires_in
		)
		
		if now_datetime() < expires_at:
			return token_doc.user
	
	return None


def validate_mcp_request():
	"""
	Hook to validate MCP requests.
	
	This is called by Frappe's auth_hooks.
	"""
	# Check if this is an MCP endpoint request
	if frappe.local.request.path == "/api/method/business_claw.mcp.server.handle_request":
		user = authenticate_request()
		
		if not user:
			frappe.throw(
				_("Authentication required for MCP access"),
				frappe.AuthenticationError
			)


def create_api_key(user: str, description: str = "") -> dict:
	"""
	Create a new AI API Key for a user.
	
	Args:
		user: User email
		description: Description for the API key
		
	Returns:
		Dict with api_key and api_secret
	"""
	import secrets
	import hashlib
	
	# Generate API key and secret
	api_key = secrets.token_hex(16)
	api_secret = secrets.token_hex(32)
	
	# Check if AI API Key DocType exists
	if frappe.db.exists("DocType", "AI API Key"):
		doc = frappe.get_doc({
			"doctype": "AI API Key",
			"user": user,
			"api_key": api_key,
			"api_secret": api_secret,
			"description": description,
			"enabled": 1
		})
		doc.insert(ignore_permissions=True)
	else:
		# Fall back to User's API key
		user_doc = frappe.get_doc("User", user)
		user_doc.api_key = api_key
		user_doc.api_secret = api_secret
		user_doc.save(ignore_permissions=True)
	
	return {
		"api_key": api_key,
		"api_secret": api_secret
	}


def revoke_api_key(api_key: str) -> bool:
	"""
	Revoke an AI API Key.
	
	Args:
		api_key: The API key to revoke
		
	Returns:
		True if revoked, False if not found
	"""
	if frappe.db.exists("DocType", "AI API Key"):
		doc_name = frappe.db.get_value("AI API Key", {"api_key": api_key})
		if doc_name:
			frappe.db.set_value("AI API Key", doc_name, "enabled", 0)
			return True
	
	return False
