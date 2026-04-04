import frappe

from e2next_ai.mcp_server.core.tool_registry import registry


def _ensure_registry():
	"""Ensure tools are registered (lazy import)."""
	if len(registry) == 0:
		from e2next_ai.mcp_server.tools.sales import (
			SalesSummaryTool,
			SalesTrendTool,
			TopCustomersTool,
			TopItemsTool,
			SalesPersonsSummaryTool,
			CustomerOutstandingTool,
			CustomerLedgerTool,
		)
		from e2next_ai.mcp_server.tools.stock import (
			StockBalanceTool,
			StockLedgerTool,
			ReorderAlertTool,
			StockAgingTool,
			WarehouseSummaryTool,
		)
		from e2next_ai.mcp_server.tools.purchase import (
			PurchaseSummaryTool,
			TopSuppliersTool,
			PendingPOTool,
			PendingPRTool,
			SupplierOutstandingTool,
		)
		from e2next_ai.mcp_server.tools.hr import (
			AttendanceSummaryTool,
			EmployeeDirectoryTool,
			HiringStatsTool,
			LeaveBalanceTool,
			LeaveSummaryTool,
		)
		from e2next_ai.mcp_server.tools.payroll import (
			PayrollCostByDeptTool,
			PayrollEntryStatusTool,
			PendingSalarySlipsTool,
			SalarySlipSummaryTool,
		)
		from e2next_ai.mcp_server.tools.supply_chain import (
			DeliveryFulfillmentTool,
			MaterialRequestStatusTool,
			POToInvoiceFlowTool,
			SupplierLeadTimeTool,
		)
		from e2next_ai.mcp_server.tools.manufacturing import (
			BomUsageTool,
			DowntimeSummaryTool,
			ProductionSummaryTool,
			WipSnapshotTool,
			WorkOrderStatusTool,
		)

		for cls in [
			SalesSummaryTool, SalesTrendTool, TopCustomersTool,
			TopItemsTool, SalesPersonsSummaryTool,
			CustomerOutstandingTool, CustomerLedgerTool,
			StockBalanceTool, StockLedgerTool, ReorderAlertTool,
			StockAgingTool, WarehouseSummaryTool,
			PurchaseSummaryTool, TopSuppliersTool, PendingPOTool,
			PendingPRTool, SupplierOutstandingTool,
			EmployeeDirectoryTool, AttendanceSummaryTool, LeaveBalanceTool,
			LeaveSummaryTool, HiringStatsTool,
			SalarySlipSummaryTool, PayrollCostByDeptTool, PendingSalarySlipsTool,
			PayrollEntryStatusTool,
			MaterialRequestStatusTool, DeliveryFulfillmentTool, POToInvoiceFlowTool,
			SupplierLeadTimeTool,
			WorkOrderStatusTool, ProductionSummaryTool, BomUsageTool, WipSnapshotTool, DowntimeSummaryTool,
		]:
			if cls.name not in registry:
				registry.register(cls)


# ── Sales APIs ───────────────────────────────────────────────────────


@frappe.whitelist()
def sales_summary(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	customer_group: str | None = None,
) -> dict:
	"""Get sales summary for a date range."""
	_ensure_registry()
	return registry.get("sales_summary").execute(
		company=company, from_date=from_date, to_date=to_date, customer_group=customer_group
	)


