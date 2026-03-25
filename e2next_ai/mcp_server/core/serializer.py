"""Serialization utilities for MCP tool responses.

Ensures all tool output is json.dumps()-safe by converting:
- Frappe _dict → plain dict
- datetime / date → ISO strings
- Decimal → float
- None → "" or 0 depending on context
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

import frappe


def serialize(obj: Any, null_number: float | int = 0, null_string: str = "") -> Any:
	"""Recursively convert obj into a JSON-serializable structure.

	Args:
		obj: The object to serialize.
		null_number: Value to use for None in numeric contexts (default 0).
		null_string: Value to use for None in string contexts (default "").
	"""
	if obj is None:
		return null_string

	# Frappe _dict → plain dict
	if isinstance(obj, frappe._dict):
		return {k: serialize(v, null_number, null_string) for k, v in obj.items()}

	if isinstance(obj, dict):
		return {k: serialize(v, null_number, null_string) for k, v in obj.items()}

	if isinstance(obj, (list, tuple)):
		return [serialize(v, null_number, null_string) for v in obj]

	# datetime / date → ISO string
	if isinstance(obj, datetime.datetime):
		return obj.isoformat()

	if isinstance(obj, datetime.date):
		return obj.isoformat()

	if isinstance(obj, datetime.time):
		return obj.isoformat()

	if isinstance(obj, datetime.timedelta):
		return str(obj)

	# Decimal → float
	if isinstance(obj, Decimal):
		return float(obj)

	# Primitive types pass through
	if isinstance(obj, (str, int, float, bool)):
		return obj

	# Fallback: convert to string
	return str(obj)


def serialize_rows(rows: list[dict], numeric_fields: list[str] | None = None) -> list[dict]:
	"""Serialize a list of row dicts, converting None in numeric fields to 0.

	Args:
		rows: List of row dicts (e.g. from frappe.db.sql as_dict=True).
		numeric_fields: Field names that should default to 0 instead of "".
	"""
	numeric = set(numeric_fields or [])
	result = []
	for row in rows:
		cleaned = {}
		for k, v in (row.items() if isinstance(row, dict) else row.items()):
			if v is None and k in numeric:
				cleaned[k] = 0
			else:
				cleaned[k] = serialize(v)
		result.append(cleaned)
	return result
