import frappe


def _to_plain(obj):
	"""Convert Frappe `_dict`/dict-like objects into plain JSON-serializable structures."""
	# Frappe uses a dict subclass (`frappe.types.frappedict._dict`) for `as_dict=True` rows.
	# FastMCP (via pydantic_core) can't serialize that type reliably, so we normalize to
	# plain `dict`/`list`.
	if isinstance(obj, frappe._dict):
		return {k: _to_plain(v) for k, v in obj.items()}
	if isinstance(obj, dict):
		return {k: _to_plain(v) for k, v in obj.items()}
	if isinstance(obj, list):
		return [_to_plain(v) for v in obj]
	return obj


def get_customer_outstanding(customer_name: str) -> dict:
	"""Return the outstanding amount for a given customer."""
	if not frappe.db.exists("Customer", customer_name):
		frappe.throw(f"Customer {customer_name!r} does not exist")

	result = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(outstanding_amount), 0) AS outstanding
		FROM `tabSales Invoice`
		WHERE customer = %s
		  AND docstatus = 1
		  AND outstanding_amount > 0
		""",
		(customer_name,),
		as_dict=True,
	)
	outstanding_amount = float(result[0].outstanding) if result else 0.0

	return _to_plain(
		{
		"customer_name": customer_name,
		"outstanding_amount": outstanding_amount,
		}
	)


def get_customer_ledger(customer_name: str, limit: int = 50) -> dict:
	"""Return recent GL Entry ledger for a customer.

	Returns debit/credit entries sorted by posting date descending.
	"""
	if not frappe.db.exists("Customer", customer_name):
		frappe.throw(f"Customer {customer_name!r} does not exist")

	entries = frappe.db.sql(
		"""
		SELECT
			posting_date,
			voucher_type,
			voucher_no,
			debit,
			credit,
			remarks
		FROM `tabGL Entry`
		WHERE party_type = 'Customer'
		  AND party = %s
		  AND is_cancelled = 0
		ORDER BY posting_date DESC, creation DESC
		LIMIT %s
		""",
		(customer_name, limit),
		as_dict=True,
	)

	# Convert date objects to strings for JSON serialization
	for entry in entries:
		entry["posting_date"] = str(entry["posting_date"])
		entry["debit"] = float(entry["debit"])
		entry["credit"] = float(entry["credit"])

	return _to_plain(
		{
		"customer_name": customer_name,
		"total_entries": len(entries),
		"entries": entries,
		}
	)


def get_top_customers(limit: int = 10, sort_by: str = "outstanding") -> dict:
	"""Return top customers ranked by outstanding amount or total revenue.

	Args:
		limit: Number of customers to return (default 10).
		sort_by: Ranking criteria — "outstanding" or "revenue".
	"""
	sort_key = (sort_by or "").strip().lower()
	# Normalize common prompt variants so Cursor can pass slightly different strings.
	if sort_key in {"revenue", "total_revenue", "sales", "total_sales"}:
		sort_by = "revenue"
	elif sort_key in {"outstanding", "outstanding_amount", "due", "amount_due"}:
		sort_by = "outstanding"
	else:
		# Backward-compatible default: anything unknown falls back to outstanding.
		sort_by = "outstanding"

	if sort_by == "revenue":
		rows = frappe.db.sql(
			"""
			SELECT
				customer AS customer_name,
				customer_name AS customer_label,
				SUM(grand_total) AS total_revenue,
				SUM(outstanding_amount) AS outstanding_amount,
				COUNT(*) AS invoice_count
			FROM `tabSales Invoice`
			WHERE docstatus = 1
			GROUP BY customer, customer_name
			ORDER BY total_revenue DESC
			LIMIT %s
			""",
			(limit,),
			as_dict=True,
		)
	else:
		rows = frappe.db.sql(
			"""
			SELECT
				customer AS customer_name,
				customer_name AS customer_label,
				SUM(grand_total) AS total_revenue,
				SUM(outstanding_amount) AS outstanding_amount,
				COUNT(*) AS invoice_count
			FROM `tabSales Invoice`
			WHERE docstatus = 1
			GROUP BY customer, customer_name
			ORDER BY outstanding_amount DESC
			LIMIT %s
			""",
			(limit,),
			as_dict=True,
		)

	for row in rows:
		row["total_revenue"] = float(row["total_revenue"])
		row["outstanding_amount"] = float(row["outstanding_amount"])
		row["invoice_count"] = int(row["invoice_count"])

	return _to_plain(
		{
		"sort_by": sort_by,
		"total_results": len(rows),
		"customers": rows,
		}
	)
