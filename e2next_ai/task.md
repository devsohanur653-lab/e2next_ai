# ERPNext MCP — ChatGPT-Feel Implementation Guide

> Build a natural-language AI layer on top of ERPNext using MCP tools.
> Users ask questions in plain English → AI routes → tools query ERPNext → human-readable answer.

---

## How It Works (Architecture Overview)

```
User Question
     │
     ▼
Intent Router  ──► General ERPNext knowledge? ──► AI answers directly (no DB)
     │
     ▼
Tool Matched? ──► YES ──► Run MCP Tool ──► Query ERPNext DB ──► Format Answer
     │
     NO
     ▼
Fallback SQL Query ──► Run raw query ──► Format Answer
     │
     ▼
Log to `MCP Query Log` doctype  ◄─────────────────────────────────────────────
(All unmatched / fallback queries saved here for next-version tool creation)
```

### Answer types
| Scenario | What happens |
|---|---|
| Tool matched | Tool runs → real data → formatted answer |
| No tool, but data question | Fallback SQL → real data → logged as "unmatched" |
| General how-to question | AI answers from knowledge, no DB hit |
| Restricted doctype | Blocked, permission error returned |

---

## Project Structure (recommended)

```
erpnext_mcp/
├── README.md                  ← this file
├── core/
│   ├── tool_registry.py       ← register all tools
│   ├── intent_router.py       ← detect module + metric from question
│   ├── date_parser.py         ← "this month", "last 30 days", FY ranges
│   ├── permissions.py         ← role checks, blocked doctypes
│   ├── serializer.py          ← strip Frappe _dict, plain JSON out
│   ├── formatter.py           ← summary + numbers + optional table
│   ├── fallback_sql.py        ← runs when no tool matches
│   └── query_logger.py        ← writes to MCP Query Log doctype
├── tools/
│   ├── sales/
│   ├── stock/
│   ├── purchase/
│   ├── hr/
│   ├── payroll/
│   ├── supply_chain/
│   └── manufacturing/
├── doctypes/
│   └── mcp_query_log/         ← custom doctype files
└── tests/
    └── (one test file per module)
```

---

## PHASE 0 — Core Foundation
> ⚠️ Must complete ALL of Phase 0 before building any module tool.

### 0.1 — Tool Framework

- [x] Define standard tool response shape:
  ```python
  {
    "status": "success" | "error",
    "tool": "tool_name",
    "query_time_ms": 123,
    "data": { ... },
    "summary": "Plain English one-liner",
    "table": [ ... ]   # optional
  }
  ```
- [x] Create base `MCPTool` class all tools inherit from
- [x] Register tools in `tool_registry.py` with name, description, parameters
- [x] Add per-tool timing (log ms taken per tool call)
- [x] Add query source logging (which SQL / ORM call was used)

### 0.2 — Date Range Parser

- [x] Parse natural language dates to `(from_date, to_date)` tuples:
  - `"this month"` → first to last day of current month
  - `"last month"` → previous calendar month
  - `"last 30 days"` → today minus 30 days
  - `"this quarter"` → current FY quarter
  - `"this year"` / `"FY 2024-25"` → fiscal year range
  - `"today"` → single day
  - `"last week"` → Mon–Sun of previous week
- [x] Support ERPNext fiscal year settings (not always Jan–Dec)
- [x] Fallback: ask user "Which date range do you mean?"

### 0.3 — Permissions & Safety

- [x] Read current user's roles from ERPNext session
- [ ] Block access to restricted doctypes:
  ```python
  BLOCKED_DOCTYPES = [
    "User", "Has Role", "Auth Token",
    "System Settings", "Data Import"
  ]
  ```
- [x] Check `has_permission()` before every query
- [x] Return clean permission error (not stack trace) when blocked
- [x] Never expose raw SQL errors to the user

### 0.4 — Serialization

- [x] Strip all Frappe `_dict` objects → plain `dict`
- [x] Convert `datetime` / `date` objects → ISO strings
- [x] Convert `Decimal` → `float`
- [x] Null-safe: replace `None` with `""` or `0` depending on field type
- [x] All tool responses must be `json.dumps()`-safe

### 0.5 — Answer Formatter

- [x] Short summary line: `"Sales this month: ৳ 12,45,000 across 38 invoices"`
- [x] Key numbers block: 3–5 most important metrics
- [x] Optional table: top 5–10 rows, sorted by relevance
- [x] Locale-aware number formatting (IQD, USD, etc.)
- [x] Respect user's preferred currency from ERPNext settings

### 0.6 — Intent Router

- [x] Detect module from question: sales / stock / purchase / hr / payroll / supply_chain / manufacturing
- [x] Detect metric type: summary / trend / top_n / pending / alert / detail
- [x] Extract entities: company name, warehouse, item, employee, date range
- [x] If multiple modules match → ask clarifying question
- [x] Confidence threshold: below 0.6 → ask "Did you mean X?"

