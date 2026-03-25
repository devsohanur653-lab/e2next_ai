"""material_request_status — Pending Material Requests by type/status.

Maps to ERPNext: Material Request list / MR pending reports.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class MaterialRequestStatusTool(MCPTool):
	name = "material_request_status"
	description = "Get pending Material Requests by type and status."
	parameters = {
		"company": {"type": "str", "required": False},
		"material_request_type": {"type": "str", "required": False, "description": "Purchase/Material Transfer/Manufacture"},
		"warehouse": {"type": "str", "required": False, "description": "Filter by set_warehouse (optional)"},
		"limit": {"type": "int", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Material Request")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		mr_type = kwargs.get("material_request_type")
		warehouse = kwargs.get("warehouse")
		limit = int(kwargs.get("limit") or 50)

		conditions = ["mr.docstatus = 1", "mr.status NOT IN ('Stopped', 'Cancelled', 'Completed')"]
		values: list[Any] = []
		if company:
			conditions.append("mr.company = %s")
			values.append(company)
		if mr_type:
			conditions.append("mr.material_request_type = %s")
			values.append(mr_type)
		if warehouse:
			conditions.append("mr.set_warehouse = %s")
			values.append(warehouse)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				mr.name,
				mr.material_request_type,
				mr.status,
				mr.transaction_date,
				mr.schedule_date,
				mr.set_warehouse,
				mr.company,
				COUNT(mri.name) AS item_count
			FROM `tabMaterial Request` mr
			LEFT JOIN `tabMaterial Request Item` mri ON mri.parent = mr.name
			WHERE {where}
			GROUP BY mr.name, mr.material_request_type, mr.status, mr.transaction_date, mr.schedule_date, mr.set_warehouse, mr.company
			ORDER BY mr.transaction_date DESC, mr.modified DESC
			LIMIT %s
		"""
		rows = frappe.db.sql(sql, (*values, limit), as_dict=True)
		table = []
		for r in rows:
			table.append(
				{
					"name": r.name,
					"material_request_type": r.material_request_type or "",
					"status": r.status or "",
					"transaction_date": str(r.transaction_date) if r.transaction_date else "",
					"schedule_date": str(r.schedule_date) if r.schedule_date else "",
					"warehouse": r.set_warehouse or "",
					"company": r.company or "",
					"item_count": int(r.item_count or 0),
				}
			)

		# counts by status
		counts: dict[str, int] = {}
		for r in table:
			s = r["status"] or "Unknown"
			counts[s] = counts.get(s, 0) + 1
		by_status = [{"status": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)]

		data = serialize(
			{
				"company": company or "All",
				"material_request_type": mr_type or "All",
				"warehouse": warehouse or "All",
				"total_pending": len(table),
				"by_status": by_status,
				"material_requests": table,
			}
		)
		summary = f"Pending Material Requests: {format_number(len(table))} (type={mr_type or 'All'})."
		return {
			"data": data,
			"summary": summary,
			"table": serialize_rows(by_status, numeric_fields=["count"]),
			"_query_source": sql.strip(),
		}

