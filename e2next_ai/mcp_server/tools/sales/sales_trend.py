"""sales_trend — Daily/monthly revenue trend with period comparison.

Maps to ERPNext report: Sales Analytics.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class SalesTrendTool(MCPTool):
	name = "sales_trend"
	description = (
		"Get daily or monthly sales revenue trend for a period. "
		"Compares to the same period last year or last month with % change."
	)
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name"},
		"period": {"type": "str", "required": False, "description": "Granularity: 'daily' or 'monthly' (default monthly)"},
		"from_date": {"type": "str", "required": False, "description": "Start date (YYYY-MM-DD) or natural language"},
		"to_date": {"type": "str", "required": False, "description": "End date (YYYY-MM-DD)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Sales Invoice")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		period = (kwargs.get("period") or "monthly").strip().lower()
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")

		# Parse natural language dates
		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		if not from_date or not to_date:
			# Default to this month
			today = date.today()
			from_date = from_date or today.replace(day=1).isoformat()
			to_date = to_date or today.isoformat()

		# Current period data
		current_data = self._get_trend_data(company, period, from_date, to_date)

		# Calculate comparison period (same duration, shifted back)
		from_d = date.fromisoformat(from_date)
		to_d = date.fromisoformat(to_date)
		duration = (to_d - from_d).days

		prev_to = from_d - timedelta(days=1)
		prev_from = prev_to - timedelta(days=duration)

		prev_data = self._get_trend_data(company, period, prev_from.isoformat(), prev_to.isoformat())

		# Calculate totals and % change
		current_total = sum(r["revenue"] for r in current_data)
		prev_total = sum(r["revenue"] for r in prev_data)
		pct_change = ((current_total - prev_total) / prev_total * 100) if prev_total else 0.0

		data = serialize({
			"from_date": from_date,
			"to_date": to_date,
			"period": period,
			"company": company or "All",
			"current_total": round(current_total, 2),
			"previous_total": round(prev_total, 2),
			"pct_change": round(pct_change, 2),
			"previous_from": prev_from.isoformat(),
			"previous_to": prev_to.isoformat(),
			"trend": current_data,
		})

		direction = "up" if pct_change > 0 else "down" if pct_change < 0 else "flat"
		summary = (
			f"Sales trend ({period}) from {from_date} to {to_date}: "
			f"{format_currency(current_total)}. "
			f"Previous period: {format_currency(prev_total)} "
			f"({direction} {abs(pct_change):.1f}%)."
		)

		return {
			"data": data,
			"summary": summary,
			"table": current_data[:31],  # Cap at 31 rows for display
			"_query_source": f"Sales Invoice grouped by {period}",
		}

	def _get_trend_data(
		self, company: str | None, period: str, from_date: str, to_date: str
	) -> list[dict[str, Any]]:
		"""Fetch aggregated revenue by period bucket."""
		if period == "daily":
			group_expr = "si.posting_date"
			label_expr = "si.posting_date AS period_label"
		else:
			group_expr = "DATE_FORMAT(si.posting_date, '%%Y-%%m')"
			label_expr = "DATE_FORMAT(si.posting_date, '%%Y-%%m') AS period_label"

		conditions = ["si.docstatus = 1", "si.posting_date BETWEEN %s AND %s"]
		values: list[Any] = [from_date, to_date]

		if company:
			conditions.append("si.company = %s")
			values.append(company)

		where = " AND ".join(conditions)

		rows = frappe.db.sql(
			f"""
			SELECT
				{label_expr},
				COUNT(*) AS invoice_count,
				COALESCE(SUM(si.grand_total), 0) AS revenue
			FROM `tabSales Invoice` si
			WHERE {where}
			GROUP BY {group_expr}
			ORDER BY {group_expr}
			""",
			tuple(values),
			as_dict=True,
		)

		return [
			{
				"period": str(r.period_label),
				"invoice_count": int(r.invoice_count),
				"revenue": float(r.revenue),
			}
			for r in rows
		]
