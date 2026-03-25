"""top_suppliers — Rank suppliers by spend, outstanding, or order count.

Maps to ERPNext report: Supplier-wise Purchase Summary.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


_RANK_MAP = {
	"spend": "total_spend", "total_spend": "total_spend", "amount": "total_spend",
	"outstanding": "outstanding", "outstanding_amount": "outstanding", "due": "outstanding",
	"orders": "invoice_count", "order_count": "invoice_count", "count": "invoice_count",
}


class TopSuppliersTool(MCPTool):
	name = "top_suppliers"
	description = "Get top suppliers ranked by spend, outstanding, or order count."
	parameters = {
		"company": {"type": "str", "required": False},
		"from_date": {"type": "str", "required": False},
		"to_date": {"type": "str", "required": False},
		"rank_by": {"type": "str", "required": False, "description": "spend, outstanding, or order_count"},
		"limit": {"type": "int", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Purchase Invoice")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		rank_by = _RANK_MAP.get((kwargs.get("rank_by") or "spend").strip().lower(), "total_spend")
		limit = int(kwargs.get("limit") or 10)

		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		conditions = ["pi.docstatus = 1"]
		values: list[Any] = []

		if from_date and to_date:
			conditions.append("pi.posting_date BETWEEN %s AND %s")
			values.extend([from_date, to_date])
		if company:
			conditions.append("pi.company = %s")
			values.append(company)

		where = " AND ".join(conditions)

		rows = frappe.db.sql(
			f"""
			SELECT
				pi.supplier,
				pi.supplier_name,
				SUM(pi.grand_total) AS total_spend,
				SUM(pi.outstanding_amount) AS outstanding,
				COUNT(*) AS invoice_count
			FROM `tabPurchase Invoice` pi
			WHERE {where}
			GROUP BY pi.supplier, pi.supplier_name
			ORDER BY {rank_by} DESC
			LIMIT %s
			""",
			(*values, limit),
			as_dict=True,
		)

		table = [{
			"supplier": r.supplier,
			"supplier_name": r.supplier_name or "",
			"total_spend": float(r.total_spend),
			"outstanding": float(r.outstanding),
			"invoice_count": int(r.invoice_count),
		} for r in rows]

		data = serialize({"rank_by": rank_by, "total_results": len(table), "suppliers": table})

		if table:
			t = table[0]
			summary = f"Top {len(table)} suppliers by {rank_by}. #1: {t['supplier_name']} — {format_currency(t['total_spend'])}."
		else:
			summary = "No supplier data found for the given filters."

		return {"data": data, "summary": summary, "table": table}
