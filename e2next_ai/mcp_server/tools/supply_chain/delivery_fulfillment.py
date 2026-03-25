"""delivery_fulfillment — Sales Orders pending delivery / partial delivery.

Maps to ERPNext: Sales Order list / Delivery Note Trends.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class DeliveryFulfillmentTool(MCPTool):
	name = "delivery_fulfillment"
	description = "Get Sales Orders pending delivery (not delivered/partially delivered) for a date range."
	parameters = {
		"company": {"type": "str", "required": False},
		"customer": {"type": "str", "required": False},
		"from_date": {"type": "str", "required": False},
		"to_date": {"type": "str", "required": False},
		"limit": {"type": "int", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Sales Order")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		customer = kwargs.get("customer")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		limit = int(kwargs.get("limit") or 50)

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
			"so.docstatus = 1",
			"so.transaction_date BETWEEN %s AND %s",
			"COALESCE(so.per_delivered, 0) < 99.99",
			"so.status NOT IN ('Closed', 'Completed', 'Cancelled')",
		]
		values: list[Any] = [from_date, to_date]

		if company:
			conditions.append("so.company = %s")
			values.append(company)
		if customer:
			conditions.append("so.customer = %s")
			values.append(customer)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				so.name,
				so.customer,
				so.customer_name,
				so.transaction_date,
				so.delivery_date,
				so.grand_total,
				so.per_delivered,
				COUNT(soi.name) AS item_count
			FROM `tabSales Order` so
			LEFT JOIN `tabSales Order Item` soi ON soi.parent = so.name
			WHERE {where}
			GROUP BY so.name, so.customer, so.customer_name, so.transaction_date, so.delivery_date, so.grand_total, so.per_delivered
			ORDER BY so.delivery_date ASC, so.transaction_date DESC
			LIMIT %s
		"""
		rows = frappe.db.sql(sql, (*values, limit), as_dict=True)

		table = []
		total_value = 0.0
		for r in rows:
			val = float(r.grand_total or 0)
			total_value += val
			table.append(
				{
					"sales_order": r.name,
					"customer": r.customer,
					"customer_name": r.customer_name or "",
					"transaction_date": str(r.transaction_date) if r.transaction_date else "",
					"delivery_date": str(r.delivery_date) if r.delivery_date else "",
					"grand_total": val,
					"percent_delivered": float(r.per_delivered or 0),
					"item_count": int(r.item_count or 0),
				}
			)

		data = serialize(
			{
				"company": company or "All",
				"customer": customer or "All",
				"from_date": from_date,
				"to_date": to_date,
				"total_pending_orders": len(table),
				"total_value": total_value,
				"orders": table,
			}
		)

		summary = (
			f"Delivery pending ({from_date} to {to_date}): "
			f"{format_number(len(table))} sales orders, total {format_currency(total_value)}."
		)
		return {"data": data, "summary": summary, "table": serialize_rows(table)[:20], "_query_source": sql.strip()}

