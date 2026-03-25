"""Fallback SQL handler — runs when no tool matches a data question.

- Whitelists allowed tables for safety
- Logs every fallback to MCP Query Log
- Returns answer with a note: "(Answered via fallback — tool coming soon)"
"""

from __future__ import annotations

import re
import time
from typing import Any

import frappe

from e2next_ai.mcp_server.core.permissions import BLOCKED_DOCTYPES, check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize

# Tables allowed for fallback queries (doctype names → tab table names)
ALLOWED_TABLES = [
	"Sales Invoice",
	"Sales Invoice Item",
	"Sales Order",
	"Sales Order Item",
	"Purchase Invoice",
	"Purchase Invoice Item",
	"Purchase Order",
	"Purchase Order Item",
	"Purchase Receipt",
	"Purchase Receipt Item",
	"Delivery Note",
	"Delivery Note Item",
	"Stock Entry",
	"Stock Entry Detail",
	"Stock Ledger Entry",
	"Bin",
	"Item",
	"Item Price",
	"Customer",
	"Supplier",
	"Employee",
	"Attendance",
	"Leave Application",
	"Salary Slip",
	"Salary Detail",
	"Work Order",
	"BOM",
	"Material Request",
	"Material Request Item",
	"GL Entry",
	"Payment Entry",
	"Journal Entry",
	"Quotation",
	"Quotation Item",
	"Company",
	"Warehouse",
	"Fiscal Year",
]

# Pre-compute the set of tab-prefixed table names for quick lookup
_ALLOWED_TAB_TABLES = {f"tab{t}" for t in ALLOWED_TABLES}
_ALLOWED_BACKTICK_TABLES = {f"`tab{t}`" for t in ALLOWED_TABLES}


def is_query_safe(sql: str) -> tuple[bool, str]:
	"""Validate that a SQL query only touches allowed tables and is read-only.

	Returns (is_safe, reason).
	"""
	sql_upper = sql.strip().upper()

	# Must be a SELECT
	if not sql_upper.startswith("SELECT"):
		return False, "Only SELECT queries are allowed."

	# Block dangerous keywords
	dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"]
	for kw in dangerous:
		if re.search(rf"\b{kw}\b", sql_upper):
			return False, f"{kw} operations are not allowed."

	# Extract table names from query
	# Match patterns like `tabXxx`, tabXxx, FROM tabXxx, JOIN tabXxx
	table_matches = re.findall(r"`?(tab[A-Za-z][A-Za-z ]*?)`?(?:\s|$|,|\))", sql)
	# Also check for blocked doctypes referenced directly
	for dt in BLOCKED_DOCTYPES:
		tab_name = f"tab{dt}"
		if tab_name.lower() in sql.lower():
			return False, f"Access to {dt} is restricted."

	for table in table_matches:
		table_clean = table.strip()
		if table_clean not in _ALLOWED_TAB_TABLES:
			# Check with backticks removed
			if f"`{table_clean}`" not in _ALLOWED_BACKTICK_TABLES:
				return False, f"Table '{table_clean}' is not in the allowed list."

	# LIMIT check — enforce a max
	if "LIMIT" not in sql_upper:
		return False, "Query must include a LIMIT clause (max 100 rows)."

	# Check limit value
	limit_match = re.search(r"LIMIT\s+(\d+)", sql_upper)
	if limit_match and int(limit_match.group(1)) > 100:
		return False, "LIMIT must be 100 or less."

	return True, ""


def run_fallback_query(sql: str, values: tuple | None = None) -> dict[str, Any]:
	"""Execute a safe fallback SQL query.

	Returns the standard tool response envelope.
	"""
	start = time.perf_counter()

	# Validate query safety
	safe, reason = is_query_safe(sql)
	if not safe:
		return {
			"status": "error",
			"tool": "fallback_sql",
			"query_time_ms": 0,
			"error": reason,
			"error_type": "validation",
		}

	# Check permissions on referenced doctypes
	table_matches = re.findall(r"`?tab([A-Za-z][A-Za-z ]*?)`?(?:\s|$|,|\))", sql)
	for doctype in table_matches:
		doctype = doctype.strip()
		if doctype in [t for t in ALLOWED_TABLES]:
			try:
				check_doctype_permission(doctype)
			except PermissionError as e:
				return {
					"status": "error",
					"tool": "fallback_sql",
					"query_time_ms": 0,
					"error": str(e),
					"error_type": "permission",
				}

	try:
		rows = frappe.db.sql(sql, values=values, as_dict=True)
		elapsed_ms = round((time.perf_counter() - start) * 1000)

		data = serialize(rows)

		return {
			"status": "success",
			"tool": "fallback_sql",
			"query_time_ms": elapsed_ms,
			"data": {"rows": data, "row_count": len(data)},
			"summary": f"Found {len(data)} rows. (Answered via fallback — tool coming soon)",
			"_query_source": sql,
			"_fallback": True,
		}

	except Exception:
		elapsed_ms = round((time.perf_counter() - start) * 1000)
		return {
			"status": "error",
			"tool": "fallback_sql",
			"query_time_ms": elapsed_ms,
			"error": "Query could not be executed. Please try rephrasing your question.",
			"error_type": "internal",
		}
