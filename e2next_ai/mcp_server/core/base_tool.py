"""Base class for all MCP tools.

Every tool inherits from MCPTool and gets:
- Standard response envelope (status, tool, query_time_ms, data, summary, table)
- Automatic timing
- Query source tracking
- Error handling that never exposes raw SQL/stack traces
"""

from __future__ import annotations

import time
import traceback
from abc import ABC, abstractmethod
from typing import Any


class MCPTool(ABC):
	"""Base class all MCP tools must inherit from."""

	# Subclasses must set these
	name: str = ""
	description: str = ""
	parameters: dict[str, Any] = {}

	def execute(self, **kwargs: Any) -> dict[str, Any]:
		"""Run the tool with timing and standard envelope.

		Subclasses implement `run()` — this method wraps it.
		"""
		start = time.perf_counter()
		query_source = None
		try:
			result = self.run(**kwargs)
			elapsed_ms = round((time.perf_counter() - start) * 1000)

			data = result.get("data", {})
			summary = result.get("summary", "")
			table = result.get("table", None)
			query_source = result.get("_query_source", None)

			response = {
				"status": "success",
				"tool": self.name,
				"query_time_ms": elapsed_ms,
				"data": data,
				"summary": summary,
			}
			if table is not None:
				response["table"] = table
			if query_source:
				response["_query_source"] = query_source

			return response

		except PermissionError as e:
			elapsed_ms = round((time.perf_counter() - start) * 1000)
			return {
				"status": "error",
				"tool": self.name,
				"query_time_ms": elapsed_ms,
				"error": str(e),
				"error_type": "permission",
			}

		except ValueError as e:
			elapsed_ms = round((time.perf_counter() - start) * 1000)
			return {
				"status": "error",
				"tool": self.name,
				"query_time_ms": elapsed_ms,
				"error": str(e),
				"error_type": "validation",
			}

		except Exception:
			elapsed_ms = round((time.perf_counter() - start) * 1000)
			# Log the real error server-side but never expose to user
			traceback.print_exc()
			return {
				"status": "error",
				"tool": self.name,
				"query_time_ms": elapsed_ms,
				"error": "An internal error occurred. Please try again or rephrase your question.",
				"error_type": "internal",
			}

	@abstractmethod
	def run(self, **kwargs: Any) -> dict[str, Any]:
		"""Execute the tool logic.

		Must return a dict with at least:
		  - "data": dict — the actual result data
		  - "summary": str — one-line plain English summary

		Optional keys:
		  - "table": list[dict] — tabular rows for display
		  - "_query_source": str — SQL or ORM call used (for logging)
		"""
		...

	def get_info(self) -> dict[str, Any]:
		"""Return tool metadata for the registry."""
		return {
			"name": self.name,
			"description": self.description,
			"parameters": self.parameters,
		}
