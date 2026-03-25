"""Tool registry — central catalog of all MCP tools.

Usage:
    from e2next_ai.mcp_server.core.tool_registry import registry

    # Register a tool class
    registry.register(SaleSummaryTool)

    # Look up by name
    tool = registry.get("sales_summary")
    result = tool.execute(company="My Co", from_date="2025-01-01", to_date="2025-01-31")

    # List all tools
    all_tools = registry.list_tools()
"""

from __future__ import annotations

from typing import Any

from e2next_ai.mcp_server.core.base_tool import MCPTool


class ToolRegistry:
	"""Singleton registry that holds all registered MCP tools."""

	def __init__(self) -> None:
		self._tools: dict[str, MCPTool] = {}

	def register(self, tool_class: type[MCPTool]) -> MCPTool:
		"""Instantiate and register a tool class. Returns the instance."""
		instance = tool_class()
		if not instance.name:
			raise ValueError(f"{tool_class.__name__} must define a `name` attribute")
		if instance.name in self._tools:
			raise ValueError(f"Tool {instance.name!r} is already registered")
		self._tools[instance.name] = instance
		return instance

	def get(self, name: str) -> MCPTool | None:
		"""Look up a tool by name. Returns None if not found."""
		return self._tools.get(name)

	def list_tools(self) -> list[dict[str, Any]]:
		"""Return metadata for all registered tools."""
		return [tool.get_info() for tool in self._tools.values()]

	def all_names(self) -> list[str]:
		"""Return sorted list of all tool names."""
		return sorted(self._tools.keys())

	def all_tools(self) -> dict[str, MCPTool]:
		"""Return the full tool mapping."""
		return dict(self._tools)

	def __contains__(self, name: str) -> bool:
		return name in self._tools

	def __len__(self) -> int:
		return len(self._tools)


# Module-level singleton
registry = ToolRegistry()
