"""E2Next AI – MCP Server

Exposes ERPNext tools over the Model Context Protocol.
Run with:  bench mcp-server
"""

import os
from typing import Any

import frappe
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings

from e2next_ai.mcp_server.core.tool_registry import registry

MCP_HOST = "0.0.0.0"
MCP_PORT = 8001

mcp = FastMCP(
	name="e2next-ai",
	instructions="ERPNext AI assistant tools. Use these to query ERP data.",
	host=MCP_HOST,
	port=MCP_PORT,
	transport_security=TransportSecuritySettings(
		enable_dns_rebinding_protection=False,
	),
)


_SITES_PATH = str(Path(__file__).resolve().parents[4] / "sites")
_SITE_NAME = None


def _init_frappe_once():
	"""Bootstrap Frappe context once at server startup (only needed for standalone MCP process)."""
	global _SITE_NAME
	if os.getcwd() != _SITES_PATH:
		os.chdir(_SITES_PATH)

	if not frappe.conf:
		sites_dir = Path(_SITES_PATH)
		current_site_file = sites_dir / "currentsite.txt"

		if current_site_file.exists():
			site = current_site_file.read_text().strip()
		else:
			site = next(
				(e.name for e in sorted(sites_dir.iterdir()) if e.is_dir() and (e / "site_config.json").exists()),
				None,
			)
			if not site:
				raise RuntimeError("No Frappe site found. Set a default site with: bench use <site-name>")

		_SITE_NAME = site
		frappe.init(site=site, sites_path=_SITES_PATH)
	elif not _SITE_NAME:
		current_site_file = Path(_SITES_PATH) / "currentsite.txt"
		if current_site_file.exists():
			_SITE_NAME = current_site_file.read_text().strip()

	if not getattr(frappe.local, "db", None):
		frappe.connect()


_init_frappe_once()


def _ensure_frappe_thread_db():
	"""Ensure thread-local frappe.local.conf and frappe.local.db are bound."""
	global _SITE_NAME

	if not _SITE_NAME:
		current_site_file = Path(_SITES_PATH) / "currentsite.txt"
		if current_site_file.exists():
			_SITE_NAME = current_site_file.read_text().strip()

	if not _SITE_NAME:
		raise RuntimeError("No Frappe site found for MCP tool initialization.")

	try:
		frappe.init(site=_SITE_NAME, sites_path=_SITES_PATH)
	except Exception as e:
		raise RuntimeError(f"Failed to init Frappe context for site={_SITE_NAME!r}") from e

	try:
		db = getattr(frappe.local, "db", None)
	except Exception:
		db = None

	if not db:
		frappe.connect()


# ── Register tools from the registry and expose via MCP ──────────


