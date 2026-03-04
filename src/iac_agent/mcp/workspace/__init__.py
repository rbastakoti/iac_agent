"""
Workspace MCP module for file operations.
Contains FastMCP-based file server and client for workspace management.
"""
from .client import FastMCPClient, fastmcp_client

__all__ = ["FastMCPClient", "fastmcp_client"]