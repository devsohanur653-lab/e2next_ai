"""leave_summary — Leaves by status for a period.

Maps to ERPNext: Leave Details Report / Leave Application list.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class LeaveSummaryTool(MCPTool):
	name = "leave_summary"
	description = "Get leave applications summary (approved/pending/rejected) for a date range."
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name (optional)"},
		"department": {"type": "str", "required": False, "description": "Filter by department (optional)"},
		"from_date": {"type": "str", "required": False, "description": "Start date (YYYY-MM-DD) or natural language"},
		"to_date": {"type": "str", "required": False, "description": "End date (YYYY-MM-DD)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		check_doctype_permission("Leave Application")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		department = kwargs.get("department")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")

		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		if not from_date or not to_date:
			parsed = parse_date_range("this month")
			assert parsed is not None
			from_date = from_date or parsed[0]
			to_date = to_date or parsed[1]

		conditions = ["la.docstatus < 2", "la.from_date <= %s AND la.to_date >= %s"]
		values: list[Any] = [to_date, from_date]

		if company:
			conditions.append("la.company = %s")
			values.append(company)
		if department:
			conditions.append("la.department = %s")
			values.append(department)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				la.status,
				COUNT(*) AS application_count,
				COUNT(DISTINCT la.employee) AS unique_employees
			FROM `tabLeave Application` la
			WHERE {where}
			GROUP BY la.status
			ORDER BY application_count DESC
		"""
		rows = frappe.db.sql(sql, tuple(values), as_dict=True)
		table = serialize_rows(rows, numeric_fields=["application_count", "unique_employees"])
		total = sum(int(r["application_count"]) for r in table) if table else 0

		data = serialize(
			{
				"from_date": from_date,
				"to_date": to_date,
				"company": company or "All",
				"department": department or "All",
				"total_applications": total,
				"by_status": table,
			}
		)

		summary = f"Leave applications from {from_date} to {to_date}: {format_number(total)} total."
		return {"data": data, "summary": summary, "table": table, "_query_source": sql.strip()}

