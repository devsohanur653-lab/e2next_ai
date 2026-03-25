"""sales_persons_summary — Revenue per sales person with target vs actual.

Maps to ERPNext report: Sales Person-wise Transaction Summary.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class SalesPersonsSummaryTool(MCPTool):
	name = "sales_persons_summary"
	description = (
		"Get revenue per sales person for a period. "
		"Shows target vs actual if sales targets are configured."
	)
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name"},
		"from_date": {"type": "str", "required": False, "description": "Start date (YYYY-MM-DD) or natural language"},
		"to_date": {"type": "str", "required": False, "description": "End date (YYYY-MM-DD)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Sales Invoice")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")

		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		if not from_date or not to_date:
			from_date, to_date = _default_fiscal_range(from_date, to_date)

		conditions = ["si.docstatus = 1", "si.posting_date BETWEEN %s AND %s"]
		values: list[Any] = [from_date, to_date]

		if company:
			conditions.append("si.company = %s")
			values.append(company)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				st.sales_person,
				SUM(si.grand_total * st.allocated_percentage / 100) AS allocated_revenue,
				SUM(si.net_total * st.allocated_percentage / 100) AS allocated_net,
				COUNT(DISTINCT si.name) AS invoice_count,
				COUNT(DISTINCT si.customer) AS customer_count
			FROM `tabSales Team` st
			JOIN `tabSales Invoice` si ON si.name = st.parent AND st.parenttype = 'Sales Invoice'
			WHERE {where}
			GROUP BY st.sales_person
			ORDER BY allocated_revenue DESC
		"""

		rows = frappe.db.sql(sql, tuple(values), as_dict=True)

		# Get targets if available
		targets = self._get_targets(company, from_date, to_date)

		table = []
		for r in rows:
			sp_name = r.sales_person
			revenue = float(r.allocated_revenue)
			target = targets.get(sp_name, 0.0)
			achievement_pct = (revenue / target * 100) if target > 0 else 0.0

			table.append({
				"sales_person": sp_name,
				"allocated_revenue": revenue,
				"allocated_net": float(r.allocated_net),
				"invoice_count": int(r.invoice_count),
				"customer_count": int(r.customer_count),
				"target": target,
				"achievement_pct": round(achievement_pct, 1),
			})

		data = serialize({
			"total_results": len(table),
			"company": company or "All",
			"from_date": from_date,
			"to_date": to_date,
			"sales_persons": table,
		})

		if table:
			total_rev = sum(r["allocated_revenue"] for r in table)
			summary = (
				f"{len(table)} sales persons from {from_date} to {to_date}. "
				f"Total allocated revenue: {format_currency(total_rev)}. "
				f"Top: {table[0]['sales_person']} with {format_currency(table[0]['allocated_revenue'])}."
			)
		else:
			summary = "No sales person data found. Sales Team may not be assigned on invoices."

		return {
			"data": data,
			"summary": summary,
			"table": table,
			"_query_source": sql.strip(),
		}

	def _get_targets(self, company: str | None, from_date: str, to_date: str) -> dict[str, float]:
		"""Get sales person targets for the period if Target Detail exists."""
		try:
			# Check if Target Detail doctype exists (not always installed)
			if not frappe.db.exists("DocType", "Target Detail"):
				return {}

			conditions = ["1=1"]
			values: list[Any] = []

			# Target Detail is a child of Sales Person
			rows = frappe.db.sql(
				"""
				SELECT
					sp.name AS sales_person,
					COALESCE(SUM(td.target_amount), 0) AS target_amount
				FROM `tabSales Person` sp
				LEFT JOIN `tabTarget Detail` td ON td.parent = sp.name AND td.parenttype = 'Sales Person'
				GROUP BY sp.name
				""",
				as_dict=True,
			)
			return {r.sales_person: float(r.target_amount) for r in rows if r.target_amount}
		except Exception:
			return {}


def _default_fiscal_range(from_date: str | None, to_date: str | None) -> tuple[str, str]:
	fiscal_year = frappe.defaults.get_global_default("fiscal_year")
	if fiscal_year and frappe.db.exists("Fiscal Year", fiscal_year):
		fy = frappe.get_doc("Fiscal Year", fiscal_year)
		return (from_date or str(fy.year_start_date), to_date or str(fy.year_end_date))
	return (
		from_date or str(frappe.utils.get_first_day(frappe.utils.today())),
		to_date or str(frappe.utils.today()),
	)
