"""po_to_invoice_flow — Procurement flow health checks.

Checks common gaps:
- Purchase Receipts not billed (GRN missing Purchase Invoice) [unbilled GRN]
- Purchase Invoices without Purchase Order (no PO reference)

Maps to ERPNext: Received Items To Be Billed, Purchase Order/Purchase Invoice reports.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class POToInvoiceFlowTool(MCPTool):
	name = "po_to_invoice_flow"
	description = "Health check for PO→Receipt→Invoice flow (unbilled GRNs, invoices missing PO, etc.)."
	parameters = {
		"company": {"type": "str", "required": False},
		"from_date": {"type": "str", "required": False},
		"to_date": {"type": "str", "required": False},
		"limit": {"type": "int", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		limit = int(kwargs.get("limit") or 20)

		# Parse natural language dates
		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		if not from_date or not to_date:
			parsed = parse_date_range("this month")
			assert parsed is not None
			from_date = from_date or parsed[0]
			to_date = to_date or parsed[1]

		# 1) Unbilled GRNs (Purchase Receipt submitted with per_billed < 100)
		check_doctype_permission("Purchase Receipt")
		conditions_pr = ["pr.docstatus = 1", "pr.posting_date BETWEEN %s AND %s", "COALESCE(pr.per_billed, 0) < 99.99"]
		values_pr: list[Any] = [from_date, to_date]
		if company:
			conditions_pr.append("pr.company = %s")
			values_pr.append(company)
		where_pr = " AND ".join(conditions_pr)

		sql_unbilled = f"""
			SELECT
				pr.name,
				pr.supplier,
				pr.supplier_name,
				pr.posting_date,
				pr.grand_total,
				pr.per_billed
			FROM `tabPurchase Receipt` pr
			WHERE {where_pr}
			ORDER BY pr.posting_date DESC
			LIMIT %s
		"""
		unbilled_rows = frappe.db.sql(sql_unbilled, (*values_pr, limit), as_dict=True)
		unbilled = []
		for r in unbilled_rows:
			unbilled.append(
				{
					"purchase_receipt": r.name,
					"supplier": r.supplier,
					"supplier_name": r.supplier_name or "",
					"posting_date": str(r.posting_date) if r.posting_date else "",
					"grand_total": float(r.grand_total or 0),
					"percent_billed": float(r.per_billed or 0),
				}
			)

		# 2) Purchase Invoices without PO reference (header-level purchase_order often empty; use item link)
		check_doctype_permission("Purchase Invoice")
		conditions_pi = ["pi.docstatus = 1", "pi.posting_date BETWEEN %s AND %s"]
		values_pi: list[Any] = [from_date, to_date]
		if company:
			conditions_pi.append("pi.company = %s")
			values_pi.append(company)
		where_pi = " AND ".join(conditions_pi)

		sql_no_po = f"""
			SELECT
				pi.name,
				pi.supplier,
				pi.supplier_name,
				pi.posting_date,
				pi.grand_total,
				COUNT(pii.name) AS item_rows,
				SUM(CASE WHEN COALESCE(pii.purchase_order, '') = '' THEN 1 ELSE 0 END) AS item_rows_without_po
			FROM `tabPurchase Invoice` pi
			LEFT JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
			WHERE {where_pi}
			GROUP BY pi.name, pi.supplier, pi.supplier_name, pi.posting_date, pi.grand_total
			HAVING item_rows_without_po = item_rows
			ORDER BY pi.posting_date DESC
			LIMIT %s
		"""
		no_po_rows = frappe.db.sql(sql_no_po, (*values_pi, limit), as_dict=True)
		invoices_without_po = []
		for r in no_po_rows:
			invoices_without_po.append(
				{
					"purchase_invoice": r.name,
					"supplier": r.supplier,
					"supplier_name": r.supplier_name or "",
					"posting_date": str(r.posting_date) if r.posting_date else "",
					"grand_total": float(r.grand_total or 0),
				}
			)

		data = serialize(
			{
				"company": company or "All",
				"from_date": from_date,
				"to_date": to_date,
				"unbilled_grn_count": len(unbilled),
				"invoices_without_po_count": len(invoices_without_po),
				"unbilled_grns": unbilled,
				"invoices_without_po": invoices_without_po,
			}
		)

		summary = (
			f"Flow health ({from_date} to {to_date}): "
			f"{format_number(len(unbilled))} unbilled GRNs, {format_number(len(invoices_without_po))} invoices without PO."
		)

		# Table: show the most urgent unbilled GRNs
		return {"data": data, "summary": summary, "table": serialize_rows(unbilled)[:20], "_query_source": sql_unbilled.strip()}

