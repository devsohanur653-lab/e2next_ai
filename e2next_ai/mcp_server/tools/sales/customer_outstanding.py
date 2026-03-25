"""customer_outstanding — Get unpaid amount for a customer."""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_currency
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class CustomerOutstandingTool(MCPTool):
	name = "customer_outstanding"
	description = "Get the outstanding (unpaid) amount for a specific customer."
	parameters = {
		"customer_name": {"type": "str", "required": True, "description": "The Customer ID (e.g. 'CUST-0001')"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Sales Invoice")

		customer_name = kwargs.get("customer_name")
		if not customer_name:
			raise ValueError("customer_name is required")

		if not frappe.db.exists("Customer", customer_name):
			raise ValueError(f"Customer {customer_name!r} does not exist")

		result = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(outstanding_amount), 0) AS outstanding
			FROM `tabSales Invoice`
			WHERE customer = %s AND docstatus = 1 AND outstanding_amount > 0
			""",
			(customer_name,),
			as_dict=True,
		)
		outstanding = float(result[0].outstanding) if result else 0.0

		data = serialize({
			"customer_name": customer_name,
			"outstanding_amount": outstanding,
		})

		summary = f"{customer_name}: Outstanding amount is {format_currency(outstanding)}."

		return {"data": data, "summary": summary}
