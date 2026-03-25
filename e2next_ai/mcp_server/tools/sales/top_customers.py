"""top_customers — Rank customers by revenue, outstanding, or order count.

Maps to ERPNext report: Customer-wise Sales Summary.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


# Normalize common prompt variants
_RANK_MAP = {
	"revenue": "revenue",
	"total_revenue": "revenue",
	"sales": "revenue",
	"total_sales": "revenue",
	"outstanding": "outstanding",
	"outstanding_amount": "outstanding",
	"due": "outstanding",
	"amount_due": "outstanding",
	"orders": "order_count",
	"order_count": "order_count",
	"invoices": "order_count",
	"invoice_count": "order_count",
	"count": "order_count",
}


class TopCustomersTool(MCPTool):
	name = "top_customers"
	description = (
		"Get top customers ranked by revenue, outstanding amount, or order count. "
		"Shows customer name, amount, invoice count, and last order date."
	)
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name"},
		"from_date": {"type": "str", "required": False, "description": "Start date (YYYY-MM-DD) or natural language"},
		"to_date": {"type": "str", "required": False, "description": "End date (YYYY-MM-DD)"},
		"rank_by": {"type": "str", "required": False, "description": "Ranking criteria: revenue, outstanding, or order_count (default revenue)"},
		"limit": {"type": "int", "required": False, "description": "Number of customers to return (default 10)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Sales Invoice")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		rank_by = _RANK_MAP.get((kwargs.get("rank_by") or "revenue").strip().lower(), "revenue")
		limit = int(kwargs.get("limit") or 10)

		# Parse natural language dates
		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		conditions = ["si.docstatus = 1"]
		values: list[Any] = []

		if from_date and to_date:
			conditions.append("si.posting_date BETWEEN %s AND %s")
			values.extend([from_date, to_date])

		if company:
			conditions.append("si.company = %s")
			values.append(company)

		where = " AND ".join(conditions)

		order_col = {
			"revenue": "total_revenue",
			"outstanding": "outstanding_amount",
			"order_count": "invoice_count",
		}[rank_by]

		sql = f"""
			SELECT
				si.customer AS customer_name,
				si.customer_name AS customer_label,
				SUM(si.grand_total) AS total_revenue,
				SUM(si.outstanding_amount) AS outstanding_amount,
				COUNT(*) AS invoice_count,
				MAX(si.posting_date) AS last_order_date
			FROM `tabSales Invoice` si
			WHERE {where}
			GROUP BY si.customer, si.customer_name
			ORDER BY {order_col} DESC
			LIMIT %s
		"""
		values.append(limit)

		rows = frappe.db.sql(sql, tuple(values), as_dict=True)

		table = []
		for r in rows:
			table.append({
				"customer_name": r.customer_name,
				"customer_label": r.customer_label,
				"total_revenue": float(r.total_revenue),
				"outstanding_amount": float(r.outstanding_amount),
				"invoice_count": int(r.invoice_count),
				"last_order_date": str(r.last_order_date) if r.last_order_date else "",
			})

		data = serialize({
			"rank_by": rank_by,
			"total_results": len(table),
			"company": company or "All",
			"from_date": from_date or "All time",
			"to_date": to_date or "All time",
			"customers": table,
		})

		# Summary
		if table:
			top = table[0]
			summary = (
				f"Top {len(table)} customers by {rank_by}. "
				f"#1: {top['customer_label']} with {format_currency(top['total_revenue'])} revenue, "
				f"{format_number(top['invoice_count'])} invoices."
			)
		else:
			summary = "No customer data found for the given filters."

		return {
			"data": data,
			"summary": summary,
			"table": table,
			"_query_source": sql.strip(),
		}
