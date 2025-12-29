"""
MCP Models Package

This package provides MCP (Model Context Protocol) tools for various services.
Each service has its own module under mcp_models/.

Available modules:
- calendar: Google Calendar integration tools
- github: GitHub integration tools (planned)
- linkedin: LinkedIn integration tools (planned)
"""

from mcp_models.calendar import MCPCalendarTools, get_calendar_tools, execute_calendar_tool

# Re-export main functions for backward compatibility
from mcp_models.calendar import get_tools, execute_tool

__all__ = [
    'MCPCalendarTools',
    'get_calendar_tools',
    'execute_calendar_tool',
    'get_tools',
    'execute_tool',
]
