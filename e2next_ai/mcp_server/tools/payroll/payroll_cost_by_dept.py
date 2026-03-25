"""payroll_cost_by_dept — Payroll cost breakdown per department.

Maps to ERPNext: Salary Register (grouped by department).
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class PayrollCostByDeptTool(MCPTool):
	name = "payroll_cost_by_dept"
	description = "Get payroll net pay totals grouped by department for a period."
	parameters = {
		"company": {"type": "str", "required": False},
		"from_date": {"type": "str", "required": False, "description": "Start date or natural language"},
		"to_date": {"type": "str", "required": False, "description": "End date"},
		"month": {"type": "int", "required": False, "description": "Month number (1-12), optional"},
		"year": {"type": "int", "required": False, "description": "Year (YYYY), optional"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		if not frappe.db.exists("DocType", "Salary Slip"):
			raise ValueError("Payroll doctypes not found (Salary Slip). Enable Payroll in ERPNext.")

		check_doctype_permission("Salary Slip")
		check_doctype_permission("Employee")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		month = kwargs.get("month")
		year = kwargs.get("year")

		if month and year and not from_date and not to_date:
			# Build month range
			import calendar
			from_date = f"{int(year):04d}-{int(month):02d}-01"
			to_date = f"{int(year):04d}-{int(month):02d}-{calendar.monthrange(int(year), int(month))[1]}"

		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		if not from_date or not to_date:
			parsed = parse_date_range("this month")
			assert parsed is not None
			from_date = from_date or parsed[0]
			to_date = to_date or parsed[1]

		conditions = ["ss.docstatus = 1", "ss.start_date >= %s", "ss.end_date <= %s"]
		values: list[Any] = [from_date, to_date]
		if company:
			conditions.append("ss.company = %s")
			values.append(company)

		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				COALESCE(e.department, 'Not Set') AS department,
				COUNT(*) AS slip_count,
				COUNT(DISTINCT ss.employee) AS employee_count,
				COALESCE(SUM(ss.net_pay), 0) AS total_net,
				COALESCE(SUM(ss.gross_pay), 0) AS total_gross,
				COALESCE(SUM(ss.total_deduction), 0) AS total_deductions
			FROM `tabSalary Slip` ss
			JOIN `tabEmployee` e ON e.name = ss.employee
			WHERE {where}
			GROUP BY COALESCE(e.department, 'Not Set')
			ORDER BY total_net DESC
			LIMIT 50
		"""
		rows = frappe.db.sql(sql, tuple(values), as_dict=True)

		table = []
		for r in rows:
			table.append(
				{
					"department": r.department or "Not Set",
					"slip_count": int(r.slip_count or 0),
					"employee_count": int(r.employee_count or 0),
					"total_net": float(r.total_net or 0),
					"total_gross": float(r.total_gross or 0),
					"total_deductions": float(r.total_deductions or 0),
				}
			)

		total_net = sum(x["total_net"] for x in table)
		data = serialize(
			{
				"company": company or "All",
				"from_date": from_date,
				"to_date": to_date,
				"total_departments": len(table),
				"total_net": total_net,
				"departments": table,
			}
		)

		out_table = serialize_rows(table, numeric_fields=["slip_count", "employee_count", "total_net", "total_gross", "total_deductions"])

		summary = f"Payroll cost by department ({from_date} to {to_date}): total net {format_currency(total_net)}."
		return {"data": data, "summary": summary, "table": out_table[:20], "_query_source": sql.strip()}

