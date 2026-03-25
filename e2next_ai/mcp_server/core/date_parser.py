"""Natural language date range parser for ERPNext MCP tools.

Converts phrases like "this month", "last quarter", "FY 2024-25" into
(from_date, to_date) tuples in YYYY-MM-DD format.

Supports ERPNext fiscal year settings (not always Jan–Dec).
"""

from __future__ import annotations

import re
from datetime import date, timedelta

import frappe


def parse_date_range(text: str) -> tuple[str, str] | None:
	"""Parse a natural language date phrase into (from_date, to_date).

	Returns None if the text cannot be parsed — caller should ask the user.
	"""
	if not text:
		return None

	text = text.strip().lower()

	today = date.today()

	# Exact date pattern: YYYY-MM-DD
	iso_match = re.match(r"^(\d{4}-\d{2}-\d{2})$", text)
	if iso_match:
		d = iso_match.group(1)
		return (d, d)

	# Date range: YYYY-MM-DD to YYYY-MM-DD
	range_match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})$", text)
	if range_match:
		return (range_match.group(1), range_match.group(2))

	# "today"
	if text == "today":
		d = today.isoformat()
		return (d, d)

	# "yesterday"
	if text == "yesterday":
		d = (today - timedelta(days=1)).isoformat()
		return (d, d)

	# "this week" (Mon–Sun of current week)
	if text == "this week":
		monday = today - timedelta(days=today.weekday())
		sunday = monday + timedelta(days=6)
		return (monday.isoformat(), sunday.isoformat())

	# "last week" (Mon–Sun of previous week)
	if text == "last week":
		monday = today - timedelta(days=today.weekday() + 7)
		sunday = monday + timedelta(days=6)
		return (monday.isoformat(), sunday.isoformat())

	# "this month"
	if text == "this month":
		first = today.replace(day=1)
		last = _last_day_of_month(today)
		return (first.isoformat(), last.isoformat())

	# "last month"
	if text == "last month":
		first_this = today.replace(day=1)
		last_prev = first_this - timedelta(days=1)
		first_prev = last_prev.replace(day=1)
		return (first_prev.isoformat(), last_prev.isoformat())

	# "last N days"
	last_n_match = re.match(r"^last\s+(\d+)\s+days?$", text)
	if last_n_match:
		n = int(last_n_match.group(1))
		from_d = today - timedelta(days=n)
		return (from_d.isoformat(), today.isoformat())

	# "this quarter"
	if text == "this quarter":
		return _get_fiscal_quarter(today)

	# "last quarter"
	if text == "last quarter":
		# Go back 3 months from start of current quarter
		qstart, _ = _get_fiscal_quarter(today)
		qstart_date = date.fromisoformat(qstart)
		prev_q_end = qstart_date - timedelta(days=1)
		return _get_fiscal_quarter(prev_q_end)

	# "this year" / "this fiscal year" / "current year"
	if text in ("this year", "this fiscal year", "current year", "current fiscal year"):
		return _get_current_fiscal_year()

	# "last year" / "last fiscal year" / "previous year"
	if text in ("last year", "last fiscal year", "previous year", "previous fiscal year"):
		return _get_previous_fiscal_year()

	# "FY 2024-25" or "FY 2024" or "FY2024-25"
	fy_match = re.match(r"^fy\s*(\d{4})(?:-(\d{2,4}))?$", text)
	if fy_match:
		return _get_named_fiscal_year(fy_match.group(0).upper().replace("FY ", "FY "))

	# Could not parse
	return None


# ── Helpers ────────────────────────────────────────────────────────


def _last_day_of_month(d: date) -> date:
	"""Return the last day of the month for the given date."""
	if d.month == 12:
		return d.replace(day=31)
	return d.replace(month=d.month + 1, day=1) - timedelta(days=1)


def _get_fiscal_year_dates() -> tuple[int, int]:
	"""Return (start_month, start_day) from ERPNext System Settings.

	Defaults to (1, 1) — January 1 — if not configured.
	"""
	try:
		fy = frappe.defaults.get_global_default("fiscal_year")
		if fy and frappe.db.exists("Fiscal Year", fy):
			doc = frappe.get_doc("Fiscal Year", fy)
			start = doc.year_start_date
			if start:
				return (start.month, start.day)
	except Exception:
		pass
	return (1, 1)


