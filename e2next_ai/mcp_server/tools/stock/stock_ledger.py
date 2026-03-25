"""stock_ledger — Item movement IN/OUT with voucher type and date.

Maps to ERPNext report: Stock Ledger.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class StockLedgerTool(MCPTool):
	name = "stock_ledger"
	description = (
		"Get stock ledger entries showing item movements (IN/OUT) with "
		"voucher type, date, and running balance."
	)
	parameters = {
		"item_code": {"type": "str", "required": True, "description": "Item code to look up"},
		"warehouse": {"type": "str", "required": False, "description": "Filter by warehouse"},
		"from_date": {"type": "str", "required": False, "description": "Start date or natural language"},
		"to_date": {"type": "str", "required": False, "description": "End date"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Stock Ledger Entry")

		item_code = kwargs.get("item_code")
		warehouse = kwargs.get("warehouse")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")

		if not item_code:
			raise ValueError("item_code is required")

		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		conditions = ["sle.docstatus = 1", "sle.is_cancelled = 0", "sle.item_code = %s"]
		values: list[Any] = [item_code]

		if warehouse:
			conditions.append("sle.warehouse = %s")
			values.append(warehouse)

		if from_date and to_date:
			conditions.append("sle.posting_date BETWEEN %s AND %s")
			values.extend([from_date, to_date])

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				sle.posting_date,
				sle.voucher_type,
				sle.voucher_no,
				sle.warehouse,
				sle.actual_qty,
				sle.qty_after_transaction,
				sle.stock_value_difference,
				sle.stock_value
			FROM `tabStock Ledger Entry` sle
			WHERE {where}
			ORDER BY sle.posting_date DESC, sle.posting_time DESC
			LIMIT 100
		"""

		rows = frappe.db.sql(sql, tuple(values), as_dict=True)

		table = []
		total_in = 0.0
		total_out = 0.0
		for r in rows:
			qty = float(r.actual_qty)
			if qty > 0:
				total_in += qty
			else:
				total_out += abs(qty)
			table.append({
				"posting_date": str(r.posting_date),
				"voucher_type": r.voucher_type,
				"voucher_no": r.voucher_no,
				"warehouse": r.warehouse,
				"actual_qty": qty,
				"direction": "IN" if qty > 0 else "OUT",
				"qty_after_transaction": float(r.qty_after_transaction),
				"stock_value_difference": float(r.stock_value_difference or 0),
				"stock_value": float(r.stock_value or 0),
			})

		date_label = f" from {from_date} to {to_date}" if from_date and to_date else ""
		data = serialize({
			"item_code": item_code,
			"warehouse": warehouse or "All",
			"from_date": from_date or "",
			"to_date": to_date or "",
			"total_entries": len(table),
			"total_in": total_in,
			"total_out": total_out,
			"entries": table,
		})

		summary = (
			f"{item_code}{date_label}: "
			f"{format_number(len(table))} movements, "
			f"IN: {format_number(total_in)}, OUT: {format_number(total_out)}."
		)

		return {"data": data, "summary": summary, "table": table[:20]}
