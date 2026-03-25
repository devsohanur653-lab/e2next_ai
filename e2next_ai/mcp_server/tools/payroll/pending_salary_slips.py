"""pending_salary_slips — Draft/unsubmitted salary slips needing action."""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class PendingSalarySlipsTool(MCPTool):
	name = "pending_salary_slips"
	description = "List draft/unsubmitted salary slips for a period (pending submission/approval)."
	parameters = {
		"company": {"type": "str", "required": False},
		"from_date": {"type": "str", "required": False},
		"to_date": {"type": "str", "required": False},
		"month": {"type": "int", "required": False},
		"year": {"type": "int", "required": False},
		"limit": {"type": "int", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		if not frappe.db.exists("DocType", "Salary Slip"):
			raise ValueError("Payroll doctypes not found (Salary Slip). Enable Payroll in ERPNext.")

		check_doctype_permission("Salary Slip")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		month = kwargs.get("month")
		year = kwargs.get("year")
		limit = int(kwargs.get("limit") or 50)

		if month and year and not from_date and not to_date:
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

		conditions = ["ss.docstatus = 0", "ss.start_date >= %s", "ss.end_date <= %s"]
		values: list[Any] = [from_date, to_date]
		if company:
			conditions.append("ss.company = %s")
			values.append(company)
		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				ss.name,
				ss.employee,
				ss.employee_name,
				ss.start_date,
				ss.end_date,
				ss.gross_pay,
				ss.total_deduction,
				ss.net_pay
			FROM `tabSalary Slip` ss
			WHERE {where}
			ORDER BY ss.modified DESC
			LIMIT %s
		"""
		rows = frappe.db.sql(sql, (*values, limit), as_dict=True)
		table = []
		total_net = 0.0
		for r in rows:
			net = float(r.net_pay or 0)
			total_net += net
			table.append(
				{
					"name": r.name,
					"employee": r.employee,
					"employee_name": r.employee_name or "",
					"start_date": str(r.start_date),
					"end_date": str(r.end_date),
					"gross_pay": float(r.gross_pay or 0),
					"total_deduction": float(r.total_deduction or 0),
					"net_pay": net,
				}
			)

		out_table = serialize_rows(
			table, numeric_fields=["gross_pay", "total_deduction", "net_pay"]
		)
		data = serialize(
			{
				"company": company or "All",
				"from_date": from_date,
				"to_date": to_date,
				"total_pending": len(table),
				"total_net": total_net,
				"salary_slips": table,
			}
		)
		summary = f"Pending salary slips: {format_number(len(table))} drafts, total net {format_currency(total_net)}."
		return {"data": data, "summary": summary, "table": out_table[:20], "_query_source": sql.strip()}

