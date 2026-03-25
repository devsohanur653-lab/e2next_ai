"""salary_slip_summary — Total gross/deductions/net for a payroll period.

Maps to ERPNext report: Salary Register (summary).
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_currency, format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize


class SalarySlipSummaryTool(MCPTool):
	name = "salary_slip_summary"
	description = "Get payroll totals from Salary Slips: gross, deductions, net pay, count for a period."
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name (optional)"},
		"from_date": {"type": "str", "required": False, "description": "Start date or natural language (optional)"},
		"to_date": {"type": "str", "required": False, "description": "End date (optional)"},
		"payroll_period": {"type": "str", "required": False, "description": "Payroll Period name (optional)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		if not frappe.db.exists("DocType", "Salary Slip"):
			raise ValueError("Payroll doctypes not found (Salary Slip). Enable Payroll in ERPNext.")

		check_doctype_permission("Salary Slip")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		from_date = kwargs.get("from_date")
		to_date = kwargs.get("to_date")
		payroll_period = kwargs.get("payroll_period")

		# If payroll_period is provided and doctype exists, use its dates
		if payroll_period and frappe.db.exists("DocType", "Payroll Period") and frappe.db.exists("Payroll Period", payroll_period):
			check_doctype_permission("Payroll Period")
			pp = frappe.get_doc("Payroll Period", payroll_period)
			from_date = from_date or str(pp.start_date)
			to_date = to_date or str(pp.end_date)

		if from_date and not to_date:
			parsed = parse_date_range(from_date)
			if parsed:
				from_date, to_date = parsed

		if not from_date or not to_date:
			# Default to this month
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
				COUNT(*) AS total_slips,
				COALESCE(SUM(ss.gross_pay), 0) AS total_gross,
				COALESCE(SUM(ss.total_deduction), 0) AS total_deductions,
				COALESCE(SUM(ss.net_pay), 0) AS total_net,
				COUNT(DISTINCT ss.employee) AS unique_employees
			FROM `tabSalary Slip` ss
			WHERE {where}
		"""
		row = frappe.db.sql(sql, tuple(values), as_dict=True)[0]

		total_slips = int(row.total_slips or 0)
		total_gross = float(row.total_gross or 0)
		total_deductions = float(row.total_deductions or 0)
		total_net = float(row.total_net or 0)

		data = serialize(
			{
				"company": company or "All",
				"from_date": from_date,
				"to_date": to_date,
				"payroll_period": payroll_period or "Auto",
				"total_slips": total_slips,
				"unique_employees": int(row.unique_employees or 0),
				"total_gross": total_gross,
				"total_deductions": total_deductions,
				"total_net": total_net,
			}
		)

		summary = (
			f"Payroll from {from_date} to {to_date}: "
			f"{format_currency(total_net)} net across {format_number(total_slips)} salary slips."
		)

		return {"data": data, "summary": summary, "_query_source": sql.strip()}

