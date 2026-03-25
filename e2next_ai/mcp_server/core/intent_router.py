"""Intent router — detects module, metric type, and entities from user questions.

Routes user questions to the correct MCP tool by:
1. Detecting the ERPNext module (sales, stock, purchase, hr, payroll, supply_chain, manufacturing)
2. Detecting the metric type (summary, trend, top_n, pending, alert, detail)
3. Extracting entities (company, warehouse, item, employee, date range)
4. Handling ambiguity with clarifying questions
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from e2next_ai.mcp_server.core.date_parser import parse_date_range


@dataclass
class Intent:
	"""Parsed intent from a user question."""

	module: str | None = None
	metric_type: str | None = None
	confidence: float = 0.0
	entities: dict[str, Any] = field(default_factory=dict)
	date_range: tuple[str, str] | None = None
	ambiguous: bool = False
	clarification: str | None = None
	matched_keywords: list[str] = field(default_factory=list)


# ── Module keyword mappings ────────────────────────────────────────

MODULE_KEYWORDS: dict[str, list[str]] = {
	"sales": [
		"sales", "sale", "revenue", "invoice", "invoiced", "invoicing",
		"customer", "customers", "receivable", "receivables",
		"sold", "selling", "sell", "order", "orders",
		"sales person", "salesperson", "sales team",
		"collection", "collected", "outstanding",
		"quotation", "quotations", "sales order",
	],
	"stock": [
		"stock", "inventory", "warehouse", "warehouses",
		"item", "items", "reorder", "restock",
		"stock balance", "stock ledger", "stock movement",
		"batch", "batches", "serial", "aging", "ageing",
		"slow moving", "dead stock", "wip",
	],
	"purchase": [
		"purchase", "purchases", "procurement", "procure",
		"supplier", "suppliers", "vendor", "vendors",
		"payable", "payables", "purchase order", "po",
		"grn", "goods receipt", "purchase receipt",
		"purchase invoice", "bill", "billed", "unbilled",
	],
	"hr": [
		"employee", "employees", "staff", "headcount",
		"attendance", "absent", "present", "late",
		"leave", "leaves", "leave balance", "on leave",
		"department", "departments", "designation",
		"hiring", "recruitment", "job opening", "applicant",
	],
	"payroll": [
		"salary", "salaries", "payroll", "pay",
		"salary slip", "salary slips", "wage", "wages",
		"deduction", "deductions", "gross", "net pay",
		"payroll entry", "payroll cost",
	],
	"supply_chain": [
		"material request", "delivery", "deliveries",
		"fulfillment", "fulfilment", "delivery note",
		"lead time", "supply chain", "logistics",
		"pending delivery", "undelivered",
	],
	"manufacturing": [
		"manufacturing", "production", "produce", "produced",
		"work order", "work orders", "bom", "bill of material",
		"workstation", "downtime", "oee",
		"raw material", "wip", "work in progress",
	],
}

# ── Metric type keywords ──────────────────────────────────────────

METRIC_KEYWORDS: dict[str, list[str]] = {
	"summary": [
		"summary", "total", "totals", "how much", "what is",
		"what are", "what were", "overview", "overall",
		"aggregate", "count", "how many",
	],
	"trend": [
		"trend", "trending", "compare", "comparison",
		"growth", "decline", "change", "vs", "versus",
		"month over month", "year over year", "daily",
		"monthly", "weekly", "over time",
	],
	"top_n": [
		"top", "best", "highest", "most", "largest",
		"biggest", "rank", "ranking", "bottom", "worst",
		"lowest", "least",
	],
	"pending": [
		"pending", "open", "draft", "unpaid", "overdue",
		"not received", "not delivered", "not billed",
		"awaiting", "incomplete", "outstanding",
	],
	"alert": [
		"alert", "warning", "below", "reorder",
		"critical", "shortage", "low stock", "expired",
		"at risk", "overdue",
	],
	"detail": [
		"detail", "details", "show me", "list",
		"ledger", "history", "entries", "movements",
		"breakdown", "by", "per", "each", "individual",
	],
}

# ── Date-related phrases to extract ───────────────────────────────

DATE_PHRASES = [
	r"today",
	r"yesterday",
	r"this week",
	r"last week",
	r"this month",
	r"last month",
	r"this quarter",
	r"last quarter",
	r"this year",
	r"last year",
	r"this fiscal year",
	r"last fiscal year",
	r"current year",
	r"previous year",
	r"current fiscal year",
	r"previous fiscal year",
	r"last \d+ days?",
	r"fy\s*\d{4}(?:-\d{2,4})?",
	r"\d{4}-\d{2}-\d{2}(?:\s+to\s+\d{4}-\d{2}-\d{2})?",
]

CONFIDENCE_THRESHOLD = 0.6


def detect_intent(question: str) -> Intent:
	"""Analyze a user question and detect the intent.

	Returns an Intent object with module, metric_type, entities, etc.
	"""
	q = question.strip().lower()
	intent = Intent()

	# 1. Extract date range
	intent.date_range = _extract_date_range(q)

	# 2. Detect module
	module_scores: dict[str, float] = {}
	for module, keywords in MODULE_KEYWORDS.items():
		score, matched = _score_keywords(q, keywords)
		if score > 0:
			module_scores[module] = score
			intent.matched_keywords.extend(matched)

	if module_scores:
		sorted_modules = sorted(module_scores.items(), key=lambda x: x[1], reverse=True)
		best_module, best_score = sorted_modules[0]

		# Check for ambiguity: two modules with similar scores
		if len(sorted_modules) > 1:
			second_module, second_score = sorted_modules[1]
			if second_score >= best_score * 0.8:
				intent.ambiguous = True
				intent.clarification = (
					f"Your question could relate to {best_module} or {second_module}. "
					f"Which module did you mean?"
				)

		intent.module = best_module
		# Normalize confidence: max possible score varies, use a heuristic
		intent.confidence = min(best_score / 3.0, 1.0)

	# 3. Detect metric type
	metric_scores: dict[str, float] = {}
	for metric, keywords in METRIC_KEYWORDS.items():
		score, matched = _score_keywords(q, keywords)
		if score > 0:
			metric_scores[metric] = score
			intent.matched_keywords.extend(matched)

	if metric_scores:
		intent.metric_type = max(metric_scores, key=metric_scores.get)

	# 4. Extract entities
	intent.entities = _extract_entities(q)

	# 5. If confidence below threshold, suggest clarification
	if intent.confidence < CONFIDENCE_THRESHOLD and not intent.clarification:
		intent.clarification = "Could you clarify what you're looking for? For example: sales, stock, purchase, HR, or payroll data?"

	return intent


def _score_keywords(text: str, keywords: list[str]) -> tuple[float, list[str]]:
	"""Score how well a text matches a list of keywords.

	Returns (score, matched_keywords). Multi-word keywords score higher.
	"""
	score = 0.0
	matched = []
	for kw in keywords:
		# Multi-word keywords: exact phrase match (worth more)
		if " " in kw:
			if kw in text:
				score += 2.0
				matched.append(kw)
		else:
			# Single word: word boundary match
			if re.search(rf"\b{re.escape(kw)}\b", text):
				score += 1.0
				matched.append(kw)
	return score, matched


def _extract_date_range(text: str) -> tuple[str, str] | None:
	"""Extract a date range phrase from text and parse it."""
	for pattern in DATE_PHRASES:
		match = re.search(pattern, text, re.IGNORECASE)
		if match:
			result = parse_date_range(match.group(0))
			if result:
				return result
	return None


def _extract_entities(text: str) -> dict[str, Any]:
	"""Extract named entities (company, warehouse, item, employee, limit) from text."""
	entities: dict[str, Any] = {}

	# Extract "top N" / "N" limits
	top_match = re.search(r"\btop\s+(\d+)\b", text)
	if top_match:
		entities["limit"] = int(top_match.group(1))

	# Extract "for company X" / "of company X"
	company_match = re.search(r"(?:for|of|in|at)\s+company\s+[\"']?([^\"',]+?)[\"']?\s*(?:\?|$|,|\.)", text)
	if company_match:
		entities["company"] = company_match.group(1).strip()

	# Extract "warehouse X" / "in warehouse X"
	wh_match = re.search(r"(?:in|at|for|from)?\s*warehouse\s+[\"']?([^\"',]+?)[\"']?\s*(?:\?|$|,|\.)", text)
	if wh_match:
		entities["warehouse"] = wh_match.group(1).strip()

	# Extract "item X" / "for item X"
	item_match = re.search(r"(?:for|of)?\s*item\s+[\"']?([^\"',]+?)[\"']?\s*(?:\?|$|,|\.)", text)
	if item_match:
		entities["item_code"] = item_match.group(1).strip()

	# Extract "employee X" / "for employee X"
	emp_match = re.search(r"(?:for|of)?\s*employee\s+[\"']?([^\"',]+?)[\"']?\s*(?:\?|$|,|\.)", text)
	if emp_match:
		entities["employee"] = emp_match.group(1).strip()

	# Extract "department X"
	dept_match = re.search(r"(?:for|of|in|by)?\s*department\s+[\"']?([^\"',]+?)[\"']?\s*(?:\?|$|,|\.)", text)
	if dept_match:
		entities["department"] = dept_match.group(1).strip()

	# Extract "customer X" / "for customer X"
	cust_match = re.search(r"(?:for|of|from)?\s*customer\s+[\"']?([^\"',]+?)[\"']?\s*(?:\?|$|,|\.)", text)
	if cust_match:
		entities["customer"] = cust_match.group(1).strip()

	# Extract "supplier X"
	sup_match = re.search(r"(?:for|of|from|to)?\s*supplier\s+[\"']?([^\"',]+?)[\"']?\s*(?:\?|$|,|\.)", text)
	if sup_match:
		entities["supplier"] = sup_match.group(1).strip()

	return entities
