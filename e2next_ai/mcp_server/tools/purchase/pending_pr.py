"""pending_pr — Purchase Receipts not yet billed (unbilled GRN).

Maps to ERPNext report: Received Items To Be Billed.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class PendingPRTool(MCPTool):
	name = "pending_pr"
	description = (
		"Get Purchase Receipts not yet billed (unbilled GRN). "
		"Shows GRN number, supplier, amount, receipt date, and days unbilled."
	)
	parameters = {
		"company": {"type": "str", "required": False},
		"supplier": {"type": "str", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Purchase Receipt")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		supplier = kwargs.get("supplier")

		conditions = [
			"pr.docstatus = 1",
			"pr.status != 'Closed'",
			"pr.per_billed < 100",
		]
		values: list[Any] = []

		if company:
			conditions.append("pr.company = %s")
			values.append(company)
		if supplier:
			conditions.append("pr.supplier = %s")
			values.append(supplier)

		where = " AND ".join(conditions)

		rows = frappe.db.sql(
			f"""
			SELECT
				pr.name AS grn_number,
				pr.supplier,
				pr.supplier_name,
				pr.grand_total,
				pr.posting_date AS receipt_date,
				pr.per_billed,
				pr.status
			FROM `tabPurchase Receipt` pr
			WHERE {where}
			ORDER BY pr.posting_date ASC
			LIMIT 100
			""",
			tuple(values),
			as_dict=True,
		)

		today = date.today()
		table = []
		for r in rows:
			receipt_date = r.receipt_date
			days_unbilled = (today - receipt_date).days if receipt_date else 0
			table.append({
				"grn_number": r.grn_number,
				"supplier": r.supplier,
				"supplier_name": r.supplier_name or "",
				"grand_total": float(r.grand_total),
				"receipt_date": str(receipt_date),
				"pct_billed": float(r.per_billed or 0),
				"days_unbilled": days_unbilled,
				"status": r.status,
			})

		total_amount = sum(r["grand_total"] for r in table)
		data = serialize({"total_unbilled": len(table), "total_amount": total_amount, "receipts": table})

		if table:
			summary = (
				f"{format_number(len(table))} Purchase Receipts not yet fully billed, "
				f"worth {format_currency(total_amount)}. "
				f"Oldest unbilled: {table[0]['days_unbilled']} days."
			)
		else:
			summary = "All Purchase Receipts have been billed."

		return {"data": data, "summary": summary, "table": table[:20]}
