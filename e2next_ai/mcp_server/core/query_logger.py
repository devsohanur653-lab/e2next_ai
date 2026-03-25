"""Query logger — writes to MCP Query Log doctype.

Auto-inserts on every unmatched / fallback query for review.
"""

from __future__ import annotations

from typing import Any

import frappe


def log_query(
	question: str,
	detected_module: str | None = None,
	detected_metric: str | None = None,
	tool_matched: bool = False,
	fallback_used: bool = False,
	fallback_query: str | None = None,
	answer_given: str | None = None,
	response_time_ms: int = 0,
) -> str | None:
	"""Log a query to MCP Query Log doctype.

	Returns the log name if successful, None on failure.
	"""
	try:
		doc = frappe.get_doc(
			{
				"doctype": "MCP Query Log",
				"question": question,
				"detected_module": detected_module or "",
				"detected_metric": detected_metric or "",
				"tool_matched": 1 if tool_matched else 0,
				"fallback_used": 1 if fallback_used else 0,
				"fallback_query": fallback_query or "",
				"answer_given": (answer_given or "")[:65535],  # truncate if very long
				"response_time_ms": response_time_ms,
				"user": frappe.session.user or "Guest",
				"timestamp": frappe.utils.now_datetime(),
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
		return doc.name
	except Exception:
		# Don't let logging failures break the main flow
		frappe.log_error("MCP Query Log insert failed")
		return None


def log_tool_result(
	question: str,
	tool_result: dict[str, Any],
	detected_module: str | None = None,
	detected_metric: str | None = None,
) -> str | None:
	"""Convenience: log from a standard tool response envelope."""
	is_fallback = tool_result.get("_fallback", False)
	return log_query(
		question=question,
		detected_module=detected_module,
		detected_metric=detected_metric,
		tool_matched=tool_result.get("tool", "") != "fallback_sql",
		fallback_used=is_fallback,
		fallback_query=tool_result.get("_query_source", ""),
		answer_given=tool_result.get("summary", ""),
		response_time_ms=tool_result.get("query_time_ms", 0),
	)
