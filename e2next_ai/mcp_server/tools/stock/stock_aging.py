"""stock_aging — Slow-moving or aged stock by FIFO.

Maps to ERPNext report: Stock Ageing.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class StockAgingTool(MCPTool):
	name = "stock_aging"
	description = (
		"Get slow-moving or aged stock analysis. Shows days in stock and value at risk. "
		"Uses FIFO-based ageing from Stock Ledger Entries."
	)
	parameters = {
		"warehouse": {"type": "str", "required": False, "description": "Filter by warehouse"},
		"company": {"type": "str", "required": False, "description": "Company name"},
		"min_days": {"type": "int", "required": False, "description": "Minimum days in stock to include (default 90)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Stock Ledger Entry")

		warehouse = kwargs.get("warehouse")
		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		min_days = int(kwargs.get("min_days") or 90)

		today = date.today()

		# Get the earliest inward SLE per item+warehouse that still has balance
		conditions = ["b.actual_qty > 0"]
		values: list[Any] = []

		if warehouse:
			conditions.append("b.warehouse = %s")
			values.append(warehouse)

		if company:
			conditions.append("w.company = %s")
			values.append(company)

		where = " AND ".join(conditions)

		# Find items with stock and their earliest inward date
		sql = f"""
			SELECT
				b.item_code,
				i.item_name,
				i.stock_uom,
				b.warehouse,
				b.actual_qty,
				b.stock_value,
				(
					SELECT MIN(sle.posting_date)
					FROM `tabStock Ledger Entry` sle
					WHERE sle.item_code = b.item_code
					  AND sle.warehouse = b.warehouse
					  AND sle.actual_qty > 0
					  AND sle.docstatus = 1
					  AND sle.is_cancelled = 0
				) AS earliest_inward_date
			FROM `tabBin` b
			JOIN `tabItem` i ON i.name = b.item_code
			JOIN `tabWarehouse` w ON w.name = b.warehouse
			WHERE {where}
			HAVING earliest_inward_date IS NOT NULL
			   AND DATEDIFF(%s, earliest_inward_date) >= %s
			ORDER BY DATEDIFF(%s, earliest_inward_date) DESC
			LIMIT 100
		"""
		values.extend([today.isoformat(), min_days, today.isoformat()])

		rows = frappe.db.sql(sql, tuple(values), as_dict=True)

		table = []
		total_value_at_risk = 0.0
		for r in rows:
			earliest = r.earliest_inward_date
			days_in_stock = (today - earliest).days if earliest else 0
			val = float(r.stock_value or 0)
			total_value_at_risk += val

			# Classify age buckets
			if days_in_stock >= 365:
				age_bucket = "365+ days"
			elif days_in_stock >= 180:
				age_bucket = "180-365 days"
			elif days_in_stock >= 90:
				age_bucket = "90-180 days"
			else:
				age_bucket = f"< 90 days"

			table.append({
				"item_code": r.item_code,
				"item_name": r.item_name or "",
				"stock_uom": r.stock_uom or "",
				"warehouse": r.warehouse,
				"actual_qty": float(r.actual_qty),
				"stock_value": val,
				"earliest_inward_date": str(earliest) if earliest else "",
				"days_in_stock": days_in_stock,
				"age_bucket": age_bucket,
			})

		data = serialize({
			"total_items": len(table),
			"total_value_at_risk": round(total_value_at_risk, 2),
			"min_days_filter": min_days,
			"warehouse": warehouse or "All",
			"company": company or "All",
			"items": table,
		})

		if table:
			summary = (
				f"{format_number(len(table))} items sitting for {min_days}+ days. "
				f"Total value at risk: {format_currency(total_value_at_risk)}. "
				f"Oldest: {table[0]['item_name']} ({table[0]['days_in_stock']} days)."
			)
		else:
			summary = f"No items found sitting for more than {min_days} days."

		return {"data": data, "summary": summary, "table": table[:20]}
