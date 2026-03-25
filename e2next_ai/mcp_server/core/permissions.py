"""Permissions & safety layer for MCP tools.

- Reads current user's roles from ERPNext session
- Blocks access to restricted doctypes
- Checks has_permission() before queries
- Returns clean permission errors (never stack traces or raw SQL errors)
"""

from __future__ import annotations

import frappe

# Doctypes that must never be queried through MCP tools
BLOCKED_DOCTYPES = [
	"User",
	"Has Role",
	"Auth Token",
	"System Settings",
	"Data Import",
	"Data Import Log",
	"Scheduled Job Type",
	"Error Log",
	"Access Log",
	"Activity Log",
	"Version",
	"Comment",
	"Communication",
	"Email Account",
	"Email Domain",
	"OAuth Client",
	"OAuth Bearer Token",
	"Token Cache",
	"Integration Request",
]


def get_current_user() -> str:
	"""Return the current session user."""
	return frappe.session.user or "Guest"


def get_user_roles(user: str | None = None) -> list[str]:
	"""Return roles for the given user (or current session user)."""
	user = user or get_current_user()
	return frappe.get_roles(user)


def is_doctype_blocked(doctype: str) -> bool:
	"""Check if a doctype is in the blocked list."""
	return doctype in BLOCKED_DOCTYPES


def check_doctype_permission(doctype: str, ptype: str = "read", user: str | None = None) -> None:
	"""Check if the current user has permission on a doctype.

	Raises PermissionError with a clean message if denied.
	"""
	if is_doctype_blocked(doctype):
		raise PermissionError(f"Access to {doctype} is restricted for security reasons.")

	user = user or get_current_user()

	if not frappe.has_permission(doctype, ptype=ptype, user=user):
		raise PermissionError(f"You do not have {ptype} access to {doctype}.")


def check_document_permission(
	doctype: str, name: str, ptype: str = "read", user: str | None = None
) -> None:
	"""Check if the current user has permission on a specific document.

	Raises PermissionError with a clean message if denied.
	"""
	if is_doctype_blocked(doctype):
		raise PermissionError(f"Access to {doctype} is restricted for security reasons.")

	user = user or get_current_user()

	if not frappe.has_permission(doctype, ptype=ptype, doc=name, user=user):
		raise PermissionError(f"You do not have {ptype} access to {doctype} '{name}'.")


def safe_error(message: str | None = None) -> str:
	"""Return a user-friendly error message. Never expose internals."""
	return message or "Something went wrong. Please try again or rephrase your question."
