"""employee_directory — Headcount summary and breakdowns.

Maps to ERPNext: Employee list / HR Analytics.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class EmployeeDirectoryTool(MCPTool):
	name = "employee_directory"
	description = "Get employee headcount totals and breakdown by department/designation (active/left)."
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name (optional)"},
		"department": {"type": "str", "required": False, "description": "Filter by department (optional)"},
		"status": {"type": "str", "required": False, "description": "Employee status filter (optional)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Employee")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		department = kwargs.get("department")
		status = kwargs.get("status")  # e.g. "Active", "Left"

		conditions = ["e.docstatus < 2"]
		values: list[Any] = []

		if company:
			conditions.append("e.company = %s")
			values.append(company)
		if department:
			conditions.append("e.department = %s")
			values.append(department)
		if status:
			conditions.append("e.status = %s")
			values.append(status)

		where = " AND ".join(conditions)

		sql_totals = f"""
			SELECT
				COUNT(*) AS total_employees,
				SUM(CASE WHEN e.status = 'Active' THEN 1 ELSE 0 END) AS active_employees,
				SUM(CASE WHEN e.status = 'Left' THEN 1 ELSE 0 END) AS left_employees
			FROM `tabEmployee` e
			WHERE {where}
		"""
		row = frappe.db.sql(sql_totals, tuple(values), as_dict=True)[0]

		sql_dept = f"""
			SELECT
				COALESCE(e.department, 'Not Set') AS department,
				COUNT(*) AS employee_count,
				SUM(CASE WHEN e.status = 'Active' THEN 1 ELSE 0 END) AS active_count,
				SUM(CASE WHEN e.status = 'Left' THEN 1 ELSE 0 END) AS left_count
			FROM `tabEmployee` e
			WHERE {where}
			GROUP BY COALESCE(e.department, 'Not Set')
			ORDER BY employee_count DESC
			LIMIT 50
		"""
		depts = frappe.db.sql(sql_dept, tuple(values), as_dict=True)

		table = serialize_rows(depts, numeric_fields=["employee_count", "active_count", "left_count"])
		data = serialize(
			{
				"total_employees": int(row.total_employees or 0),
				"active_employees": int(row.active_employees or 0),
				"left_employees": int(row.left_employees or 0),
				"company": company or "All",
				"department": department or "All",
				"status": status or "All",
				"departments": table,
			}
		)

		summary = (
			f"Employees: {format_number(int(row.total_employees or 0))} total "
			f"({format_number(int(row.active_employees or 0))} active, {format_number(int(row.left_employees or 0))} left)."
		)
		if department:
			summary = f"Employees in {department}: {format_number(int(row.total_employees or 0))} total."

		return {"data": data, "summary": summary, "table": table[:20], "_query_source": sql_totals.strip()}

