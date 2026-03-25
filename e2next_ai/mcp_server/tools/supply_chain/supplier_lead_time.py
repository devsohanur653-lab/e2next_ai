"""supplier_lead_time — Average days from PO to GRN per supplier.

Maps to ERPNext: Supplier Lead Time / procurement analytics.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class SupplierLeadTimeTool(MCPTool):
	name = "supplier_lead_time"
	description = "Get average lead time (days) from Purchase Order date to Purchase Receipt date per supplier."
	parameters = {
		"company": {"type": "str", "required": False},
		"supplier": {"type": "str", "required": False},
		"from_date": {"type": "str", "required": False},
		"to_date": {"type": "str", "required": False},
		"limit": {"type": "int", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Purchase Order")
		check_doctype_permission("Purchase Receipt")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		supplier = kwargs.get("supplier")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		limit = int(kwargs.get("limit") or 20)

		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		if not from_date or not to_date:
			parsed = parse_date_range("this month")
			assert parsed is not None
			from_date = from_date or parsed[0]
			to_date = to_date or parsed[1]

		conditions = [
			"pr.docstatus = 1",
			"po.docstatus = 1",
			"pr.posting_date BETWEEN %s AND %s",
			"COALESCE(pri.purchase_order, '') != ''",
		]
		values: list[Any] = [from_date, to_date]

		if company:
			conditions.append("pr.company = %s")
			values.append(company)
		if supplier:
			conditions.append("pr.supplier = %s")
			values.append(supplier)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				pr.supplier,
				pr.supplier_name,
				COUNT(DISTINCT pr.name) AS receipt_count,
				COUNT(DISTINCT po.name) AS po_count,
				AVG(DATEDIFF(pr.posting_date, po.transaction_date)) AS avg_days,
				MIN(DATEDIFF(pr.posting_date, po.transaction_date)) AS min_days,
				MAX(DATEDIFF(pr.posting_date, po.transaction_date)) AS max_days
			FROM `tabPurchase Receipt` pr
			JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
			JOIN `tabPurchase Order` po ON po.name = pri.purchase_order
			WHERE {where}
			GROUP BY pr.supplier, pr.supplier_name
			ORDER BY avg_days ASC
			LIMIT %s
		"""
		rows = frappe.db.sql(sql, (*values, limit), as_dict=True)

		table = []
		for r in rows:
			table.append(
				{
					"supplier": r.supplier,
					"supplier_name": r.supplier_name or "",
					"receipt_count": int(r.receipt_count or 0),
					"po_count": int(r.po_count or 0),
					"avg_days": float(r.avg_days or 0),
					"min_days": float(r.min_days or 0),
					"max_days": float(r.max_days or 0),
				}
			)

		data = serialize(
			{
				"company": company or "All",
				"supplier": supplier or "All",
				"from_date": from_date,
				"to_date": to_date,
				"total_suppliers": len(table),
				"suppliers": table,
			}
		)

		summary = f"Supplier lead time ({from_date} to {to_date}): {format_number(len(table))} suppliers."
		return {"data": data, "summary": summary, "table": serialize_rows(table)[:20], "_query_source": sql.strip()}

