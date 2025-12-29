"""
MCP Models Package

This package provides MCP (Model Context Protocol) tools for various services.
Each service has its own module under mcp_models/.

Available modules:
- calendar: Google Calendar integration tools
- github: GitHub integration tools
- linkedin: LinkedIn integration tools (planned)
"""

from typing import Any, Dict, List

from mcp_models.calendar import MCPCalendarTools, get_calendar_tools, execute_calendar_tool
from mcp_models.github import MCPGitHubTools, get_github_tools, execute_github_tool
from pages.authorization.data import check_github_connection


def get_tools(user_id: int) -> List[Dict[str, Any]]:
    """Get all available tools (calendar + GitHub) for the user."""
    # Get calendar tools
    tools = get_calendar_tools(user_id)
    
    # Try to get GitHub tools (if connected)
    try:
        # Check if GitHub is connected (synchronously)
        connection_status = check_github_connection(user_id)
        
        if connection_status:
            github_tools_instance = MCPGitHubTools(user_id)
            
            # Add GitHub tools with direct method references (like calendar)
            github_method_map = {
                "github_is_connected": github_tools_instance.is_connected,
                "github_list_repositories": github_tools_instance.list_repositories,
                "github_get_repository_details": github_tools_instance.get_repository_details,
                "github_get_repo_structure": github_tools_instance.get_repo_structure,
                "github_read_file": github_tools_instance.read_file,
                "github_summarize_repository": github_tools_instance.summarize_repository,
                "github_create_repository_with_code": github_tools_instance.create_repository_with_code,
                "github_create_empty_repository": github_tools_instance.create_empty_repository,
                "github_list_issues": github_tools_instance.list_issues,
                "github_create_issue": github_tools_instance.create_issue,
                "github_close_issue": github_tools_instance.close_issue,
                "github_list_pull_requests": github_tools_instance.list_pull_requests,
                "github_summarize_pull_request": github_tools_instance.summarize_pull_request,
                "github_comment_on_pull_request": github_tools_instance.comment_on_pull_request,
                "github_read_notifications": github_tools_instance.read_notifications,
                "github_mark_notification_as_read": github_tools_instance.mark_notification_as_read,
            }
            
            github_tool_defs = get_github_tools(user_id)
            for tool_def in github_tool_defs:
                tool_name = tool_def['name']
                if tool_name in github_method_map:
                    tools.append({
                        'name': tool_name,
                        'description': tool_def['description'],
                        'parameters': tool_def['parameters'],
                        'function': github_method_map[tool_name]
                    })
    except Exception as e:
        # GitHub tools not available, continue with calendar only
        pass
    
    return tools


async def execute_tool(user_id: int, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute any MCP tool (calendar or GitHub) by name."""
    # Check if it's a GitHub tool
    if tool_name.startswith('github_'):
        try:
            return await execute_github_tool(user_id, tool_name, parameters)
        except Exception as e:
            return {'success': False, 'error': f"GitHub tool error: {str(e)}"}
    
    # Otherwise, it's a calendar tool
    return await execute_calendar_tool(user_id, tool_name, parameters)


__all__ = [
    # Combined tools
    'get_tools',
    'execute_tool',
    # Calendar
    'MCPCalendarTools',
    'get_calendar_tools',
    'execute_calendar_tool',
    # GitHub
    'MCPGitHubTools',
    'get_github_tools',
    'execute_github_tool',
]
