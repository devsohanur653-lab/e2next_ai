"""downtime_summary — Machine downtime summary (if configured).

Best-effort:
- Uses `Downtime Entry` if it exists; otherwise returns a helpful validation error.
"""

from __future__ import annotations

from typing import Any

import frappe

from e2next_ai.mcp_server.core.base_tool import MCPTool
from e2next_ai.mcp_server.core.date_parser import parse_date_range
from e2next_ai.mcp_server.core.formatter import format_number
from e2next_ai.mcp_server.core.permissions import check_doctype_permission
from e2next_ai.mcp_server.core.serializer import serialize, serialize_rows


class DowntimeSummaryTool(MCPTool):
	name = "downtime_summary"
	description = "Get workstation downtime summary for a period (requires Downtime Entry)."
	parameters = {
		"company": {"type": "str", "required": False},
		"workstation": {"type": "str", "required": False},
		"from_date": {"type": "str", "required": False},
		"to_date": {"type": "str", "required": False},
	}

	def run(self, **kwargs: Any) -> dict[str, Any]:
		if not frappe.db.exists("DocType", "Downtime Entry"):
			raise ValueError("Downtime Entry doctype not found. Enable Manufacturing > Maintenance/OEE features if available.")

		check_doctype_permission("Downtime Entry")

		company = kwargs.get("company") or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		workstation = kwargs.get("workstation")
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

		# Date field varies by implementation; use one that exists.
		date_candidates = ["posting_date", "start_time", "from_time", "creation"]
		date_field = next((f for f in date_candidates if frappe.db.has_column("Downtime Entry", f)), None)
		if not date_field:
			raise ValueError(
				"Downtime Entry is missing a date field (expected one of: "
				+ ", ".join(date_candidates)
				+ ")."
			)

		# If the date field is datetime, we still accept YYYY-MM-DD boundaries.
		conditions = ["de.docstatus = 1", f"de.{date_field} BETWEEN %s AND %s"]
		values: list[Any] = [from_date, to_date]
		if company and frappe.db.has_column("Downtime Entry", "company"):
			conditions.append("de.company = %s")
			values.append(company)
		if workstation:
			conditions.append("de.workstation = %s")
			values.append(workstation)
		where = " AND ".join(conditions)

		# Different ERPNext versions/implementations use different field names for minutes.
		# Try a safe, common set and pick the first that exists.
		candidates = ["downtime_in_mins", "downtime_in_minutes", "downtime_minutes", "downtime"]
		mins_field = next((f for f in candidates if frappe.db.has_column("Downtime Entry", f)), None)
		if not mins_field:
			raise ValueError(
				"Downtime Entry is missing a downtime minutes field (expected one of: "
				+ ", ".join(candidates)
				+ ")."
			)

		sql = f"""
			SELECT
				de.workstation,
				COUNT(*) AS entry_count,
				COALESCE(SUM(de.{mins_field}), 0) AS downtime_mins
			FROM `tabDowntime Entry` de
			WHERE {where}
			GROUP BY de.workstation
			ORDER BY downtime_mins DESC
			LIMIT 50
		"""
		rows = frappe.db.sql(sql, tuple(values), as_dict=True)

		table = []
		total_mins = 0.0
		for r in rows:
			m = float(r.downtime_mins or 0)
			total_mins += m
			table.append(
				{
					"workstation": r.workstation or "Not Set",
					"entry_count": int(r.entry_count or 0),
					"downtime_mins": m,
				}
			)

		data = serialize(
			{
				"company": company or "All",
				"workstation": workstation or "All",
				"from_date": from_date,
				"to_date": to_date,
				"total_downtime_mins": total_mins,
				"by_workstation": table,
			}
		)
		summary = f"Downtime ({from_date} to {to_date}): {format_number(total_mins)} minutes total."
		return {"data": data, "summary": summary, "table": serialize_rows(table)[:20], "_query_source": sql.strip()}