def _register_all_tools():
	"""Register all tool classes with the registry and create MCP wrappers."""
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
		EmployeeDirectoryTool,
		AttendanceSummaryTool,
		LeaveBalanceTool,
		LeaveSummaryTool,
		HiringStatsTool,
	)
	from e2next_ai.mcp_server.tools.payroll import (
		SalarySlipSummaryTool,
		PayrollCostByDeptTool,
		PendingSalarySlipsTool,
		PayrollEntryStatusTool,
	)
	from e2next_ai.mcp_server.tools.supply_chain import (
		MaterialRequestStatusTool,
		DeliveryFulfillmentTool,
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

	tool_classes = [
		# Sales
		SalesSummaryTool,
		SalesTrendTool,
		TopCustomersTool,
		TopItemsTool,
		SalesPersonsSummaryTool,
		CustomerOutstandingTool,
		CustomerLedgerTool,
		# Stock
		StockBalanceTool,
		StockLedgerTool,
		ReorderAlertTool,
		StockAgingTool,
		WarehouseSummaryTool,
		# Purchase
		PurchaseSummaryTool,
		TopSuppliersTool,
		PendingPOTool,
		PendingPRTool,
		SupplierOutstandingTool,
		# HR
		EmployeeDirectoryTool,
		AttendanceSummaryTool,
		LeaveBalanceTool,
		LeaveSummaryTool,
		HiringStatsTool,
		# Payroll
		SalarySlipSummaryTool,
		PayrollCostByDeptTool,
		PendingSalarySlipsTool,
		PayrollEntryStatusTool,
		# Supply Chain
		MaterialRequestStatusTool,
		DeliveryFulfillmentTool,
		POToInvoiceFlowTool,
		SupplierLeadTimeTool,
		# Manufacturing
		WorkOrderStatusTool,
		ProductionSummaryTool,
		BomUsageTool,
		WipSnapshotTool,
		DowntimeSummaryTool,
	]

	for cls in tool_classes:
		if cls.name not in registry:
			registry.register(cls)


_register_all_tools()


# ── MCP Tool Wrappers ─────────────────────────────────────────────
# Each @mcp.tool wraps a registered MCPTool, adding Frappe thread init.


@mcp.tool(structured_output=False)
def sales_summary(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	customer_group: str | None = None,
) -> dict[str, Any]:
	"""Get sales summary: total invoiced, collected, outstanding, invoice count, avg invoice value.

	Args:
		company: Company name (optional, defaults to user's company)
		from_date: Start date YYYY-MM-DD or natural language like "this month"
		to_date: End date YYYY-MM-DD
		customer_group: Filter by customer group (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("sales_summary")
	return tool.execute(company=company, from_date=from_date, to_date=to_date, customer_group=customer_group)


@mcp.tool(structured_output=False)
def sales_trend(
	company: str | None = None,
	period: str = "monthly",
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict[str, Any]:
	"""Get daily or monthly sales revenue trend with comparison to previous period.

	Args:
		company: Company name (optional)
		period: Granularity — "daily" or "monthly" (default monthly)
		from_date: Start date YYYY-MM-DD or natural language
		to_date: End date YYYY-MM-DD
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("sales_trend")
	return tool.execute(company=company, period=period, from_date=from_date, to_date=to_date)


@mcp.tool(structured_output=False)
def top_customers(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	rank_by: str = "revenue",
	limit: int = 10,
) -> dict[str, Any]:
	"""Get top customers ranked by revenue, outstanding, or order count.

	Args:
		company: Company name (optional)
		from_date: Start date YYYY-MM-DD or natural language
		to_date: End date YYYY-MM-DD
		rank_by: Ranking criteria — "revenue", "outstanding", or "order_count"
		limit: Number of customers to return (default 10)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("top_customers")
	return tool.execute(company=company, from_date=from_date, to_date=to_date, rank_by=rank_by, limit=limit)


@mcp.tool(structured_output=False)
def top_items(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	rank_by: str = "revenue",
	item_group: str | None = None,
	limit: int = 10,
) -> dict[str, Any]:
	"""Get top selling items ranked by quantity or revenue.

	Args:
		company: Company name (optional)
		from_date: Start date YYYY-MM-DD or natural language
		to_date: End date YYYY-MM-DD
		rank_by: Ranking criteria — "revenue" or "qty"
		item_group: Filter by item group (optional)
		limit: Number of items to return (default 10)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("top_items")
	return tool.execute(company=company, from_date=from_date, to_date=to_date, rank_by=rank_by, item_group=item_group, limit=limit)


@mcp.tool(structured_output=False)
def sales_persons_summary(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict[str, Any]:
	"""Get revenue per sales person with target vs actual comparison.

	Args:
		company: Company name (optional)
		from_date: Start date YYYY-MM-DD or natural language
		to_date: End date YYYY-MM-DD
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("sales_persons_summary")
	return tool.execute(company=company, from_date=from_date, to_date=to_date)


@mcp.tool(structured_output=False)
def customer_outstanding(customer_name: str) -> dict[str, Any]:
	"""Get the outstanding (unpaid) amount for a customer.

	Args:
		customer_name: The Customer ID (e.g. "CUST-0001")
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("customer_outstanding")
	return tool.execute(customer_name=customer_name)


@mcp.tool(structured_output=False)
def customer_ledger(customer_name: str, limit: int = 50) -> dict[str, Any]:
	"""Get the general ledger entries for a customer.

	Args:
		customer_name: The Customer ID (e.g. "CUST-0001")
		limit: Maximum number of entries to return (default 50)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("customer_ledger")
	return tool.execute(customer_name=customer_name, limit=limit)


# ── Stock Tools ────────────────────────────────────────────────────


@mcp.tool(structured_output=False)
def stock_balance(
	item_code: str | None = None,
	warehouse: str | None = None,
	company: str | None = None,
) -> dict[str, Any]:
	"""Get current stock balance (quantity and value) by item and/or warehouse.

	Args:
		item_code: Filter by specific item code (optional)
		warehouse: Filter by warehouse (optional)
		company: Company name (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("stock_balance")
	return tool.execute(item_code=item_code, warehouse=warehouse, company=company)


@mcp.tool(structured_output=False)
def stock_ledger(
	item_code: str = "",
	warehouse: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict[str, Any]:
	"""Get stock ledger entries showing item movements (IN/OUT) with voucher details.

	Args:
		item_code: Item code to look up (required)
		warehouse: Filter by warehouse (optional)
		from_date: Start date YYYY-MM-DD or natural language
		to_date: End date YYYY-MM-DD
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("stock_ledger")
	return tool.execute(item_code=item_code, warehouse=warehouse, from_date=from_date, to_date=to_date)


@mcp.tool(structured_output=False)
def reorder_alert(
	warehouse: str | None = None,
	item_group: str | None = None,
) -> dict[str, Any]:
	"""Get items at or below reorder level with shortfall quantities.

	Args:
		warehouse: Filter by warehouse (optional)
		item_group: Filter by item group (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("reorder_alert")
	return tool.execute(warehouse=warehouse, item_group=item_group)


@mcp.tool(structured_output=False)
def stock_aging(
	warehouse: str | None = None,
	company: str | None = None,
	min_days: int = 90,
) -> dict[str, Any]:
	"""Get slow-moving or aged stock analysis with days in stock and value at risk.

	Args:
		warehouse: Filter by warehouse (optional)
		company: Company name (optional)
		min_days: Minimum days in stock to include (default 90)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("stock_aging")
	return tool.execute(warehouse=warehouse, company=company, min_days=min_days)


@mcp.tool(structured_output=False)
def warehouse_summary(
	company: str | None = None,
) -> dict[str, Any]:
	"""Get total stock value and item count per warehouse.

	Args:
		company: Company name (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("warehouse_summary")
	return tool.execute(company=company)


# ── Purchase Tools ─────────────────────────────────────────────────


@mcp.tool(structured_output=False)
def purchase_summary(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	supplier_group: str | None = None,
) -> dict[str, Any]:
	"""Get purchase summary: total billed, paid, outstanding for a period.

	Args:
		company: Company name (optional)
		from_date: Start date YYYY-MM-DD or natural language
		to_date: End date YYYY-MM-DD
		supplier_group: Filter by supplier group (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("purchase_summary")
	return tool.execute(company=company, from_date=from_date, to_date=to_date, supplier_group=supplier_group)


@mcp.tool(structured_output=False)
def top_suppliers(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	rank_by: str = "spend",
	limit: int = 10,
) -> dict[str, Any]:
	"""Get top suppliers ranked by spend, outstanding, or order count.

	Args:
		company: Company name (optional)
		from_date: Start date YYYY-MM-DD or natural language
		to_date: End date YYYY-MM-DD
		rank_by: Ranking criteria — "spend", "outstanding", or "order_count"
		limit: Number of suppliers to return (default 10)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("top_suppliers")
	return tool.execute(company=company, from_date=from_date, to_date=to_date, rank_by=rank_by, limit=limit)


@mcp.tool(structured_output=False)
def pending_po(
	company: str | None = None,
	supplier: str | None = None,
) -> dict[str, Any]:
	"""Get open Purchase Orders not yet fully received.

	Args:
		company: Company name (optional)
		supplier: Filter by supplier (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("pending_po")
	return tool.execute(company=company, supplier=supplier)


@mcp.tool(structured_output=False)
def pending_pr(
	company: str | None = None,
	supplier: str | None = None,
) -> dict[str, Any]:
	"""Get Purchase Receipts not yet billed (unbilled GRN).

	Args:
		company: Company name (optional)
		supplier: Filter by supplier (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("pending_pr")
	return tool.execute(company=company, supplier=supplier)


@mcp.tool(structured_output=False)
def supplier_outstanding(
	company: str | None = None,
	supplier: str | None = None,
) -> dict[str, Any]:
	"""Get payable ageing by supplier with buckets: 0-30, 31-60, 61-90, 90+ days.

	Args:
		company: Company name (optional)
		supplier: Filter by specific supplier (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("supplier_outstanding")
	return tool.execute(company=company, supplier=supplier)


# ── HR Tools ───────────────────────────────────────────────────────


@mcp.tool(structured_output=False)
def employee_directory(
	company: str | None = None,
	department: str | None = None,
	status: str | None = None,
) -> dict[str, Any]:
	"""Get employee headcount totals and department breakdown.

	Args:
		company: Company name (optional)
		department: Filter by department (optional)
		status: Filter by employee status (optional, e.g. "Active")
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("employee_directory")
	return tool.execute(company=company, department=department, status=status)


@mcp.tool(structured_output=False)
def attendance_summary(
	company: str | None = None,
	department: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict[str, Any]:
	"""Get attendance counts by status for a date range.

	Args:
		company: Company name (optional)
		department: Filter by department (optional)
		from_date: Start date YYYY-MM-DD or natural language like "this month"
		to_date: End date YYYY-MM-DD
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("attendance_summary")
	return tool.execute(company=company, department=department, from_date=from_date, to_date=to_date)


@mcp.tool(structured_output=False)
def leave_balance(
	company: str | None = None,
	employee: str | None = None,
	leave_type: str | None = None,
) -> dict[str, Any]:
	"""Get leave balance per employee/leave type.

	Best-effort: uses Leave Ledger Entry when available; otherwise allocation-only.

	Args:
		company: Company name (optional)
		employee: Employee ID (optional)
		leave_type: Leave Type (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("leave_balance")
	return tool.execute(company=company, employee=employee, leave_type=leave_type)


@mcp.tool(structured_output=False)
def leave_summary(
	company: str | None = None,
	department: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict[str, Any]:
	"""Get leave applications summary by status for a date range.

	Args:
		company: Company name (optional)
		department: Filter by department (optional)
		from_date: Start date YYYY-MM-DD or natural language like "this month"
		to_date: End date YYYY-MM-DD
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("leave_summary")
	return tool.execute(company=company, department=department, from_date=from_date, to_date=to_date)


@mcp.tool(structured_output=False)
def hiring_stats(
	company: str | None = None,
	department: str | None = None,
) -> dict[str, Any]:
	"""Get hiring/recruitment snapshot (job openings + applicants).

	Args:
		company: Company name (optional)
		department: Filter by department (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("hiring_stats")
	return tool.execute(company=company, department=department)


# ── Payroll Tools ───────────────────────────────────────────────────


@mcp.tool(structured_output=False)
def salary_slip_summary(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	payroll_period: str | None = None,
) -> dict[str, Any]:
	"""Get salary slip totals (gross/deductions/net) for a payroll period.

	Args:
		company: Company name (optional)
		from_date: Start date YYYY-MM-DD or natural language like "this month"
		to_date: End date YYYY-MM-DD
		payroll_period: Payroll Period name (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("salary_slip_summary")
	return tool.execute(company=company, from_date=from_date, to_date=to_date, payroll_period=payroll_period)


@mcp.tool(structured_output=False)
def payroll_cost_by_dept(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	month: int | None = None,
	year: int | None = None,
) -> dict[str, Any]:
	"""Get payroll cost breakdown by department.

	Args:
		company: Company name (optional)
		from_date: Start date YYYY-MM-DD or natural language
		to_date: End date YYYY-MM-DD
		month: Month number 1-12 (optional)
		year: Year YYYY (optional)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("payroll_cost_by_dept")
	return tool.execute(company=company, from_date=from_date, to_date=to_date, month=month, year=year)


@mcp.tool(structured_output=False)
def pending_salary_slips(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	month: int | None = None,
	year: int | None = None,
	limit: int = 50,
) -> dict[str, Any]:
	"""List draft/unsubmitted salary slips needing action.

	Args:
		company: Company name (optional)
		from_date: Start date YYYY-MM-DD or natural language
		to_date: End date YYYY-MM-DD
		month: Month number 1-12 (optional)
		year: Year YYYY (optional)
		limit: Max rows (default 50)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("pending_salary_slips")
	return tool.execute(company=company, from_date=from_date, to_date=to_date, month=month, year=year, limit=limit)


@mcp.tool(structured_output=False)
def payroll_entry_status(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 50,
) -> dict[str, Any]:
	"""Get Payroll Entry run statuses for a period.

	Args:
		company: Company name (optional)
		from_date: Start date YYYY-MM-DD or natural language
		to_date: End date YYYY-MM-DD
		limit: Max rows (default 50)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("payroll_entry_status")
	return tool.execute(company=company, from_date=from_date, to_date=to_date, limit=limit)


# ── Supply Chain Tools ──────────────────────────────────────────────


@mcp.tool(structured_output=False)
def material_request_status(
	company: str | None = None,
	material_request_type: str | None = None,
	warehouse: str | None = None,
	limit: int = 50,
) -> dict[str, Any]:
	"""Get pending Material Requests by type/status.

	Args:
		company: Company name (optional)
		material_request_type: Purchase / Material Transfer / Manufacture (optional)
		warehouse: Filter by set_warehouse (optional)
		limit: Max rows (default 50)
	"""
	_ensure_frappe_thread_db()
	tool = registry.get("material_request_status")
	return tool.execute(
		company=company, material_request_type=material_request_type, warehouse=warehouse, limit=limit
	)


@mcp.tool(structured_output=False)
def delivery_fulfillment(
	company: str | None = None,
	customer: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 50,
) -> dict[str, Any]:
	"""Get Sales Orders pending delivery/partial delivery for a date range."""
	_ensure_frappe_thread_db()
	tool = registry.get("delivery_fulfillment")
	return tool.execute(company=company, customer=customer, from_date=from_date, to_date=to_date, limit=limit)


@mcp.tool(structured_output=False)
def po_to_invoice_flow(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 20,
) -> dict[str, Any]:
	"""Health check for PO→Receipt→Invoice flow."""
	_ensure_frappe_thread_db()
	tool = registry.get("po_to_invoice_flow")
	return tool.execute(company=company, from_date=from_date, to_date=to_date, limit=limit)


@mcp.tool(structured_output=False)
def supplier_lead_time(
	company: str | None = None,
	supplier: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 20,
) -> dict[str, Any]:
	"""Average days from PO to GRN per supplier."""
	_ensure_frappe_thread_db()
	tool = registry.get("supplier_lead_time")
	return tool.execute(company=company, supplier=supplier, from_date=from_date, to_date=to_date, limit=limit)


# ── Manufacturing Tools ─────────────────────────────────────────────


@mcp.tool(structured_output=False)
def work_order_status(
	company: str | None = None,
	status: str | None = None,
	item_code: str | None = None,
	limit: int = 50,
) -> dict[str, Any]:
	"""Get work orders by status/item."""
	_ensure_frappe_thread_db()
	tool = registry.get("work_order_status")
	return tool.execute(company=company, status=status, item_code=item_code, limit=limit)


@mcp.tool(structured_output=False)
def production_summary(
	company: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	item_code: str | None = None,
	limit: int = 20,
) -> dict[str, Any]:
	"""Get planned vs produced by item for a date range."""
	_ensure_frappe_thread_db()
	tool = registry.get("production_summary")
	return tool.execute(company=company, from_date=from_date, to_date=to_date, item_code=item_code, limit=limit)


@mcp.tool(structured_output=False)
def bom_usage(
	bom_no: str | None = None,
	item_code: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict[str, Any]:
	"""Get BOM standard raw materials, optionally compare with consumption."""
	_ensure_frappe_thread_db()
	tool = registry.get("bom_usage")
	return tool.execute(bom_no=bom_no, item_code=item_code, from_date=from_date, to_date=to_date)


@mcp.tool(structured_output=False)
def wip_snapshot(
	company: str | None = None,
	wip_warehouse: str | None = None,
	limit: int = 50,
) -> dict[str, Any]:
	"""Get WIP stock snapshot for a WIP warehouse."""
	_ensure_frappe_thread_db()
	tool = registry.get("wip_snapshot")
	return tool.execute(company=company, wip_warehouse=wip_warehouse, limit=limit)


@mcp.tool(structured_output=False)
def downtime_summary(
	company: str | None = None,
	workstation: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict[str, Any]:
	"""Get workstation downtime summary for a date range (if configured)."""
	_ensure_frappe_thread_db()
	tool = registry.get("downtime_summary")
	return tool.execute(company=company, workstation=workstation, from_date=from_date, to_date=to_date)


# ── Entrypoint ──────────────────────────────────────────────────────

if __name__ == "__main__":
	mcp.run(transport="sse")
