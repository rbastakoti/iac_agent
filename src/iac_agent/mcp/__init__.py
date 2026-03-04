"""
MCP (Model Context Protocol) integration for IaC Agent.
Now using FastMCP for simplified implementation with organized workspace module.
"""
from .workspace import FastMCPClient, fastmcp_client

# For backward compatibility, alias fastmcp_client as mcp_client
mcp_client = fastmcp_client

__all__ = ["FastMCPClient", "fastmcp_client", "mcp_client"]