def _get_current_fiscal_year() -> tuple[str, str]:
	"""Return (from_date, to_date) for the current fiscal year."""
	try:
		fy_name = frappe.defaults.get_global_default("fiscal_year")
		if fy_name and frappe.db.exists("Fiscal Year", fy_name):
			doc = frappe.get_doc("Fiscal Year", fy_name)
			return (str(doc.year_start_date), str(doc.year_end_date))
	except Exception:
		pass

	# Fallback: calendar year
	today = date.today()
	return (date(today.year, 1, 1).isoformat(), date(today.year, 12, 31).isoformat())


def _get_previous_fiscal_year() -> tuple[str, str]:
	"""Return (from_date, to_date) for the previous fiscal year."""
	try:
		current_fy = frappe.defaults.get_global_default("fiscal_year")
		if current_fy:
			# Get all fiscal years ordered by start date
			all_fys = frappe.get_all(
				"Fiscal Year",
				fields=["name", "year_start_date", "year_end_date"],
				order_by="year_start_date desc",
			)
			found_current = False
			for fy in all_fys:
				if found_current:
					return (str(fy.year_start_date), str(fy.year_end_date))
				if fy.name == current_fy:
					found_current = True
	except Exception:
		pass

	# Fallback: previous calendar year
	today = date.today()
	prev = today.year - 1
	return (date(prev, 1, 1).isoformat(), date(prev, 12, 31).isoformat())


def _get_named_fiscal_year(text: str) -> tuple[str, str] | None:
	"""Look up a fiscal year by name like 'FY 2024-25' or '2024-2025'."""
	# Try common naming patterns
	patterns = [text]

	# Extract year digits
	year_match = re.search(r"(\d{4})(?:-(\d{2,4}))?", text)
	if year_match:
		y1 = year_match.group(1)
		y2 = year_match.group(2)
		if y2 and len(y2) == 2:
			y2_full = y1[:2] + y2
			patterns.extend([f"{y1}-{y2}", f"{y1}-{y2_full}"])
		elif y2:
			patterns.extend([f"{y1}-{y2}", f"{y1}-{y2[-2:]}"])
		else:
			patterns.append(y1)

	for pattern in patterns:
		fys = frappe.get_all(
			"Fiscal Year",
			filters={"name": ("like", f"%{pattern}%")},
			fields=["year_start_date", "year_end_date"],
			limit=1,
		)
		if fys:
			return (str(fys[0].year_start_date), str(fys[0].year_end_date))

	return None


def _get_fiscal_quarter(d: date) -> tuple[str, str]:
	"""Return (from_date, to_date) for the fiscal quarter containing date `d`."""
	fy_start_month, fy_start_day = _get_fiscal_year_dates()

	# Calculate quarter boundaries based on fiscal year start
	# Quarters are 3 months each starting from fiscal year start month
	q_starts = []
	for i in range(4):
		m = ((fy_start_month - 1 + i * 3) % 12) + 1
		q_starts.append(m)

	# Find which quarter contains date d
	for i in range(3, -1, -1):
		q_month = q_starts[i]
		# Determine the year for this quarter start
		if q_month >= fy_start_month:
			q_year = d.year if d.month >= fy_start_month else d.year - 1
		else:
			q_year = d.year if d.month < fy_start_month else d.year + 1

		q_start = date(q_year, q_month, fy_start_day if i == 0 else 1)
		if d >= q_start:
			# End of quarter: start of next quarter minus 1 day
			next_q_month = q_starts[(i + 1) % 4]
			if (i + 1) % 4 == 0:
				next_q_year = q_year + 1
			else:
				next_q_year = q_year + (1 if next_q_month < q_month else 0)
			q_end = date(next_q_year, next_q_month, 1) - timedelta(days=1)
			return (q_start.isoformat(), q_end.isoformat())

	# Fallback: first quarter
	q_start = date(d.year, fy_start_month, fy_start_day)
	q_end_month = ((fy_start_month - 1 + 3) % 12) + 1
	q_end_year = d.year + (1 if q_end_month < fy_start_month else 0)
	q_end = date(q_end_year, q_end_month, 1) - timedelta(days=1)
	return (q_start.isoformat(), q_end.isoformat())
