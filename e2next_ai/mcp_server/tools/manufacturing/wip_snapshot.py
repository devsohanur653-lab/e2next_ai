"""wip_snapshot — Work-in-progress stock snapshot by item in a WIP warehouse.

Uses Bin for current stock in the given WIP warehouse.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class WipSnapshotTool(MCPTool):
	name = "wip_snapshot"
	description = "Get WIP stock snapshot (qty/value) for a WIP warehouse."
	parameters = {
		"company": {"type": "str", "required": False},
		"wip_warehouse": {"type": "str", "required": False, "description": "Warehouse name (required for useful results)"},
		"limit": {"type": "int", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Bin")
		check_doctype_permission("Warehouse")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		wip_warehouse = kwargs.get("wip_warehouse")
		limit = int(kwargs.get("limit") or 50)

		if not wip_warehouse:
			# Best-effort: try user default warehouse, else any warehouse containing "WIP",
			# else any warehouse at all (so the tool can still run on simple setups).
			wip_warehouse = frappe.defaults.get_user_default("warehouse") or None
			if not wip_warehouse:
				wip_warehouse = frappe.db.get_value("Warehouse", {"name": ("like", "%WIP%")}, "name")
			if not wip_warehouse:
				wip_warehouse = frappe.db.get_value("Warehouse", {}, "name")

		if not wip_warehouse:
			raise ValueError("No Warehouse found. Please create a warehouse or provide wip_warehouse.")

		conditions = ["b.actual_qty != 0", "b.warehouse = %s"]
		values: list[Any] = [wip_warehouse]
		if company:
			conditions.append("w.company = %s")
			values.append(company)
		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				b.item_code,
				i.item_name,
				i.stock_uom,
				b.actual_qty,
				b.stock_value
			FROM `tabBin` b
			JOIN `tabItem` i ON i.name = b.item_code
			JOIN `tabWarehouse` w ON w.name = b.warehouse
			WHERE {where}
			ORDER BY b.stock_value DESC
			LIMIT %s
		"""
		rows = frappe.db.sql(sql, (*values, limit), as_dict=True)

		table = []
		total_value = 0.0
		for r in rows:
			val = float(r.stock_value or 0)
			total_value += val
			table.append(
				{
					"item_code": r.item_code,
					"item_name": r.item_name or "",
					"stock_uom": r.stock_uom or "",
					"qty": float(r.actual_qty or 0),
					"stock_value": val,
				}
			)

		data = serialize(
			{
				"company": company or "All",
				"wip_warehouse": wip_warehouse,
				"total_rows": len(table),
				"total_value": total_value,
				"items": table,
			}
		)
		summary = f"WIP in {wip_warehouse}: {format_number(len(table))} items, value {format_currency(total_value)}."
		return {"data": data, "summary": summary, "table": serialize_rows(table)[:20], "_query_source": sql.strip()}