### 0.7 — Follow-up Question Engine

- [x] Identify missing required parameters before running a tool
- [x] Ask only ONE question at a time
- [x] Store partial context in session so user can answer naturally
  - Example: Tool needs `warehouse` → ask "Which warehouse? (Main, Store, etc.)"
  - User replies "Main" → tool runs with `warehouse = "Main Warehouse"`

### 0.8 — Fallback SQL Handler

- [x] When no tool matches a data question, attempt a safe generic query
- [x] Whitelist allowed tables for fallback queries
- [x] Log every fallback to `MCP Query Log` doctype (see 0.9)
- [x] Return answer with a note: `"(Answered via fallback — tool coming soon)"`

### 0.9 — MCP Query Log Doctype (for next version)

Create a custom doctype `MCP Query Log` with these fields:

| Field | Type | Purpose |
|---|---|---|
| `question` | Long Text | Original user question |
| `detected_module` | Data | Module router picked |
| `detected_metric` | Data | Metric type detected |
| `tool_matched` | Check | Was a tool found? |
| `fallback_used` | Check | Did fallback SQL run? |
| `fallback_query` | Code | The SQL that ran |
| `answer_given` | Long Text | What was returned to user |
| `response_time_ms` | Int | How long it took |
| `user` | Link → User | Who asked |
| `timestamp` | Datetime | When |
| `flagged_for_tool` | Check | Mark for building a tool |
| `notes` | Text | Dev notes for next version |

- [ ] Create doctype JSON in `doctypes/mcp_query_log/`
- [ ] Auto-insert on every unmatched / fallback query
- [ ] Build a simple report: "Unmatched Questions This Month"
- [ ] Review weekly → highest frequency = next tool to build

---

## PHASE 1 — Sales Module
> Depends on: Phase 0 complete

### Tools to build

#### `sales_summary`
- [x] Total invoiced amount for period + company
- [x] Total collected (payment entries)
- [x] Outstanding (invoiced − collected)
- [x] Invoice count
- [x] Average invoice value
- [x] Parameters: `company`, `from_date`, `to_date`, `customer_group` (optional)
- [ ] Maps to ERPNext report: *Sales Analytics*, *Accounts Receivable Summary*

#### `sales_trend`
- [x] Daily or monthly revenue over a period
- [x] Compare to same period last year / last month
- [x] % change calculation
- [x] Parameters: `company`, `period` (daily/monthly), `from_date`, `to_date`
- [ ] Maps to ERPNext report: *Sales Analytics*

#### `top_customers`
- [x] Rank customers by: revenue / outstanding / order count (user chooses)
- [x] Top N (default 10)
- [x] Show: customer name, amount, invoice count, last order date
- [x] Parameters: `company`, `from_date`, `to_date`, `rank_by`, `limit`
- [ ] Maps to ERPNext report: *Customer-wise Sales Summary*

#### `top_items`
- [x] Rank items by: qty sold / revenue (user chooses)
- [x] Show: item name, qty, amount, top customer for that item
- [x] Parameters: `company`, `from_date`, `to_date`, `rank_by`, `item_group` (optional), `limit`
- [ ] Maps to ERPNext report: *Item-wise Sales History*

#### `sales_persons_summary`
- [x] Revenue per sales person
- [x] Target vs actual (if targets set)
- [x] Parameters: `company`, `from_date`, `to_date`
- [ ] Maps to ERPNext report: *Sales Person-wise Transaction Summary*

### Sample questions this module must answer
```
"What were our total sales this month?"
"Which customer bought the most last quarter?"
"Show me top 5 items sold in January"
"How is sales trending compared to last month?"
"What is our outstanding receivable?"
"How did each sales person perform this year?"
```

---

## PHASE 2 — Stock / Inventory Module
> Depends on: Phase 0 complete

### Tools to build

#### `stock_balance`
- [x] Current qty and value by item and/or warehouse
- [x] Parameters: `item_code` (optional), `warehouse` (optional), `company`
- [ ] Maps to ERPNext report: *Stock Balance*

#### `stock_ledger`
- [x] Item movement: IN / OUT with voucher type and date
- [x] Parameters: `item_code`, `warehouse` (optional), `from_date`, `to_date`
- [ ] Maps to ERPNext report: *Stock Ledger*

#### `reorder_alert`
- [x] Items at or below reorder level / min stock qty
- [x] Show: item, warehouse, current qty, reorder level, shortfall
- [x] Parameters: `warehouse` (optional), `item_group` (optional)
- [ ] Maps to ERPNext report: *Items To Be Requested*

#### `stock_aging`
- [x] Slow-moving or aged stock by batch / FIFO
- [x] Days in stock, value at risk
- [x] Parameters: `warehouse`, `ageing_based_on` (FIFO/batch), `from_date`
- [ ] Maps to ERPNext report: *Stock Ageing*

