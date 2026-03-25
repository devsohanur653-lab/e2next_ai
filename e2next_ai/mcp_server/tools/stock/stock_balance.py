"""stock_balance — Current qty and value by item and/or warehouse.

Maps to ERPNext report: Stock Balance.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class StockBalanceTool(MCPTool):
	name = "stock_balance"
	description = (
		"Get current stock balance (quantity and value) by item and/or warehouse. "
		"Uses the Bin table for real-time stock data."
	)
	parameters = {
		"item_code": {"type": "str", "required": False, "description": "Filter by specific item code"},
		"warehouse": {"type": "str", "required": False, "description": "Filter by warehouse"},
		"company": {"type": "str", "required": False, "description": "Company name"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Bin")

		item_code = kwargs.get("item_code")
		warehouse = kwargs.get("warehouse")
		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")

		conditions = ["b.actual_qty != 0"]
		values: list[Any] = []

		if item_code:
			conditions.append("b.item_code = %s")
			values.append(item_code)

		if warehouse:
			conditions.append("b.warehouse = %s")
			values.append(warehouse)

		if company:
			conditions.append("w.company = %s")
			values.append(company)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				b.item_code,
				i.item_name,
				i.stock_uom,
				b.warehouse,
				b.actual_qty,
				b.stock_value,
				b.valuation_rate
			FROM `tabBin` b
			JOIN `tabItem` i ON i.name = b.item_code
			JOIN `tabWarehouse` w ON w.name = b.warehouse
			WHERE {where}
			ORDER BY b.stock_value DESC
			LIMIT 100
		"""

		rows = frappe.db.sql(sql, tuple(values), as_dict=True)

		table = []
		total_value = 0.0
		total_items = set()
		for r in rows:
			val = float(r.stock_value or 0)
			total_value += val
			total_items.add(r.item_code)
			table.append({
				"item_code": r.item_code,
				"item_name": r.item_name or "",
				"stock_uom": r.stock_uom or "",
				"warehouse": r.warehouse,
				"actual_qty": float(r.actual_qty),
				"stock_value": val,
				"valuation_rate": float(r.valuation_rate or 0),
			})

		data = serialize({
			"total_rows": len(table),
			"total_unique_items": len(total_items),
			"total_stock_value": round(total_value, 2),
			"company": company or "All",
			"item_code": item_code or "All",
			"warehouse": warehouse or "All",
			"items": table,
		})

		summary = (
			f"Stock balance: {format_number(len(total_items))} items, "
			f"total value {format_currency(total_value)}."
		)
		if item_code and table:
			total_qty = sum(r["actual_qty"] for r in table)
			summary = (
				f"{item_code}: {format_number(total_qty)} {table[0]['stock_uom']} "
				f"across {len(table)} warehouse(s), value {format_currency(total_value)}."
			)

		return {"data": data, "summary": summary, "table": table[:20]}
