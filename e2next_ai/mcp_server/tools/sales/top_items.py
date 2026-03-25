"""top_items — Rank items by qty sold or revenue.

Maps to ERPNext report: Item-wise Sales History.
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
	"revenue": "revenue",
	"amount": "revenue",
	"total_revenue": "revenue",
	"sales": "revenue",
	"qty": "qty",
	"quantity": "qty",
	"total_qty": "qty",
	"sold": "qty",
}


class TopItemsTool(MCPTool):
	name = "top_items"
	description = (
		"Get top selling items ranked by quantity sold or revenue. "
		"Shows item name, qty, amount, and top customer for each item."
	)
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name"},
		"from_date": {"type": "str", "required": False, "description": "Start date (YYYY-MM-DD) or natural language"},
		"to_date": {"type": "str", "required": False, "description": "End date (YYYY-MM-DD)"},
		"rank_by": {"type": "str", "required": False, "description": "Ranking criteria: revenue or qty (default revenue)"},
		"item_group": {"type": "str", "required": False, "description": "Filter by item group"},
		"limit": {"type": "int", "required": False, "description": "Number of items to return (default 10)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Sales Invoice")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		rank_by = _RANK_MAP.get((kwargs.get("rank_by") or "revenue").strip().lower(), "revenue")
		item_group = kwargs.get("item_group")
		limit = int(kwargs.get("limit") or 10)

		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		# Default to current fiscal year
		if not from_date or not to_date:
			from_date, to_date = _default_fiscal_range(from_date, to_date)

		conditions = ["si.docstatus = 1", "si.posting_date BETWEEN %s AND %s"]
		values: list[Any] = [from_date, to_date]

		if company:
			conditions.append("si.company = %s")
			values.append(company)

		if item_group:
			conditions.append("sii.item_group = %s")
			values.append(item_group)

		where = " AND ".join(conditions)
		order_col = "total_revenue" if rank_by == "revenue" else "total_qty"

		sql = f"""
			SELECT
				sii.item_code,
				sii.item_name,
				sii.stock_uom AS uom,
				SUM(sii.qty) AS total_qty,
				SUM(sii.amount) AS total_revenue,
				COUNT(DISTINCT si.name) AS invoice_count
			FROM `tabSales Invoice Item` sii
			JOIN `tabSales Invoice` si ON si.name = sii.parent
			WHERE {where}
			GROUP BY sii.item_code, sii.item_name, sii.stock_uom
			ORDER BY {order_col} DESC
			LIMIT %s
		"""
		values.append(limit)

		rows = frappe.db.sql(sql, tuple(values), as_dict=True)

		# Get top customer per item
		table = []
		for r in rows:
			top_customer = self._get_top_customer(r.item_code, from_date, to_date, company)
			table.append({
				"item_code": r.item_code,
				"item_name": r.item_name,
				"uom": r.uom or "",
				"total_qty": float(r.total_qty),
				"total_revenue": float(r.total_revenue),
				"invoice_count": int(r.invoice_count),
				"top_customer": top_customer,
			})

		data = serialize({
			"rank_by": rank_by,
			"total_results": len(table),
			"company": company or "All",
			"from_date": from_date,
			"to_date": to_date,
			"item_group": item_group or "All",
			"items": table,
		})

		if table:
			top = table[0]
			summary = (
				f"Top {len(table)} items by {rank_by}. "
				f"#1: {top['item_name']} — {format_number(top['total_qty'])} {top['uom']} "
				f"({format_currency(top['total_revenue'])})."
			)
		else:
			summary = "No item sales data found for the given filters."

		return {
			"data": data,
			"summary": summary,
			"table": table,
			"_query_source": sql.strip(),
		}

	def _get_top_customer(
		self, item_code: str, from_date: str, to_date: str, company: str | None
	) -> str:
		"""Get the customer who bought the most of this item."""
		conditions = [
			"si.docstatus = 1",
			"si.posting_date BETWEEN %s AND %s",
			"sii.item_code = %s",
		]
		values: list[Any] = [from_date, to_date, item_code]

		if company:
			conditions.append("si.company = %s")
			values.append(company)

		where = " AND ".join(conditions)

		result = frappe.db.sql(
			f"""
			SELECT si.customer_name
			FROM `tabSales Invoice Item` sii
			JOIN `tabSales Invoice` si ON si.name = sii.parent
			WHERE {where}
			GROUP BY si.customer, si.customer_name
			ORDER BY SUM(sii.amount) DESC
			LIMIT 1
			""",
			tuple(values),
			as_dict=True,
		)
		return result[0].customer_name if result else ""


def _default_fiscal_range(from_date: str | None, to_date: str | None) -> tuple[str, str]:
	fiscal_year = frappe.defaults.get_global_default("fiscal_year")
	if fiscal_year and frappe.db.exists("Fiscal Year", fiscal_year):
		fy = frappe.get_doc("Fiscal Year", fiscal_year)
		return (from_date or str(fy.year_start_date), to_date or str(fy.year_end_date))
	return (
		from_date or str(frappe.utils.get_first_day(frappe.utils.today())),
		to_date or str(frappe.utils.today()),
	)
