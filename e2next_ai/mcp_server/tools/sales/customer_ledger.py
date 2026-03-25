"""customer_ledger — Get GL Entry ledger for a customer."""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class CustomerLedgerTool(MCPTool):
	name = "customer_ledger"
	description = "Get the general ledger entries (debit/credit) for a specific customer."
	parameters = {
		"customer_name": {"type": "str", "required": True, "description": "The Customer ID"},
		"limit": {"type": "int", "required": False, "description": "Max entries to return (default 50)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("GL Entry")

		customer_name = kwargs.get("customer_name")
		limit = int(kwargs.get("limit") or 50)

		if not customer_name:
			raise ValueError("customer_name is required")

		if not frappe.db.exists("Customer", customer_name):
			raise ValueError(f"Customer {customer_name!r} does not exist")

		entries = frappe.db.sql(
			"""
			SELECT
				posting_date, voucher_type, voucher_no,
				debit, credit, remarks
			FROM `tabGL Entry`
			WHERE party_type = 'Customer' AND party = %s AND is_cancelled = 0
			ORDER BY posting_date DESC, creation DESC
			LIMIT %s
			""",
			(customer_name, limit),
			as_dict=True,
		)

		table = []
		for e in entries:
			table.append({
				"posting_date": str(e.posting_date),
				"voucher_type": e.voucher_type,
				"voucher_no": e.voucher_no,
				"debit": float(e.debit),
				"credit": float(e.credit),
				"remarks": e.remarks or "",
			})

		data = serialize({
			"customer_name": customer_name,
			"total_entries": len(table),
			"entries": table,
		})

		summary = f"{customer_name}: {format_number(len(table))} ledger entries returned."

		return {"data": data, "summary": summary, "table": table}
