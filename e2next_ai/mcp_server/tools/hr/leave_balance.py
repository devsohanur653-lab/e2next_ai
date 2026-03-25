"""leave_balance — Leave balance snapshot per employee/leave type.

Best-effort across ERPNext versions:
- Prefer `Leave Ledger Entry` if available (true balance)
- Fallback to `Leave Allocation` totals (allocation-only view)
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class LeaveBalanceTool(MCPTool):
	name = "leave_balance"
	description = "Get leave balance per employee and leave type (uses Leave Ledger Entry when available)."
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name (optional)"},
		"employee": {"type": "str", "required": False, "description": "Employee ID (optional)"},
		"leave_type": {"type": "str", "required": False, "description": "Leave Type (optional)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		employee = kwargs.get("employee")
		leave_type = kwargs.get("leave_type")

		# Prefer Leave Ledger Entry if present (more accurate balance)
		if frappe.db.exists("DocType", "Leave Ledger Entry"):
			check_doctype_permission("Leave Ledger Entry")

			conditions = ["lle.docstatus = 1"]
			values: list[Any] = []

			if company:
				conditions.append("lle.company = %s")
				values.append(company)
			if employee:
				conditions.append("lle.employee = %s")
				values.append(employee)
			if leave_type:
				conditions.append("lle.leave_type = %s")
				values.append(leave_type)

			where = " AND ".join(conditions)

			sql = f"""
				SELECT
					lle.employee,
					lle.employee_name,
					lle.leave_type,
					COALESCE(SUM(lle.leaves), 0) AS balance
				FROM `tabLeave Ledger Entry` lle
				WHERE {where}
				GROUP BY lle.employee, lle.employee_name, lle.leave_type
				ORDER BY balance DESC
				LIMIT 100
			"""
			rows = frappe.db.sql(sql, tuple(values), as_dict=True)
			table = serialize_rows(rows, numeric_fields=["balance"])

			data = serialize(
				{
					"company": company or "All",
					"employee": employee or "All",
					"leave_type": leave_type or "All",
					"source": "Leave Ledger Entry",
					"rows": table,
				}
			)
			summary = f"Leave balances: {format_number(len(table))} row(s) from Leave Ledger Entry."
			return {"data": data, "summary": summary, "table": table[:20], "_query_source": sql.strip()}

		# Fallback: allocation-only view
		check_doctype_permission("Leave Allocation")

		conditions = ["la.docstatus = 1"]
		values = []
		if company:
			conditions.append("la.company = %s")
			values.append(company)
		if employee:
			conditions.append("la.employee = %s")
			values.append(employee)
		if leave_type:
			conditions.append("la.leave_type = %s")
			values.append(leave_type)

		where = " AND ".join(conditions)
		sql = f"""
			SELECT
				la.employee,
				la.employee_name,
				la.leave_type,
				COALESCE(SUM(la.total_leaves_allocated), 0) AS allocated
			FROM `tabLeave Allocation` la
			WHERE {where}
			GROUP BY la.employee, la.employee_name, la.leave_type
			ORDER BY allocated DESC
			LIMIT 100
		"""
		rows = frappe.db.sql(sql, tuple(values), as_dict=True)
		table = serialize_rows(rows, numeric_fields=["allocated"])
		data = serialize(
			{
				"company": company or "All",
				"employee": employee or "All",
				"leave_type": leave_type or "All",
				"source": "Leave Allocation (allocation-only)",
				"rows": table,
			}
		)
		summary = f"Leave allocations: {format_number(len(table))} row(s) (allocation-only view)."
		return {"data": data, "summary": summary, "table": table[:20], "_query_source": sql.strip()}