#### `warehouse_summary`
- [x] Total stock value and item count per warehouse
- [x] Parameters: `company`
- [ ] Maps to ERPNext report: *Warehouse-wise Stock Balance*

### Sample questions this module must answer
```
"What is the current stock of Item X?"
"Which items are below reorder level?"
"Show me all stock movements for Item Y this week"
"What is the total stock value in Main Warehouse?"
"Which items have been sitting for more than 90 days?"
```

---

## PHASE 3 — Purchase Module
> Depends on: Phase 0 complete

### Tools to build

#### `purchase_summary`
- [x] Total billed, paid, outstanding by period
- [x] Parameters: `company`, `from_date`, `to_date`, `supplier_group` (optional)
- [ ] Maps to: *Purchase Analytics*, *Accounts Payable Summary*

#### `top_suppliers`
- [x] Rank by spend / outstanding / order count
- [x] Parameters: `company`, `from_date`, `to_date`, `rank_by`, `limit`
- [ ] Maps to: *Supplier-wise Purchase Summary*

#### `pending_po`
- [x] Open Purchase Orders not yet fully received
- [x] Show: PO number, supplier, amount, expected date, % received
- [x] Parameters: `company`, `supplier` (optional)
- [ ] Maps to: *Purchase Order Trends*

#### `pending_pr`
- [x] Purchase Receipts not yet billed (unbilled GRN)
- [x] Show: GRN number, supplier, amount, receipt date, days unbilled
- [x] Parameters: `company`, `supplier` (optional)
- [ ] Maps to: *Received Items To Be Billed*

#### `supplier_outstanding`
- [x] Payable ageing by supplier (0–30, 31–60, 61–90, 90+ days)
- [x] Parameters: `company`, `supplier` (optional), `ageing_based_on`
- [ ] Maps to: *Accounts Payable*

### Sample questions this module must answer
```
"How much did we spend on purchases this month?"
"Which supplier do we owe the most to?"
"Show me open purchase orders not yet received"
"Which GRNs have not been billed yet?"
"What is our total payable ageing?"
```

---

## PHASE 4 — HR Module
> Depends on: Phase 0 complete

### Tools to build

#### `employee_directory`
- [ ] Headcount: total, by department, by designation, by status (active/left)
- [ ] Parameters: `company`, `department` (optional), `status`
- [ ] Maps to: *Employee Analytics*, *HR Analytics*

#### `attendance_summary`
- [ ] Present / absent / late / on-leave counts
- [ ] Parameters: `company`, `department` (optional), `from_date`, `to_date`
- [ ] Maps to: *Monthly Attendance Sheet*, *Employee Attendance Summary*

#### `leave_balance`
- [ ] Leave balance per employee per leave type
- [ ] Parameters: `employee` (optional), `leave_type` (optional), `company`
- [ ] Maps to: *Employee Leave Balance*

#### `leave_summary`
- [ ] Approved / pending / rejected leaves for a period
- [ ] Parameters: `company`, `department` (optional), `from_date`, `to_date`
- [ ] Maps to: *Leave Details Report*

#### `hiring_stats`
- [ ] Open job openings, applicant count, interview stage, offers made
- [ ] Parameters: `company`, `department` (optional)
- [ ] Maps to: *Recruitment Analytics*

### Sample questions this module must answer
```
"How many employees do we have by department?"
"Who was absent today?"
"What is the leave balance for employee John?"
"How many people are on leave this week?"
"How many open positions do we have?"
```

---

## PHASE 5 — Payroll Module
> Depends on: Phase 0 + HR Module

### Tools to build

#### `salary_slip_summary`
- [x] Total gross, deductions, net pay for a payroll period
- [x] Parameters: `company`, `payroll_period` or `from_date`/`to_date`
- [ ] Maps to: *Salary Register*

#### `payroll_cost_by_dept`
- [x] Salary cost breakdown per department
- [x] Parameters: `company`, `month`, `year`
- [ ] Maps to: *Salary Register* (grouped)

#### `pending_salary_slips`
- [x] Draft / unsubmitted salary slips needing action
- [x] Show: employee, month, status, gross
- [x] Parameters: `company`, `month`

#### `payroll_entry_status`
- [x] Payroll runs: submitted / bank transfer done / pending
- [x] Parameters: `company`, `month`
- [ ] Maps to: *Payroll Entry*

### Sample questions this module must answer
```
"What is the total salary cost this month?"
"Which salary slips are still pending submission?"
"Show payroll cost by department for March"
"Has this month's payroll been processed?"
```

---

## PHASE 6 — Supply Chain Module
> Depends on: Phase 0 + Stock + Purchase complete

### Tools to build

