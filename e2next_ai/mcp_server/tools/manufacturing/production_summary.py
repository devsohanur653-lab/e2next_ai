"""production_summary — Planned vs produced by period/item.

Uses Work Order created in period as a proxy for planning, and produced_qty as output.
Maps to ERPNext: Production Analytics (approximation).
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class ProductionSummaryTool(MCPTool):
	name = "production_summary"
	description = "Get planned vs produced quantities by item for a date range."
	parameters = {
		"company": {"type": "str", "required": False},
		"from_date": {"type": "str", "required": False},
		"to_date": {"type": "str", "required": False},
		"item_code": {"type": "str", "required": False},
		"limit": {"type": "int", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		if not frappe.db.exists("DocType", "Work Order"):
			raise ValueError("Manufacturing doctypes not found (Work Order). Enable Manufacturing in ERPNext.")

		check_doctype_permission("Work Order")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		item_code = kwargs.get("item_code")
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

		conditions = ["wo.docstatus < 2", "wo.planned_start_date BETWEEN %s AND %s"]
		values: list[Any] = [from_date, to_date]
		if company:
			conditions.append("wo.company = %s")
			values.append(company)
		if item_code:
			conditions.append("wo.production_item = %s")
			values.append(item_code)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				wo.production_item AS item_code,
				wo.item_name,
				SUM(wo.qty) AS planned_qty,
				SUM(wo.produced_qty) AS produced_qty,
				COUNT(*) AS work_order_count
			FROM `tabWork Order` wo
			WHERE {where}
			GROUP BY wo.production_item, wo.item_name
			ORDER BY produced_qty DESC
			LIMIT %s
		"""
		rows = frappe.db.sql(sql, (*values, limit), as_dict=True)

		table = []
		total_planned = 0.0
		total_produced = 0.0
		for r in rows:
			planned = float(r.planned_qty or 0)
			produced = float(r.produced_qty or 0)
			total_planned += planned
			total_produced += produced
			table.append(
				{
					"item_code": r.item_code or "",
					"item_name": r.item_name or "",
					"planned_qty": planned,
					"produced_qty": produced,
					"work_order_count": int(r.work_order_count or 0),
				}
			)

		data = serialize(
			{
				"company": company or "All",
				"from_date": from_date,
				"to_date": to_date,
				"item_code": item_code or "All",
				"total_planned_qty": total_planned,
				"total_produced_qty": total_produced,
				"items": table,
			}
		)
		summary = (
			f"Production ({from_date} to {to_date}): "
			f"{format_number(total_produced)} produced vs {format_number(total_planned)} planned."
		)
		return {"data": data, "summary": summary, "table": serialize_rows(table)[:20], "_query_source": sql.strip()}

