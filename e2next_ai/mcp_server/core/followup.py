"""Follow-up question engine for MCP tools.

When a tool requires parameters the user hasn't provided:
- Identifies which parameters are missing
- Asks ONE question at a time
- Stores partial context in session so user can answer naturally
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import frappe


@dataclass
class ToolParam:
	"""Definition of a tool parameter."""

	name: str
	label: str
	required: bool = False
	param_type: str = "str"  # str, int, float, date, date_range
	options: list[str] | None = None
	default: Any = None
	prompt: str = ""  # Question to ask user if missing


@dataclass
class PendingContext:
	"""Partial context for a tool execution awaiting more info."""

	tool_name: str
	provided_params: dict[str, Any] = field(default_factory=dict)
	missing_params: list[ToolParam] = field(default_factory=list)
	asking_for: str | None = None


# In-memory session store (per user)
# In production, this could be backed by Redis/cache
_sessions: dict[str, PendingContext] = {}


def get_session_key() -> str:
	"""Get a unique session key for the current user."""
	return frappe.session.user or "Guest"


def get_pending_context() -> PendingContext | None:
	"""Get the pending context for the current user, if any."""
	return _sessions.get(get_session_key())


def set_pending_context(ctx: PendingContext) -> None:
	"""Store a pending context for the current user."""
	_sessions[get_session_key()] = ctx


def clear_pending_context() -> None:
	"""Clear the pending context for the current user."""
	_sessions.pop(get_session_key(), None)


def check_missing_params(
	tool_name: str,
	required_params: list[ToolParam],
	provided: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
	"""Check for missing required parameters and return the next question.

	Args:
		tool_name: Name of the tool being invoked.
		required_params: List of ToolParam definitions.
		provided: Parameters already provided by the user.

	Returns:
		(complete_params, follow_up_question)
		- If all required params present: (params_dict, None)
		- If something missing: (partial_params, question_string)
	"""
	params = dict(provided)
	missing = []

	for param in required_params:
		if param.name in params and params[param.name] is not None:
			continue
		if param.default is not None:
			params[param.name] = param.default
			continue
		if param.required:
			missing.append(param)

	if not missing:
		clear_pending_context()
		return params, None

	# Ask for the first missing parameter
	next_param = missing[0]
	question = next_param.prompt or f"Which {next_param.label}?"

	# Add options hint if available
	if next_param.options:
		options_str = ", ".join(next_param.options[:10])
		question += f" (e.g. {options_str})"

	# Store context so user's next message resolves this
	ctx = PendingContext(
		tool_name=tool_name,
		provided_params=params,
		missing_params=missing[1:],  # remaining after current
		asking_for=next_param.name,
	)
	set_pending_context(ctx)

	return params, question


def resolve_followup(user_reply: str) -> tuple[str, dict[str, Any], str | None]:
	"""Resolve a follow-up answer from the user.

	Args:
		user_reply: The user's reply to the follow-up question.

	Returns:
		(tool_name, updated_params, next_question_or_none)
		- If all resolved: (tool_name, complete_params, None)
		- If more needed: (tool_name, partial_params, next_question)
	"""
	ctx = get_pending_context()
	if not ctx:
		return ("", {}, None)

	# Apply the user's reply to the parameter we asked for
	ctx.provided_params[ctx.asking_for] = user_reply.strip()

	# Check if there are more missing parameters
	if ctx.missing_params:
		next_param = ctx.missing_params[0]
		question = next_param.prompt or f"Which {next_param.label}?"
		if next_param.options:
			options_str = ", ".join(next_param.options[:10])
			question += f" (e.g. {options_str})"

		ctx.missing_params = ctx.missing_params[1:]
		ctx.asking_for = next_param.name
		set_pending_context(ctx)

		return (ctx.tool_name, ctx.provided_params, question)

	# All params resolved
	params = ctx.provided_params
	tool_name = ctx.tool_name
	clear_pending_context()
	return (tool_name, params, None)