#### `material_request_status`
- [x] Pending MRs by type: purchase / stock transfer / manufacture
- [x] Parameters: `company`, `material_request_type`, `warehouse` (optional)
- [ ] Maps to: *Material Requests for which Supplier Quotations are Pending*

#### `delivery_fulfillment`
- [x] Sales Orders pending delivery / partial delivery
- [x] Show: SO number, customer, items, expected date, % delivered
- [x] Parameters: `company`, `customer` (optional), `from_date`, `to_date`
- [ ] Maps to: *Delivery Note Trends*

#### `po_to_invoice_flow`
- [x] Health check: POs that have receipt but no bill, bills with no PO, etc.
- [x] Parameters: `company`, `from_date`, `to_date`

#### `supplier_lead_time`
- [x] Average days from PO to GRN per supplier
- [x] Parameters: `company`, `supplier` (optional), `from_date`, `to_date`

### Sample questions this module must answer
```
"Which material requests are still pending?"
"Which sales orders haven't been delivered yet?"
"Are there any GRNs missing a purchase invoice?"
"Which supplier has the shortest lead time?"
```

---

## PHASE 7 — Manufacturing Module
> Depends on: Phase 0 + Stock complete

### Tools to build

#### `work_order_status`
- [x] Open / in-progress / completed work orders
- [x] Show: WO number, item, qty, status, expected completion
- [x] Parameters: `company`, `status`, `item_code` (optional)
- [ ] Maps to: *Work Order Summary*

#### `production_summary`
- [x] Planned vs produced qty by item / period
- [x] Parameters: `company`, `from_date`, `to_date`, `item_code` (optional)
- [ ] Maps to: *Production Analytics*

#### `bom_usage`
- [x] BOM raw material consumption vs standard (best-effort; requires submitted BOM)
- [x] Parameters: `bom_no` or `item_code`, `from_date`, `to_date`
- [ ] Maps to: *BOM Search*, *Item Shortage Report*

#### `wip_snapshot`
- [x] Work-in-progress stock: items, qty, value currently in WIP warehouse
- [x] Parameters: `company`, `wip_warehouse`

#### `downtime_summary`
- [x] Machine downtime log summary (if configured)
- [x] Parameters: `company`, `workstation` (optional), `from_date`, `to_date`

### Sample questions this module must answer
```
"How many work orders are in progress?"
"What did we produce this week vs plan?"
"Which BOM has the highest material variance?"
"What is our current WIP stock value?"
"Which machine had the most downtime this month?"
```

---

## Testing Checklist (per module)

For each module, before marking it done, verify these questions return correct answers:

- [ ] "What happened [this month / last month / this year]?" — date parsing works
- [ ] "Show me data for Company X" — multi-company filtering works
- [ ] "Who are the top 5 X?" — top-N with correct ranking
- [ ] Ask a question with missing parameter — follow-up question fires
- [ ] Ask a restricted question — permission error, no crash
- [ ] Ask a question with no matching tool — fallback logs to `MCP Query Log`

---

## MCP Query Log — Review Workflow

> Run this weekly to decide what to build next.

1. Open `MCP Query Log` report in ERPNext
2. Filter: `tool_matched = No` and `fallback_used = Yes`
3. Group by `question` — find the most repeated unanswered questions
4. Top 3 repeated questions = next 3 tools to build
5. Tick `flagged_for_tool = Yes` and add dev notes
6. Add to the task list above in the relevant module phase

---

## Implementation Order Summary

```
Phase 0 — Core Foundation          ← DO THIS FIRST, everything depends on it
Phase 1 — Sales                    ← Most visible, easiest to validate
Phase 2 — Stock                    ← Second most used in most businesses
Phase 3 — Purchase                 ← Pairs naturally with Stock
Phase 4 — HR                       ← Independent, can be parallel with Phase 3
Phase 5 — Payroll                  ← After HR
Phase 6 — Supply Chain             ← After Stock + Purchase
Phase 7 — Manufacturing            ← After Stock, last (most complex)
```

---

## Notes & Decisions to Make Before Starting

| Decision | Options | Default |
|---|---|---|
| ERPNext version | v13 / v14 / v15 | Confirm before Phase 0 |
| Primary company name | Single / Multi | Confirm for date+company filters |
| Fiscal year start | Jan / Apr / Jul / custom | Read from ERPNext System Settings |
| Currency / locale | BDT / USD / etc. | Read from ERPNext Company settings |
| MCP transport | stdio / SSE | Confirm before Phase 0 |
| Fallback SQL — allowed or disabled | Allowed (logged) / Disabled | Allowed + logged recommended |

---

*Last updated: Phases 0–3 completed (Sales, Stock, Purchase)*
*Next action: Phase 4 — HR module tools (`employee_directory`, `attendance_summary`, `leave_balance`, `leave_summary`, `hiring_stats`)*