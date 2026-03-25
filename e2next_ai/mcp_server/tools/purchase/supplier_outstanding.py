"""supplier_outstanding — Payable ageing by supplier.

Maps to ERPNext report: Accounts Payable.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class SupplierOutstandingTool(MCPTool):
	name = "supplier_outstanding"
	description = (
		"Get payable ageing by supplier with buckets: 0-30, 31-60, 61-90, 90+ days."
	)
	parameters = {
		"company": {"type": "str", "required": False},
		"supplier": {"type": "str", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Purchase Invoice")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		supplier = kwargs.get("supplier")

		conditions = ["pi.docstatus = 1", "pi.outstanding_amount > 0"]
		values: list[Any] = []

		if company:
			conditions.append("pi.company = %s")
			values.append(company)
		if supplier:
			conditions.append("pi.supplier = %s")
			values.append(supplier)

		where = " AND ".join(conditions)

		rows = frappe.db.sql(
			f"""
			SELECT
				pi.supplier,
				pi.supplier_name,
				SUM(pi.outstanding_amount) AS total_outstanding,
				SUM(CASE WHEN DATEDIFF(CURDATE(), pi.posting_date) <= 30 THEN pi.outstanding_amount ELSE 0 END) AS bucket_0_30,
				SUM(CASE WHEN DATEDIFF(CURDATE(), pi.posting_date) BETWEEN 31 AND 60 THEN pi.outstanding_amount ELSE 0 END) AS bucket_31_60,
				SUM(CASE WHEN DATEDIFF(CURDATE(), pi.posting_date) BETWEEN 61 AND 90 THEN pi.outstanding_amount ELSE 0 END) AS bucket_61_90,
				SUM(CASE WHEN DATEDIFF(CURDATE(), pi.posting_date) > 90 THEN pi.outstanding_amount ELSE 0 END) AS bucket_90_plus,
				COUNT(*) AS invoice_count
			FROM `tabPurchase Invoice` pi
			WHERE {where}
			GROUP BY pi.supplier, pi.supplier_name
			ORDER BY total_outstanding DESC
			LIMIT 50
			""",
			tuple(values),
			as_dict=True,
		)

		table = [{
			"supplier": r.supplier,
			"supplier_name": r.supplier_name or "",
			"total_outstanding": float(r.total_outstanding),
			"0_30_days": float(r.bucket_0_30),
			"31_60_days": float(r.bucket_31_60),
			"61_90_days": float(r.bucket_61_90),
			"90_plus_days": float(r.bucket_90_plus),
			"invoice_count": int(r.invoice_count),
		} for r in rows]

		grand_total = sum(r["total_outstanding"] for r in table)
		data = serialize({
			"total_suppliers": len(table),
			"grand_total_outstanding": grand_total,
			"suppliers": table,
		})

		if table:
			summary = (
				f"{format_number(len(table))} suppliers with outstanding payables totalling {format_currency(grand_total)}. "
				f"Largest: {table[0]['supplier_name']} ({format_currency(table[0]['total_outstanding'])})."
			)
		else:
			summary = "No outstanding supplier payables found."

		return {"data": data, "summary": summary, "table": table[:20]}
