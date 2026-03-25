"""payroll_entry_status — Payroll runs status for a period.

Maps to ERPNext: Payroll Entry.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class PayrollEntryStatusTool(MCPTool):
	name = "payroll_entry_status"
	description = "Get Payroll Entry runs status (submitted/paid/pending) for a date range."
	parameters = {
		"company": {"type": "str", "required": False},
		"from_date": {"type": "str", "required": False},
		"to_date": {"type": "str", "required": False},
		"limit": {"type": "int", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		if not frappe.db.exists("DocType", "Payroll Entry"):
			raise ValueError("Payroll doctypes not found (Payroll Entry). Enable Payroll in ERPNext.")

		check_doctype_permission("Payroll Entry")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
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

		conditions = ["pe.docstatus < 2", "pe.start_date >= %s", "pe.end_date <= %s"]
		values: list[Any] = [from_date, to_date]
		if company:
			conditions.append("pe.company = %s")
			values.append(company)
		where = " AND ".join(conditions)

		sql = f"""
			SELECT
				pe.name,
				pe.payroll_frequency,
				pe.start_date,
				pe.end_date,
				pe.status,
				pe.posting_date,
				pe.company
			FROM `tabPayroll Entry` pe
			WHERE {where}
			ORDER BY pe.posting_date DESC, pe.modified DESC
			LIMIT %s
		"""
		rows = frappe.db.sql(sql, (*values, limit), as_dict=True)

		table = []
		for r in rows:
			table.append(
				{
					"name": r.name,
					"status": r.status or "",
					"payroll_frequency": r.payroll_frequency or "",
					"start_date": str(r.start_date),
					"end_date": str(r.end_date),
					"posting_date": str(r.posting_date) if r.posting_date else "",
					"company": r.company or "",
				}
			)

		# Status counts
		counts: dict[str, int] = {}
		for r in table:
			s = r["status"] or "Unknown"
			counts[s] = counts.get(s, 0) + 1

		count_table = [{"status": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)]

		data = serialize(
			{
				"company": company or "All",
				"from_date": from_date,
				"to_date": to_date,
				"total_entries": len(table),
				"by_status": count_table,
				"entries": table,
			}
		)

		summary = f"Payroll entries ({from_date} to {to_date}): {format_number(len(table))} runs."
		return {"data": data, "summary": summary, "table": serialize_rows(count_table, numeric_fields=['count']), "_query_source": sql.strip()}

