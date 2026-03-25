"""bom_usage — BOM consumption vs standard (approximation).

Best-effort implementation:
- Lists BOM items (standard quantities) for a BOM or production item.
- Optionally compares to Stock Entry consumption (Material Consumption / Manufacture) in date range if present.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class BomUsageTool(MCPTool):
	name = "bom_usage"
	description = "Get BOM standard raw materials, optionally compare with consumption stock entries."
	parameters = {
		"bom_no": {"type": "str", "required": False},
		"item_code": {"type": "str", "required": False},
		"from_date": {"type": "str", "required": False},
		"to_date": {"type": "str", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		if not frappe.db.exists("DocType", "BOM"):
			raise ValueError("Manufacturing doctypes not found (BOM). Enable Manufacturing in ERPNext.")

		check_doctype_permission("BOM")
		check_doctype_permission("BOM Item")

		bom_no = kwargs.get("bom_no")
		item_code = kwargs.get("item_code")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")

		if not bom_no and item_code:
			# Pick default active BOM for item
			bom_no = frappe.db.get_value("BOM", {"item": item_code, "is_active": 1, "docstatus": 1}, "name")

		if not bom_no:
			# Best-effort default: pick any submitted BOM (some setups don't set is_active)
			bom_no = frappe.db.get_value("BOM", {"docstatus": 1}, "name")
		if not bom_no:
			raise ValueError("No submitted BOM found. Provide bom_no or item_code after creating a BOM in ERPNext.")

		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		sql_bom = """
			SELECT
				b.name AS bom_no,
				b.item AS production_item,
				b.item_name AS production_item_name,
				b.quantity AS bom_qty
			FROM `tabBOM` b
			WHERE b.name = %s
		"""
		bom_row = frappe.db.sql(sql_bom, (bom_no,), as_dict=True)[0]

		sql_items = """
			SELECT
				bi.item_code,
				bi.item_name,
				bi.stock_uom,
				bi.qty AS standard_qty
			FROM `tabBOM Item` bi
			WHERE bi.parent = %s
			ORDER BY bi.qty DESC
		"""
		rows = frappe.db.sql(sql_items, (bom_no,), as_dict=True)

		table = []
		for r in rows:
			table.append(
				{
					"item_code": r.item_code,
					"item_name": r.item_name or "",
					"stock_uom": r.stock_uom or "",
					"standard_qty": float(r.standard_qty or 0),
				}
			)

		# Optional: consumption from Stock Entry Detail (best-effort)
		consumption = None
		if from_date and to_date and frappe.db.exists("DocType", "Stock Entry"):
			try:
				check_doctype_permission("Stock Entry")
				check_doctype_permission("Stock Entry Detail")
				sql_cons = """
					SELECT
						sed.item_code,
						SUM(sed.qty) AS consumed_qty
					FROM `tabStock Entry` se
					JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
					WHERE se.docstatus = 1
					  AND se.posting_date BETWEEN %s AND %s
					  AND se.purpose IN ('Material Consumption', 'Manufacture')
					  AND COALESCE(se.bom_no, '') = %s
					GROUP BY sed.item_code
				"""
				cons_rows = frappe.db.sql(sql_cons, (from_date, to_date, bom_no), as_dict=True)
				consumption = {r.item_code: float(r.consumed_qty or 0) for r in cons_rows}
			except Exception:
				consumption = None

		if consumption is not None:
			for r in table:
				r["consumed_qty"] = float(consumption.get(r["item_code"], 0))
				r["variance_qty"] = float(r["consumed_qty"] - r["standard_qty"])

		data = serialize(
			{
				"bom_no": bom_no,
				"production_item": bom_row.production_item or "",
				"production_item_name": bom_row.production_item_name or "",
				"bom_qty": float(bom_row.bom_qty or 0),
				"from_date": from_date or "",
				"to_date": to_date or "",
				"items": table,
			}
		)

		summary = f"BOM {bom_no}: {format_number(len(table))} raw material rows."
		return {"data": data, "summary": summary, "table": serialize_rows(table)[:20], "_query_source": sql_items.strip()}