@frappe.whitelist()
def sales_trend(
	company: str | None = None,
	period: str = "monthly",
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict:
	"""Get sales revenue trend (daily/monthly) with period comparison."""
	_ensure_registry()
	return registry.get("sales_trend").execute(
		company=company, period=period, from_date=from_date, to_date=to_date
	)


@frappe.whitelist()
def top_customers(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	rank_by: str = "revenue",
	limit: int = 10,
) -> dict:
	"""Get top customers ranked by revenue, outstanding, or order count."""
	_ensure_registry()
	return registry.get("top_customers").execute(
		company=company, from_date=from_date, to_date=to_date, rank_by=rank_by, limit=limit
	)


@frappe.whitelist()
def top_items(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	rank_by: str = "revenue",
	item_group: str | None = None,
	limit: int = 10,
) -> dict:
	"""Get top selling items ranked by quantity or revenue."""
	_ensure_registry()
	return registry.get("top_items").execute(
		company=company, from_date=from_date, to_date=to_date,
		rank_by=rank_by, item_group=item_group, limit=limit
	)


@frappe.whitelist()
def sales_persons_summary(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict:
	"""Get revenue per sales person with target vs actual."""
	_ensure_registry()
	return registry.get("sales_persons_summary").execute(
		company=company, from_date=from_date, to_date=to_date
	)


# ── Customer APIs ────────────────────────────────────────────────────


@frappe.whitelist()
def customer_outstanding(customer_name: str) -> dict:
	"""Get the outstanding (unpaid) amount for a customer."""
	_ensure_registry()
	return registry.get("customer_outstanding").execute(customer_name=customer_name)


@frappe.whitelist()
def customer_ledger(customer_name: str, limit: int = 50) -> dict:
	"""Get the general ledger entries for a customer."""
	_ensure_registry()
	return registry.get("customer_ledger").execute(customer_name=customer_name, limit=limit)


# ── Stock APIs ──────────────────────────────────────────────────────


@frappe.whitelist()
def stock_balance(
	item_code: str | None = None,
	warehouse: str | None = None,
	company: str | None = None,
) -> dict:
	"""Get current stock balance by item and/or warehouse."""
	_ensure_registry()
	return registry.get("stock_balance").execute(item_code=item_code, warehouse=warehouse, company=company)


@frappe.whitelist()
def stock_ledger(
	item_code: str = "",
	warehouse: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict:
	"""Get stock ledger entries showing item movements."""
	_ensure_registry()
	return registry.get("stock_ledger").execute(
		item_code=item_code, warehouse=warehouse, from_date=from_date, to_date=to_date
	)


@frappe.whitelist()
def reorder_alert(
	warehouse: str | None = None,
	item_group: str | None = None,
) -> dict:
	"""Get items at or below reorder level."""
	_ensure_registry()
	return registry.get("reorder_alert").execute(warehouse=warehouse, item_group=item_group)


@frappe.whitelist()
def stock_aging(
	warehouse: str | None = None,
	company: str | None = None,
	min_days: int = 90,
) -> dict:
	"""Get slow-moving or aged stock analysis."""
	_ensure_registry()
	return registry.get("stock_aging").execute(warehouse=warehouse, company=company, min_days=min_days)


@frappe.whitelist()
def warehouse_summary(company: str | None = None) -> dict:
	"""Get total stock value and item count per warehouse."""
	_ensure_registry()
	return registry.get("warehouse_summary").execute(company=company)


# ── Purchase APIs ──────────────────────────────────────────────────


@frappe.whitelist()
def purchase_summary(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	supplier_group: str | None = None,
) -> dict:
	"""Get purchase summary for a date range."""
	_ensure_registry()
	return registry.get("purchase_summary").execute(
		company=company, from_date=from_date, to_date=to_date, supplier_group=supplier_group
	)


@frappe.whitelist()
def top_suppliers(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	rank_by: str = "spend",
	limit: int = 10,
) -> dict:
	"""Get top suppliers ranked by spend, outstanding, or order count."""
	_ensure_registry()
	return registry.get("top_suppliers").execute(
		company=company, from_date=from_date, to_date=to_date, rank_by=rank_by, limit=limit
	)


@frappe.whitelist()
def pending_po(company: str | None = None, supplier: str | None = None) -> dict:
	"""Get open Purchase Orders not yet fully received."""
	_ensure_registry()
	return registry.get("pending_po").execute(company=company, supplier=supplier)


@frappe.whitelist()
def pending_pr(company: str | None = None, supplier: str | None = None) -> dict:
	"""Get Purchase Receipts not yet billed."""
	_ensure_registry()
	return registry.get("pending_pr").execute(company=company, supplier=supplier)


@frappe.whitelist()
def supplier_outstanding(company: str | None = None, supplier: str | None = None) -> dict:
	"""Get payable ageing by supplier."""
	_ensure_registry()
	return registry.get("supplier_outstanding").execute(company=company, supplier=supplier)


# ── HR APIs ─────────────────────────────────────────────────────────


@frappe.whitelist()
def employee_directory(
	company: str | None = None,
	department: str | None = None,
	status: str | None = None,
) -> dict:
	"""Get employee headcount totals and breakdowns."""
	_ensure_registry()
	return registry.get("employee_directory").execute(company=company, department=department, status=status)


@frappe.whitelist()
def attendance_summary(
	company: str | None = None,
	department: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict:
	"""Get attendance summary for a date range."""
	_ensure_registry()
	return registry.get("attendance_summary").execute(
		company=company, department=department, from_date=from_date, to_date=to_date
	)


@frappe.whitelist()
def leave_balance(
	company: str | None = None,
	employee: str | None = None,
	leave_type: str | None = None,
) -> dict:
	"""Get leave balance snapshot per employee/leave type."""
	_ensure_registry()
	return registry.get("leave_balance").execute(company=company, employee=employee, leave_type=leave_type)


@frappe.whitelist()
def leave_summary(
	company: str | None = None,
	department: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict:
	"""Get leave applications summary for a date range."""
	_ensure_registry()
	return registry.get("leave_summary").execute(
		company=company, department=department, from_date=from_date, to_date=to_date
	)


@frappe.whitelist()
def hiring_stats(
	company: str | None = None,
	department: str | None = None,
) -> dict:
	"""Get hiring/recruitment snapshot."""
	_ensure_registry()
	return registry.get("hiring_stats").execute(company=company, department=department)


# ── Payroll APIs ────────────────────────────────────────────────────


@frappe.whitelist()
def salary_slip_summary(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	payroll_period: str | None = None,
) -> dict:
	"""Get salary slip totals (gross/deductions/net) for a period."""
	_ensure_registry()
	return registry.get("salary_slip_summary").execute(
		company=company, from_date=from_date, to_date=to_date, payroll_period=payroll_period
	)


@frappe.whitelist()
def payroll_cost_by_dept(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	month: int | None = None,
	year: int | None = None,
) -> dict:
	"""Get payroll cost breakdown by department."""
	_ensure_registry()
	return registry.get("payroll_cost_by_dept").execute(
		company=company, from_date=from_date, to_date=to_date, month=month, year=year
	)


@frappe.whitelist()
def pending_salary_slips(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	month: int | None = None,
	year: int | None = None,
	limit: int = 50,
) -> dict:
	"""List draft/unsubmitted salary slips needing action."""
	_ensure_registry()
	return registry.get("pending_salary_slips").execute(
		company=company, from_date=from_date, to_date=to_date, month=month, year=year, limit=limit
	)


@frappe.whitelist()
def payroll_entry_status(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 50,
) -> dict:
	"""Get Payroll Entry run status for a period."""
	_ensure_registry()
	return registry.get("payroll_entry_status").execute(
		company=company, from_date=from_date, to_date=to_date, limit=limit
	)


# ── Supply Chain APIs ───────────────────────────────────────────────


@frappe.whitelist()
def material_request_status(
	company: str | None = None,
	material_request_type: str | None = None,
	warehouse: str | None = None,
	limit: int = 50,
) -> dict:
	"""Get pending Material Requests by type/status."""
	_ensure_registry()
	return registry.get("material_request_status").execute(
		company=company,
		material_request_type=material_request_type,
		warehouse=warehouse,
		limit=limit,
	)


@frappe.whitelist()
def delivery_fulfillment(
	company: str | None = None,
	customer: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 50,
) -> dict:
	"""Get Sales Orders pending delivery/partial delivery."""
	_ensure_registry()
	return registry.get("delivery_fulfillment").execute(
		company=company, customer=customer, from_date=from_date, to_date=to_date, limit=limit
	)


@frappe.whitelist()
def po_to_invoice_flow(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 20,
) -> dict:
	"""Health check for PO→Receipt→Invoice flow."""
	_ensure_registry()
	return registry.get("po_to_invoice_flow").execute(
		company=company, from_date=from_date, to_date=to_date, limit=limit
	)


@frappe.whitelist()
def supplier_lead_time(
	company: str | None = None,
	supplier: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 20,
) -> dict:
	"""Average days from PO to GRN per supplier."""
	_ensure_registry()
	return registry.get("supplier_lead_time").execute(
		company=company, supplier=supplier, from_date=from_date, to_date=to_date, limit=limit
	)


# ── Manufacturing APIs ──────────────────────────────────────────────


@frappe.whitelist()
def work_order_status(
	company: str | None = None,
	status: str | None = None,
	item_code: str | None = None,
	limit: int = 50,
) -> dict:
	"""Get work orders by status/item."""
	_ensure_registry()
	return registry.get("work_order_status").execute(
		company=company, status=status, item_code=item_code, limit=limit
	)


@frappe.whitelist()
def production_summary(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	item_code: str | None = None,
	limit: int = 20,
) -> dict:
	"""Get planned vs produced quantities by item for a date range."""
	_ensure_registry()
	return registry.get("production_summary").execute(
		company=company, from_date=from_date, to_date=to_date, item_code=item_code, limit=limit
	)


@frappe.whitelist()
def bom_usage(
	bom_no: str | None = None,
	item_code: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict:
	"""Get BOM standard raw materials, optionally compare with consumption."""
	_ensure_registry()
	return registry.get("bom_usage").execute(
		bom_no=bom_no, item_code=item_code, from_date=from_date, to_date=to_date
	)


@frappe.whitelist()
def wip_snapshot(
	company: str | None = None,
	wip_warehouse: str | None = None,
	limit: int = 50,
) -> dict:
	"""Get WIP stock snapshot for a WIP warehouse."""
	_ensure_registry()
	return registry.get("wip_snapshot").execute(company=company, wip_warehouse=wip_warehouse, limit=limit)


@frappe.whitelist()
def downtime_summary(
	company: str | None = None,
	workstation: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict:
	"""Get workstation downtime summary for a date range (if configured)."""
	_ensure_registry()
	return registry.get("downtime_summary").execute(
		company=company, workstation=workstation, from_date=from_date, to_date=to_date
	)


# ── Chat API (Gemini LLM) ─────────────────────────────────────────


@frappe.whitelist()
def chat(message: str, session_id: str | None = None) -> dict:
	"""Chat with E2Next AI via Gemini LLM."""
	_ensure_registry()
	from e2next_ai.gemini_chat import handle_chat

	return handle_chat(message=message, session_id=session_id)
