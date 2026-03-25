"""warehouse_summary — Total stock value and item count per warehouse.

Maps to ERPNext report: Warehouse-wise Stock Balance.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class WarehouseSummaryTool(MCPTool):
	name = "warehouse_summary"
	description = (
		"Get total stock value and item count per warehouse. "
		"Provides a high-level view of inventory distribution."
	)
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Bin")
		check_doctype_permission("Warehouse")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")

		conditions = ["b.actual_qty != 0"]
		values: list[Any] = []

		if company:
			conditions.append("w.company = %s")
			values.append(company)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				b.warehouse,
				w.warehouse_type,
				COUNT(DISTINCT b.item_code) AS item_count,
				SUM(b.actual_qty) AS total_qty,
				SUM(b.stock_value) AS total_value
			FROM `tabBin` b
			JOIN `tabWarehouse` w ON w.name = b.warehouse
			WHERE {where}
			GROUP BY b.warehouse, w.warehouse_type
			ORDER BY total_value DESC
		"""

		rows = frappe.db.sql(sql, tuple(values), as_dict=True)

		table = []
		grand_total = 0.0
		grand_items = 0
		for r in rows:
			val = float(r.total_value or 0)
			items = int(r.item_count)
			grand_total += val
			grand_items += items
			table.append({
				"warehouse": r.warehouse,
				"warehouse_type": r.warehouse_type or "",
				"item_count": items,
				"total_qty": float(r.total_qty),
				"total_value": val,
			})

		data = serialize({
			"total_warehouses": len(table),
			"grand_total_value": round(grand_total, 2),
			"grand_total_items": grand_items,
			"company": company or "All",
			"warehouses": table,
		})

		if table:
			summary = (
				f"{format_number(len(table))} warehouses with stock. "
				f"Total value: {format_currency(grand_total)} across {format_number(grand_items)} items. "
				f"Largest: {table[0]['warehouse']} ({format_currency(table[0]['total_value'])})."
			)
		else:
			summary = "No warehouse stock data found."

		return {"data": data, "summary": summary, "table": table}
