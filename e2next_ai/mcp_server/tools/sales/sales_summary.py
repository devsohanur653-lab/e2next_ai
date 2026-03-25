"""sales_summary — Total invoiced, collected, outstanding for a period.

Maps to ERPNext reports: Sales Analytics, Accounts Receivable Summary.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class SalesSummaryTool(MCPTool):
	name = "sales_summary"
	description = (
		"Get sales summary: total invoiced, collected, outstanding, invoice count, "
		"and average invoice value for a date range."
	)
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name"},
		"from_date": {"type": "str", "required": False, "description": "Start date (YYYY-MM-DD) or natural language like 'this month'"},
		"to_date": {"type": "str", "required": False, "description": "End date (YYYY-MM-DD)"},
		"customer_group": {"type": "str", "required": False, "description": "Filter by customer group"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Sales Invoice")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		customer_group = kwargs.get("customer_group")

		# Parse natural language dates
		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		# Default to current fiscal year
		if not from_date or not to_date:
			from_date, to_date = _default_date_range(from_date, to_date)

		# Build query
		conditions = ["si.docstatus = 1", "si.posting_date BETWEEN %s AND %s"]
		values: list[Any] = [from_date, to_date]

		if company:
			conditions.append("si.company = %s")
			values.append(company)

		if customer_group:
			conditions.append("si.customer_group = %s")
			values.append(customer_group)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				COUNT(*) AS total_invoices,
				COALESCE(SUM(si.grand_total), 0) AS total_invoiced,
				COALESCE(SUM(si.net_total), 0) AS total_net,
				COALESCE(SUM(si.total_taxes_and_charges), 0) AS total_taxes,
				COALESCE(SUM(si.outstanding_amount), 0) AS total_outstanding,
				COALESCE(SUM(si.grand_total - si.outstanding_amount), 0) AS total_collected,
				COUNT(DISTINCT si.customer) AS unique_customers
			FROM `tabSales Invoice` si
			WHERE {where}
		"""

		row = frappe.db.sql(sql, tuple(values), as_dict=True)[0]

		total_invoices = int(row.total_invoices)
		total_invoiced = float(row.total_invoiced)
		total_collected = float(row.total_collected)
		total_outstanding = float(row.total_outstanding)
		total_net = float(row.total_net)
		total_taxes = float(row.total_taxes)
		unique_customers = int(row.unique_customers)
		avg_invoice = total_invoiced / total_invoices if total_invoices > 0 else 0.0

		data = serialize({
			"total_invoices": total_invoices,
			"total_invoiced": total_invoiced,
			"total_net": total_net,
			"total_taxes": total_taxes,
			"total_outstanding": total_outstanding,
			"total_collected": total_collected,
			"unique_customers": unique_customers,
			"avg_invoice_value": round(avg_invoice, 2),
			"from_date": from_date,
			"to_date": to_date,
			"company": company or "All",
			"customer_group": customer_group or "All",
		})

		summary = (
			f"Sales from {from_date} to {to_date}: "
			f"{format_currency(total_invoiced)} across {format_number(total_invoices)} invoices. "
			f"Collected: {format_currency(total_collected)}, "
			f"Outstanding: {format_currency(total_outstanding)}."
		)

		return {
			"data": data,
			"summary": summary,
			"_query_source": sql.strip(),
		}


def _default_date_range(from_date: str | None, to_date: str | None) -> tuple[str, str]:
	"""Fall back to current fiscal year or current month."""
	fiscal_year = frappe.defaults.get_global_default("fiscal_year")
	if fiscal_year and frappe.db.exists("Fiscal Year", fiscal_year):
		fy = frappe.get_doc("Fiscal Year", fiscal_year)
		return (
			from_date or str(fy.year_start_date),
			to_date or str(fy.year_end_date),
		)
	return (
		from_date or str(frappe.utils.get_first_day(frappe.utils.today())),
		to_date or str(frappe.utils.today()),
	)
