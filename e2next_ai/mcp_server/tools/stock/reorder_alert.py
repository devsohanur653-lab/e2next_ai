"""reorder_alert — Items at or below reorder level.

Maps to ERPNext report: Items To Be Requested.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class ReorderAlertTool(MCPTool):
	name = "reorder_alert"
	description = (
		"Get items at or below reorder level / minimum stock quantity. "
		"Shows item, warehouse, current qty, reorder level, and shortfall."
	)
	parameters = {
		"warehouse": {"type": "str", "required": False, "description": "Filter by warehouse"},
		"item_group": {"type": "str", "required": False, "description": "Filter by item group"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Bin")
		check_doctype_permission("Item")

		warehouse = kwargs.get("warehouse")
		item_group = kwargs.get("item_group")

		conditions = [
			"b.actual_qty <= ir.warehouse_reorder_level",
			"ir.warehouse_reorder_level > 0",
		]
		values: list[Any] = []

		if warehouse:
			conditions.append("b.warehouse = %s")
			values.append(warehouse)

		if item_group:
			conditions.append("i.item_group = %s")
			values.append(item_group)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				b.item_code,
				i.item_name,
				i.item_group,
				i.stock_uom,
				b.warehouse,
				b.actual_qty AS current_qty,
				ir.warehouse_reorder_level AS reorder_level,
				ir.warehouse_reorder_qty AS reorder_qty,
				(ir.warehouse_reorder_level - b.actual_qty) AS shortfall
			FROM `tabBin` b
			JOIN `tabItem` i ON i.name = b.item_code
			JOIN `tabItem Reorder` ir ON ir.parent = i.name AND ir.warehouse = b.warehouse
			WHERE {where}
			ORDER BY (ir.warehouse_reorder_level - b.actual_qty) DESC
			LIMIT 100
		"""

		rows = frappe.db.sql(sql, tuple(values), as_dict=True)

		table = []
		for r in rows:
			table.append({
				"item_code": r.item_code,
				"item_name": r.item_name or "",
				"item_group": r.item_group or "",
				"stock_uom": r.stock_uom or "",
				"warehouse": r.warehouse,
				"current_qty": float(r.current_qty),
				"reorder_level": float(r.reorder_level),
				"reorder_qty": float(r.reorder_qty or 0),
				"shortfall": float(r.shortfall),
			})

		data = serialize({
			"total_alerts": len(table),
			"warehouse": warehouse or "All",
			"item_group": item_group or "All",
			"items": table,
		})

		if table:
			summary = (
				f"{format_number(len(table))} items below reorder level. "
				f"Most critical: {table[0]['item_name']} in {table[0]['warehouse']} "
				f"(need {format_number(table[0]['shortfall'])} {table[0]['stock_uom']})."
			)
		else:
			summary = "No items are currently below their reorder level."

		return {"data": data, "summary": summary, "table": table[:20]}
