import click


@click.command("mcp-server")
@click.option("--transport", default="sse", type=click.Choice(["stdio", "sse"]), help="MCP transport type")
@click.option("--host", default=None, help="Host to bind SSE server (default: 0.0.0.0)")
@click.option("--port", default=None, type=int, help="Port for SSE server (default: 8001)")
def mcp_server(transport, host, port):
	"""Start the E2Next AI MCP server."""
	from e2next_ai.mcp_server.server import mcp

	if host:
		mcp.settings.host = host
	if port:
		mcp.settings.port = port

	mcp.run(transport=transport)


commands = [mcp_server]
