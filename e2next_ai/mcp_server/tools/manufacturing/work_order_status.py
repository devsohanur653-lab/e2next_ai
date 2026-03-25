"""work_order_status — Work Order list by status/item.

Maps to ERPNext: Work Order Summary.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class WorkOrderStatusTool(MCPTool):
	name = "work_order_status"
	description = "Get work orders by status (open/in progress/completed) with key fields."
	parameters = {
		"company": {"type": "str", "required": False},
		"status": {"type": "str", "required": False, "description": "WO status (optional)"},
		"item_code": {"type": "str", "required": False},
		"limit": {"type": "int", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		if not frappe.db.exists("DocType", "Work Order"):
			raise ValueError("Manufacturing doctypes not found (Work Order). Enable Manufacturing in ERPNext.")

		check_doctype_permission("Work Order")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		status = kwargs.get("status")
		item_code = kwargs.get("item_code")
		limit = int(kwargs.get("limit") or 50)

		conditions = ["wo.docstatus < 2"]
		values: list[Any] = []
		if company:
			conditions.append("wo.company = %s")
			values.append(company)
		if status:
			conditions.append("wo.status = %s")
			values.append(status)
		if item_code:
			conditions.append("wo.production_item = %s")
			values.append(item_code)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				wo.name,
				wo.status,
				wo.production_item AS item_code,
				wo.item_name,
				wo.qty,
				wo.produced_qty,
				wo.planned_start_date,
				wo.expected_delivery_date,
				wo.company
			FROM `tabWork Order` wo
			WHERE {where}
			ORDER BY wo.modified DESC
			LIMIT %s
		"""
		rows = frappe.db.sql(sql, (*values, limit), as_dict=True)

		table = []
		for r in rows:
			table.append(
				{
					"work_order": r.name,
					"status": r.status or "",
					"item_code": r.item_code or "",
					"item_name": r.item_name or "",
					"qty": float(r.qty or 0),
					"produced_qty": float(r.produced_qty or 0),
					"planned_start_date": str(r.planned_start_date) if r.planned_start_date else "",
					"expected_delivery_date": str(r.expected_delivery_date) if r.expected_delivery_date else "",
					"company": r.company or "",
				}
			)

		# Status counts
		counts: dict[str, int] = {}
		for r in table:
			s = r["status"] or "Unknown"
			counts[s] = counts.get(s, 0) + 1
		by_status = [{"status": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)]

		data = serialize(
			{
				"company": company or "All",
				"status": status or "All",
				"item_code": item_code or "All",
				"total_results": len(table),
				"by_status": by_status,
				"work_orders": table,
			}
		)

		summary = f"Work orders: {format_number(len(table))} result(s) (status={status or 'All'})."
		return {"data": data, "summary": summary, "table": serialize_rows(table)[:20], "_query_source": sql.strip()}

