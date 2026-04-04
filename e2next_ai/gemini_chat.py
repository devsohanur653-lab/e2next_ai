"""Gemini LLM chat backend for E2Next AI.

Orchestrates Gemini 2.5 Flash with function calling,
using the existing ToolRegistry to execute MCP tool calls.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import frappe
from google import genai
from google.genai import types

from e2next_ai.mcp_server.core.tool_registry import registry

# Cache TTL for conversation history (seconds)
_CHAT_TTL = 7200  # 2 hours

# ── Settings ──────────────────────────────────────────────────────


def _get_settings() -> dict[str, Any]:
	"""Load E2Next AI Settings (cached per request)."""
	settings = frappe.get_cached_doc("E2Next AI Settings")
	if not settings.enabled:
		frappe.throw("E2Next AI is not enabled. Please enable it in E2Next AI Settings.")
	api_key = settings.get_password("gemini_api_key")
	if not api_key:
		frappe.throw("Gemini API key is not configured. Please set it in E2Next AI Settings.")
	return {
		"api_key": api_key,
		"model": settings.gemini_model or "gemini-2.5-flash",
		"system_prompt": settings.system_prompt or "",
		"max_tool_rounds": settings.max_tool_rounds or 5,
		"max_result_chars": settings.max_result_chars or 4000,
	}


# ── Tool declarations for Gemini ─────────────────────────────────

_TYPE_MAP = {
	"str": "STRING",
	"string": "STRING",
	"int": "INTEGER",
	"integer": "INTEGER",
	"float": "NUMBER",
	"number": "NUMBER",
	"bool": "BOOLEAN",
	"boolean": "BOOLEAN",
}


def _build_gemini_tools() -> list[types.Tool]:
	"""Convert MCP tool registry to Gemini function declarations."""
	from e2next_ai.api import _ensure_registry

	_ensure_registry()

	declarations = []
	for tool_info in registry.list_tools():
		properties = {}
		required = []

		for param_name, param_meta in (tool_info.get("parameters") or {}).items():
			schema_type = _TYPE_MAP.get(param_meta.get("type", "str"), "STRING")
			properties[param_name] = types.Schema(
				type=schema_type,
				description=param_meta.get("description", ""),
			)
			if param_meta.get("required"):
				required.append(param_name)

		fn_schema = None
		if properties:
			fn_schema = types.Schema(
				type="OBJECT",
				properties=properties,
				required=required if required else None,
			)

		declarations.append(types.FunctionDeclaration(
			name=tool_info["name"],
			description=tool_info.get("description", ""),
			parameters=fn_schema,
		))

	return [types.Tool(function_declarations=declarations)]


# ── Conversation history (Redis) ─────────────────────────────────


def _cache_key(session_id: str) -> str:
	user = frappe.session.user or "Guest"
	return f"e2next_chat:{user}:{session_id}"


def _load_history(session_id: str) -> list[dict]:
	raw = frappe.cache.get_value(_cache_key(session_id))
	if raw:
		return json.loads(raw)
	return []


def _save_history(session_id: str, history: list[dict]) -> None:
	# Keep only last 40 messages to avoid token overflow
	trimmed = history[-40:]
	frappe.cache.set_value(_cache_key(session_id), json.dumps(trimmed), expires_in_sec=_CHAT_TTL)


# ── Chat orchestration ───────────────────────────────────────────


def _build_system_prompt(base_prompt: str) -> str:
	"""Enrich the system prompt with user/company context."""
	parts = [base_prompt]

	company = (
		frappe.defaults.get_user_default("Company")
		or frappe.defaults.get_global_default("company")
		or ""
	)
	if company:
		parts.append(f"The user's default company is: {company}")

	user = frappe.session.user or "Guest"
	full_name = frappe.db.get_value("User", user, "full_name") or user
	parts.append(f"Current user: {full_name} ({user})")
	parts.append(f"Today's date: {frappe.utils.today()}")

	fiscal_year = frappe.defaults.get_global_default("fiscal_year")
	if fiscal_year:
		parts.append(f"Current fiscal year: {fiscal_year}")

	return "\n".join(parts)


def _truncate_result(result: dict, max_chars: int) -> dict:
	"""Truncate tool result data if it exceeds max_chars."""
	serialized = json.dumps(result, default=str)
	if len(serialized) <= max_chars:
		return result

	# Keep summary and metadata, truncate table/data
	truncated = {
		"status": result.get("status"),
		"tool": result.get("tool"),
		"query_time_ms": result.get("query_time_ms"),
		"summary": result.get("summary", ""),
	}

	data = result.get("data", {})
	if isinstance(data, dict):
		# Keep scalar values, truncate lists
		for k, v in data.items():
			if isinstance(v, list) and len(v) > 10:
				truncated.setdefault("data", {})[k] = v[:10]
				truncated.setdefault("data", {})["_truncated"] = True
				truncated.setdefault("data", {})["_total_rows"] = len(v)
			else:
				truncated.setdefault("data", {})[k] = v
	else:
		truncated["data"] = data

	return truncated


def _execute_tool_call(function_call, max_chars: int) -> dict:
	"""Execute a single Gemini function call via the tool registry."""
	tool_name = function_call.name
	args = dict(function_call.args) if function_call.args else {}

	tool = registry.get(tool_name)
	if not tool:
		return {"status": "error", "error": f"Unknown tool: {tool_name}"}

	result = tool.execute(**args)
	return _truncate_result(result, max_chars)


def _history_to_contents(history: list[dict]) -> list[types.Content]:
	"""Convert serialized history back to Gemini Content objects."""
	contents = []
	for entry in history:
		role = entry["role"]
		parts = []
		for p in entry["parts"]:
			if "text" in p:
				parts.append(types.Part.from_text(text=p["text"]))
			elif "function_call" in p:
				fc = p["function_call"]
				parts.append(types.Part.from_function_call(
					name=fc["name"],
					args=fc.get("args", {}),
				))
			elif "function_response" in p:
				fr = p["function_response"]
				parts.append(types.Part.from_function_response(
					name=fr["name"],
					response=fr.get("response", {}),
				))
		if parts:
			contents.append(types.Content(role=role, parts=parts))
	return contents


def _serialize_content(content) -> dict:
	"""Serialize a Gemini Content object for Redis storage."""
	parts = []
	for part in content.parts:
		if part.text is not None:
			parts.append({"text": part.text})
		elif part.function_call is not None:
			parts.append({
				"function_call": {
					"name": part.function_call.name,
					"args": dict(part.function_call.args) if part.function_call.args else {},
				}
			})
		elif part.function_response is not None:
			parts.append({
				"function_response": {
					"name": part.function_response.name,
					"response": dict(part.function_response.response) if part.function_response.response else {},
				}
			})
	return {"role": content.role, "parts": parts}


def _run_chat(user_message: str, session_id: str) -> dict[str, Any]:
	"""Core chat orchestration: user message → Gemini → tool calls → response."""
	settings = _get_settings()

	client = genai.Client(api_key=settings["api_key"])
	tools = _build_gemini_tools()
	system_prompt = _build_system_prompt(settings["system_prompt"])

	# Load conversation history
	history = _load_history(session_id)
	contents = _history_to_contents(history)

	# Add user message
	user_content = types.Content(
		role="user",
		parts=[types.Part.from_text(text=user_message)],
	)
	contents.append(user_content)
	history.append(_serialize_content(user_content))

	tools_called = []
	max_rounds = settings["max_tool_rounds"]
	max_chars = settings["max_result_chars"]

	for _ in range(max_rounds):
		response = client.models.generate_content(
			model=settings["model"],
			contents=contents,
			config=types.GenerateContentConfig(
				system_instruction=system_prompt,
				tools=tools,
			),
		)

		candidate = response.candidates[0]
		model_content = candidate.content

		# Serialize and store model response
		contents.append(model_content)
		history.append(_serialize_content(model_content))

		# Check if there are function calls
		function_calls = [p for p in model_content.parts if p.function_call is not None]

		if not function_calls:
			# No tool calls — we have the final text response
			break

		# Execute all function calls
		response_parts = []
		for part in function_calls:
			result = _execute_tool_call(part.function_call, max_chars)
			tools_called.append({
				"tool": part.function_call.name,
				"args": dict(part.function_call.args) if part.function_call.args else {},
				"status": result.get("status"),
				"query_time_ms": result.get("query_time_ms"),
				"summary": result.get("summary", ""),
			})
			response_parts.append(types.Part.from_function_response(
				name=part.function_call.name,
				response=result,
			))

		# Send tool results back to Gemini
		tool_response_content = types.Content(role="user", parts=response_parts)
		contents.append(tool_response_content)
		history.append(_serialize_content(tool_response_content))

	# Extract final text response
	reply = ""
	for part in contents[-1].parts if hasattr(contents[-1], "parts") else []:
		if hasattr(part, "text") and part.text:
			reply += part.text

	if not reply:
		# If the last content is a model response, extract text from it
		for content in reversed(contents):
			if hasattr(content, "role") and content.role == "model":
				for part in content.parts:
					if hasattr(part, "text") and part.text:
						reply += part.text
				if reply:
					break

	if not reply:
		reply = "I could not generate a response. Please try rephrasing your question."

	# Save conversation history
	_save_history(session_id, history)

	return {
		"reply": reply,
		"session_id": session_id,
		"tools_called": tools_called,
	}


# ── Public API ────────────────────────────────────────────────────


def handle_chat(message: str, session_id: str | None = None) -> dict[str, Any]:
	"""Entry point for the chat API.

	Args:
		message: User's question.
		session_id: Chat session ID (generated if not provided).

	Returns:
		dict with reply, session_id, tools_called.
	"""
	if not message or not message.strip():
		frappe.throw("Message cannot be empty.")

	if not session_id:
		session_id = str(uuid.uuid4())

	return _run_chat(message.strip(), session_id)
