"""purchase_summary — Total billed, paid, outstanding by period.

Maps to ERPNext reports: Purchase Analytics, Accounts Payable Summary.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class PurchaseSummaryTool(MCPTool):
	name = "purchase_summary"
	description = (
		"Get purchase summary: total billed, paid, outstanding, invoice count "
		"for a date range."
	)
	parameters = {
		"company": {"type": "str", "required": False},
		"from_date": {"type": "str", "required": False},
		"to_date": {"type": "str", "required": False},
		"supplier_group": {"type": "str", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Purchase Invoice")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		supplier_group = kwargs.get("supplier_group")

		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		if not from_date or not to_date:
			from_date, to_date = _default_fiscal(from_date, to_date)

		conditions = ["pi.docstatus = 1", "pi.posting_date BETWEEN %s AND %s"]
		values: list[Any] = [from_date, to_date]

		if company:
			conditions.append("pi.company = %s")
			values.append(company)
		if supplier_group:
			conditions.append("pi.supplier_group = %s")
			values.append(supplier_group)

		where = " AND ".join(conditions)

		row = frappe.db.sql(
			f"""
			SELECT
				COUNT(*) AS total_invoices,
				COALESCE(SUM(pi.grand_total), 0) AS total_billed,
				COALESCE(SUM(pi.outstanding_amount), 0) AS total_outstanding,
				COALESCE(SUM(pi.grand_total - pi.outstanding_amount), 0) AS total_paid,
				COUNT(DISTINCT pi.supplier) AS unique_suppliers
			FROM `tabPurchase Invoice` pi
			WHERE {where}
			""",
			tuple(values),
			as_dict=True,
		)[0]

		total_billed = float(row.total_billed)
		total_paid = float(row.total_paid)
		total_outstanding = float(row.total_outstanding)
		total_invoices = int(row.total_invoices)

		data = serialize({
			"total_invoices": total_invoices,
			"total_billed": total_billed,
			"total_paid": total_paid,
			"total_outstanding": total_outstanding,
			"unique_suppliers": int(row.unique_suppliers),
			"from_date": from_date,
			"to_date": to_date,
			"company": company or "All",
		})

		summary = (
			f"Purchases from {from_date} to {to_date}: "
			f"{format_currency(total_billed)} billed across {format_number(total_invoices)} invoices. "
			f"Paid: {format_currency(total_paid)}, Outstanding: {format_currency(total_outstanding)}."
		)

		return {"data": data, "summary": summary}


def _default_fiscal(from_date, to_date):
	fy = frappe.defaults.get_global_default("fiscal_year")
	if fy and frappe.db.exists("Fiscal Year", fy):
		doc = frappe.get_doc("Fiscal Year", fy)
		return (from_date or str(doc.year_start_date), to_date or str(doc.year_end_date))
	return (from_date or str(frappe.utils.get_first_day(frappe.utils.today())), to_date or str(frappe.utils.today()))
