"""pending_po — Open Purchase Orders not yet fully received.

Maps to ERPNext report: Purchase Order Trends.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class PendingPOTool(MCPTool):
	name = "pending_po"
	description = (
		"Get open Purchase Orders not yet fully received. "
		"Shows PO number, supplier, amount, expected date, and % received."
	)
	parameters = {
		"company": {"type": "str", "required": False},
		"supplier": {"type": "str", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Purchase Order")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		supplier = kwargs.get("supplier")

		conditions = ["po.docstatus = 1", "po.status NOT IN ('Completed', 'Closed', 'Cancelled')"]
		values: list[Any] = []

		if company:
			conditions.append("po.company = %s")
			values.append(company)
		if supplier:
			conditions.append("po.supplier = %s")
			values.append(supplier)

		where = " AND ".join(conditions)

		rows = frappe.db.sql(
			f"""
			SELECT
				po.name AS po_number,
				po.supplier,
				po.supplier_name,
				po.grand_total,
				po.status,
				po.transaction_date,
				po.schedule_date AS expected_date,
				po.per_received
			FROM `tabPurchase Order` po
			WHERE {where}
			ORDER BY po.schedule_date ASC
			LIMIT 100
			""",
			tuple(values),
			as_dict=True,
		)

		table = [{
			"po_number": r.po_number,
			"supplier": r.supplier,
			"supplier_name": r.supplier_name or "",
			"grand_total": float(r.grand_total),
			"status": r.status,
			"transaction_date": str(r.transaction_date),
			"expected_date": str(r.expected_date) if r.expected_date else "",
			"pct_received": float(r.per_received or 0),
		} for r in rows]

		total_amount = sum(r["grand_total"] for r in table)
		data = serialize({"total_pending": len(table), "total_amount": total_amount, "orders": table})

		if table:
			summary = (
				f"{format_number(len(table))} pending Purchase Orders worth {format_currency(total_amount)}. "
				f"Earliest expected: {table[0]['expected_date']}."
			)
		else:
			summary = "No pending Purchase Orders found."

		return {"data": data, "summary": summary, "table": table[:20]}
