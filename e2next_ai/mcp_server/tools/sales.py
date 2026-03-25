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


def get_sales_summary(from_date: str | None = None, to_date: str | None = None) -> dict:
	"""Return a sales summary for the given date range.

	Defaults to the current fiscal year if dates are not provided.
	"""
	if not from_date or not to_date:
		fiscal_year = frappe.defaults.get_global_default("fiscal_year")
		if fiscal_year and frappe.db.exists("Fiscal Year", fiscal_year):
			fy = frappe.get_doc("Fiscal Year", fiscal_year)
			from_date = from_date or str(fy.year_start_date)
			to_date = to_date or str(fy.year_end_date)
		else:
			from_date = from_date or str(frappe.utils.get_first_day(frappe.utils.today()))
			to_date = to_date or str(frappe.utils.today())

	summary = frappe.db.sql(
		"""
		SELECT
			COUNT(*) AS total_invoices,
			COALESCE(SUM(grand_total), 0) AS total_sales,
			COALESCE(SUM(net_total), 0) AS total_net,
			COALESCE(SUM(total_taxes_and_charges), 0) AS total_taxes,
			COALESCE(SUM(outstanding_amount), 0) AS total_outstanding,
			COALESCE(SUM(grand_total - outstanding_amount), 0) AS total_collected,
			COUNT(DISTINCT customer) AS unique_customers
		FROM `tabSales Invoice`
		WHERE docstatus = 1
		  AND posting_date BETWEEN %s AND %s
		""",
		(from_date, to_date),
		as_dict=True,
	)[0]

	for key in summary:
		if key != "total_invoices" and key != "unique_customers":
			summary[key] = float(summary[key])
		else:
			summary[key] = int(summary[key])

	summary["from_date"] = from_date
	summary["to_date"] = to_date

	return _to_plain(summary)


def get_top_selling_items(limit: int = 10, from_date: str | None = None, to_date: str | None = None) -> dict:
	"""Return top selling items by quantity and revenue.

	Defaults to the current fiscal year if dates are not provided.
	"""
	if not from_date or not to_date:
		fiscal_year = frappe.defaults.get_global_default("fiscal_year")
		if fiscal_year and frappe.db.exists("Fiscal Year", fiscal_year):
			fy = frappe.get_doc("Fiscal Year", fiscal_year)
			from_date = from_date or str(fy.year_start_date)
			to_date = to_date or str(fy.year_end_date)
		else:
			from_date = from_date or str(frappe.utils.get_first_day(frappe.utils.today()))
			to_date = to_date or str(frappe.utils.today())

	items = frappe.db.sql(
		"""
		SELECT
			sii.item_code,
			sii.item_name,
			sii.stock_uom AS uom,
			SUM(sii.qty) AS total_qty,
			SUM(sii.amount) AS total_revenue,
			COUNT(DISTINCT si.name) AS invoice_count
		FROM `tabSales Invoice Item` sii
		JOIN `tabSales Invoice` si ON si.name = sii.parent
		WHERE si.docstatus = 1
		  AND si.posting_date BETWEEN %s AND %s
		GROUP BY sii.item_code, sii.item_name, sii.stock_uom
		ORDER BY total_revenue DESC
		LIMIT %s
		""",
		(from_date, to_date, limit),
		as_dict=True,
	)

	for item in items:
		item["total_qty"] = float(item["total_qty"])
		item["total_revenue"] = float(item["total_revenue"])
		item["invoice_count"] = int(item["invoice_count"])

	return _to_plain(
		{
			"from_date": from_date,
			"to_date": to_date,
			"total_results": len(items),
			"items": items,
		}
	)
