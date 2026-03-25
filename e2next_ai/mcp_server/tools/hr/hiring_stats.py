"""hiring_stats — Recruitment snapshot.

Maps to ERPNext: Job Opening / Job Applicant / Recruitment Analytics.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class HiringStatsTool(MCPTool):
	name = "hiring_stats"
	description = "Get hiring/recruitment stats: open job openings and applicant counts."
	parameters = {
		"company": {"type": "str", "required": False, "description": "Company name (optional)"},
		"department": {"type": "str", "required": False, "description": "Filter by department (optional)"},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		# These doctypes may not exist if HR/Recruitment isn't installed/enabled.
		if not frappe.db.exists("DocType", "Job Opening") or not frappe.db.exists("DocType", "Job Applicant"):
			raise ValueError("Recruitment doctypes not found (Job Opening / Job Applicant). Enable HR/Recruitment in ERPNext.")

		check_doctype_permission("Job Opening")
		check_doctype_permission("Job Applicant")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		department = kwargs.get("department")

		conditions = ["jo.docstatus < 2"]
		values: list[Any] = []
		if company:
			conditions.append("jo.company = %s")
			values.append(company)
		if department:
			conditions.append("jo.department = %s")
			values.append(department)

		where = " AND ".join(conditions)

		sql_openings = f"""
			SELECT
				SUM(CASE WHEN jo.status IN ('Open', 'In Progress') THEN 1 ELSE 0 END) AS open_openings,
				COUNT(*) AS total_openings
			FROM `tabJob Opening` jo
			WHERE {where}
		"""
		openings = frappe.db.sql(sql_openings, tuple(values), as_dict=True)[0]

		sql_applicants = """
			SELECT
				ja.status,
				COUNT(*) AS applicant_count
			FROM `tabJob Applicant` ja
			WHERE ja.docstatus < 2
			GROUP BY ja.status
			ORDER BY applicant_count DESC
		"""
		app_rows = frappe.db.sql(sql_applicants, as_dict=True)
		app_table = serialize_rows(app_rows, numeric_fields=["applicant_count"])
		total_applicants = sum(int(r["applicant_count"]) for r in app_table) if app_table else 0

		data = serialize(
			{
				"company": company or "All",
				"department": department or "All",
				"total_openings": int(openings.total_openings or 0),
				"open_openings": int(openings.open_openings or 0),
				"total_applicants": total_applicants,
				"applicants_by_status": app_table,
			}
		)

		summary = (
			f"Hiring: {format_number(int(openings.open_openings or 0))} open openings "
			f"({format_number(int(openings.total_openings or 0))} total). "
			f"Applicants: {format_number(total_applicants)}."
		)

		return {"data": data, "summary": summary, "table": app_table[:20], "_query_source": sql_openings.strip()}

