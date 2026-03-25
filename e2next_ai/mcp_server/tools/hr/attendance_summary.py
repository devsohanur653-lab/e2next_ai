"""attendance_summary — Attendance counts for a period.

Maps to ERPNext: Employee Attendance Summary / Monthly Attendance Sheet.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class AttendanceSummaryTool(MCPTool):
	name = "attendance_summary"
	description = "Get attendance summary (present/absent/leave/etc.) for a date range."
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name (optional)"},
		"department": {"type": "str", "required": False, "description": "Filter by department (optional)"},
		"from_date": {"type": "str", "required": False, "description": "Start date (YYYY-MM-DD) or natural language"},
		"to_date": {"type": "str", "required": False, "description": "End date (YYYY-MM-DD)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Attendance")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		department = kwargs.get("department")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")

		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		if not from_date or not to_date:
			# Default: this month
			parsed = parse_date_range("this month")
			assert parsed is not None
			from_date = from_date or parsed[0]
			to_date = to_date or parsed[1]

		conditions = ["a.docstatus = 1", "a.attendance_date BETWEEN %s AND %s"]
		values: list[Any] = [from_date, to_date]

		if company:
			conditions.append("a.company = %s")
			values.append(company)
		if department:
			conditions.append("a.department = %s")
			values.append(department)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				a.status,
				COUNT(*) AS count_rows,
				COUNT(DISTINCT a.employee) AS unique_employees
			FROM `tabAttendance` a
			WHERE {where}
			GROUP BY a.status
			ORDER BY count_rows DESC
		"""
		rows = frappe.db.sql(sql, tuple(values), as_dict=True)
		table = serialize_rows(rows, numeric_fields=["count_rows", "unique_employees"])

		total = sum(int(r["count_rows"]) for r in table) if table else 0

		data = serialize(
			{
				"from_date": from_date,
				"to_date": to_date,
				"company": company or "All",
				"department": department or "All",
				"total_records": total,
				"by_status": table,
			}
		)

		summary = f"Attendance from {from_date} to {to_date}: {format_number(total)} records."
		return {"data": data, "summary": summary, "table": table, "_query_source": sql.strip()}

