"""Answer formatter for MCP tool responses.

Produces human-readable output:
- Short summary line ("Sales this month: ৳ 12,45,000 across 38 invoices")
- Key numbers block (3-5 most important metrics)
- Optional table (top 5-10 rows)
- Locale-aware number formatting (BDT, USD, etc.)
- Respects user's preferred currency from ERPNext settings
"""

from __future__ import annotations

from typing import Any

import frappe


def get_default_currency() -> str:
	"""Get the default currency from ERPNext Company settings."""
	try:
		company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default(
			"company"
		)
		if company:
			return frappe.get_cached_value("Company", company, "default_currency") or "USD"
	except Exception:
		pass
	return "USD"


def get_currency_symbol(currency: str | None = None) -> str:
	"""Get the symbol for a currency code."""
	currency = currency or get_default_currency()
	symbols = {
		"USD": "$",
		"BDT": "৳",
		"INR": "₹",
		"EUR": "€",
		"GBP": "£",
		"JPY": "¥",
		"CNY": "¥",
		"AUD": "A$",
		"CAD": "C$",
		"SGD": "S$",
		"AED": "AED",
		"SAR": "SAR",
		"MYR": "RM",
		"PKR": "₨",
		"LKR": "Rs",
		"NPR": "₨",
	}
	return symbols.get(currency, currency)


def format_currency(amount: float | int, currency: str | None = None) -> str:
	"""Format a number as currency with locale-aware formatting.

	Uses Indian numbering (12,45,000) for BDT/INR/PKR/NPR/LKR.
	Uses Western numbering (1,245,000) for others.
	"""
	currency = currency or get_default_currency()
	symbol = get_currency_symbol(currency)

	# Indian-style numbering for South Asian currencies
	indian_currencies = {"BDT", "INR", "PKR", "NPR", "LKR"}

	if currency in indian_currencies:
		formatted = _format_indian(amount)
	else:
		formatted = _format_western(amount)

	return f"{symbol} {formatted}"


def format_number(value: float | int, decimals: int = 0) -> str:
	"""Format a plain number with thousand separators."""
	if decimals > 0:
		return f"{value:,.{decimals}f}"
	if isinstance(value, float) and value != int(value):
		return f"{value:,.2f}"
	return f"{int(value):,}"


def format_summary(text: str, **numbers: float | int) -> str:
	"""Build a summary line, auto-formatting any currency values.

	Example:
		format_summary(
			"Sales this month: {total} across {count} invoices",
			total=1245000,
			count=38,
		)
	"""
	formatted = {}
	currency = get_default_currency()
	for key, val in numbers.items():
		if key.startswith("currency_") or key in ("total", "amount", "revenue", "outstanding", "collected"):
			formatted[key] = format_currency(val, currency)
		else:
			formatted[key] = format_number(val)
	return text.format(**formatted)


def format_key_numbers(metrics: dict[str, Any], currency_keys: list[str] | None = None) -> str:
	"""Format 3-5 key metrics as a readable block.

	Args:
		metrics: Dict of metric_label -> value
		currency_keys: Which keys should be formatted as currency
	"""
	currency_fields = set(currency_keys or [])
	currency = get_default_currency()
	lines = []

	for label, value in metrics.items():
		if label in currency_fields or (isinstance(value, (int, float)) and value > 1000 and label in currency_fields):
			formatted = format_currency(value, currency)
		elif isinstance(value, (int, float)):
			formatted = format_number(value)
		else:
			formatted = str(value)
		lines.append(f"  {label}: {formatted}")

	return "\n".join(lines)


def format_table(
	rows: list[dict],
	columns: list[str] | None = None,
	currency_columns: list[str] | None = None,
	max_rows: int = 10,
) -> list[dict[str, Any]]:
	"""Format tabular data for display, limiting to max_rows.

	Args:
		rows: List of row dicts
		columns: Column names to include (None = all)
		currency_columns: Columns to format as currency
		max_rows: Maximum rows to return (default 10)
	"""
	if not rows:
		return []

	currency_cols = set(currency_columns or [])
	currency = get_default_currency()
	result = []

	for row in rows[:max_rows]:
		formatted_row = {}
		keys = columns or list(row.keys())
		for col in keys:
			val = row.get(col)
			if col in currency_cols and isinstance(val, (int, float)):
				formatted_row[col] = format_currency(val, currency)
			elif isinstance(val, float):
				formatted_row[col] = format_number(val, 2)
			else:
				formatted_row[col] = val
		result.append(formatted_row)

	return result


# ── Internal helpers ───────────────────────────────────────────────


def _format_indian(amount: float | int) -> str:
	"""Format number in Indian numbering system (12,45,000)."""
	if amount < 0:
		return "-" + _format_indian(-amount)

	is_float = isinstance(amount, float) and amount != int(amount)
	if is_float:
		integer_part = int(amount)
		decimal_part = f"{amount - integer_part:.2f}"[1:]  # ".XX"
	else:
		integer_part = int(amount)
		decimal_part = ""

	s = str(integer_part)
	if len(s) <= 3:
		result = s
	else:
		result = s[-3:]
		s = s[:-3]
		while s:
			result = s[-2:] + "," + result
			s = s[:-2]

	return result + decimal_part


def _format_western(amount: float | int) -> str:
	"""Format number in Western numbering system (1,245,000)."""
	if isinstance(amount, float) and amount != int(amount):
		return f"{amount:,.2f}"
	return f"{int(amount):,}"
