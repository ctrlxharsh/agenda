"""
Chatbot Logic with LangGraph Agent

This module implements the chatbot logic using LangGraph for agent orchestration
and OpenAI for language model capabilities. The agent can call MCP tools to
manage calendar tasks and events.
"""

import logging
import os
import asyncio
import inspect
from typing import Any, Dict, List, Optional, AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

from utils.env_config import get_openai_api_key
import mcp_models

# Configure logging for observability
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Condensed, production-ready system prompt
SYSTEM_PROMPT = """You are a helpful AI assistant. You manage the user's calendar, tasks, meetings, and GitHub repositories.

**Calendar Tools:**
- save_todo_only: Save task to todo list (no calendar)
- add_task_to_calendar: Add task/event to calendar
- schedule_meeting: Meeting with collaborators and Google Meet
- get_collaborators: Search friends in user's network
- add_collaborators_to_event: Add people to existing event
- generate_meeting_link: Create/attach Google Meet link
- get_calendar_events: List events for a date range

**GitHub Tools (if connected):**
- github_list_repositories: List user's repos
- github_get_repository_details: Get repo info
- github_create_repository_with_code: Create repo with YOUR CUSTOM CODE (games, apps, etc)
- github_create_empty_repository: Create empty repo with README, .gitignore, license. Returns clone command.
- github_list_issues / github_create_issue / github_close_issue: Manage issues
- github_list_pull_requests / github_comment_on_pull_request: Manage PRs
- github_read_notifications / github_mark_notification_as_read: Notifications

**Rules:**
1. Only use available tools.
2. **Be Proactive:** If the user's intent is clear, execute it immediately without asking for confirmation. Only ask for clarification if critical information is genuinely missing and cannot be reasonably inferred.
3. **Auto-fill Smart Defaults:** Use intelligent defaults when needed (e.g., current time, standard duration, reasonable descriptions). Don't ask the user to confirm obvious choices.
4. Never call multiple creation tools for the same request.
5. For meetings: Only ask for time and attendees if not provided. Don't ask about optional fields.
6. Timezone: Asia/Kolkata.

**GitHub Project Creation - CRITICAL:**
6. For SPECIFIC projects (game, app, portfolio, or simple websites): Use `github_create_repository_with_code`.
   - You MUST provide `name` (not repo_name).
   - You MUST provide `html_content` (full HTML code).
   - You CAN provide `css_content` and `js_content`.
   - Do NOT invent parameters like "stack", "single_page", "enable_pages".
8. For "new python project", "init a node project", etc: Use `github_create_empty_repository` with correct `project_type`.
9. Keep responses SHORT - just show URLs and clone command, don't output code.
10. GitHub Pages will be enabled automatically for web projects.

Be conversational, friendly, and CONCISE!"""


class ChatbotAgent:
    """LangGraph-powered chatbot agent using create_react_agent."""
    
    def __init__(self, user_id: int, username: str):
        """
        Initialize the chatbot agent.
        
        Args:
            user_id: ID of the user chatting
            username: Username for personalization
        """
        self.user_id = user_id
        self.username = username
        
        logger.info(f"Initializing ChatbotAgent for user_id={user_id}, username={username}")
        
        # Initialize OpenAI client
        api_key = get_openai_api_key()
        self.llm = ChatOpenAI(
            model="gpt-5-mini",
            temperature=0.6,
            api_key=api_key
        )
        
        # Create tools from MCP server
        self.tools = self._create_langchain_tools()
        logger.info(f"Created {len(self.tools)} tools")
        
        # Create the agent using LangGraph's prebuilt create_react_agent
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=SYSTEM_PROMPT
        )
        
        logger.info("LangGraph agent created successfully")
    
    def _create_langchain_tools(self) -> List[StructuredTool]:
        """
        Create LangChain tools from MCP server tools.
        
        Returns:
            List of LangChain StructuredTool objects
        """
        from pydantic import BaseModel, create_model, Field
        
        mcp_tools = mcp_models.get_tools(self.user_id)
        langchain_tools = []
        
        for mcp_tool in mcp_tools:
            tool_func = mcp_tool['function']
            tool_name = mcp_tool['name']
            tool_desc = mcp_tool['description']
            tool_params = mcp_tool.get('parameters', {})
            
            # Check if the function is a coroutine function
            if inspect.iscoroutinefunction(tool_func):
                # For async tools with parameters schema, create args_schema
                if tool_params and 'properties' in tool_params:
                    # Build pydantic model from JSON schema
                    fields = {}
                    for param_name, param_def in tool_params['properties'].items():
                        param_type = str  # default
                        param_default = ...  # required by default
                        
                        # Map JSON types to Python types
                        if param_def.get('type') == 'integer':
                            param_type = int
                        elif param_def.get('type') == 'boolean':
                            param_type = bool
                        elif param_def.get('type') == 'array':
                            param_type = list
                        elif param_def.get('type') == 'object':
                            param_type = dict
                        
                        # Check if parameter is required
                        if param_name not in tool_params.get('required', []):
                            param_default = param_def.get('default', None)
                        
                        fields[param_name] = (param_type, param_default)
                    
                    # Create pydantic model
                    ArgsSchema = create_model(f"{tool_name}_args", **fields)
                    
                    structured_tool = StructuredTool(
                        name=tool_name,
                        description=tool_desc,
                        coroutine=tool_func,
                        args_schema=ArgsSchema
                    )
                else:
                    # No schema, use from_function
                    structured_tool = StructuredTool.from_function(
                        func=lambda: None,
                        coroutine=tool_func,
                        name=tool_name,
                        description=tool_desc
                    )
            else:
                # Standard sync tool
                structured_tool = StructuredTool.from_function(
                    func=tool_func,
                    name=tool_name,
                    description=tool_desc
                )
            
            langchain_tools.append(structured_tool)
        
        return langchain_tools
    
    async def chat_stream(self, user_message: str, chat_history: Optional[List[Dict]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message and yield events from the agent.
        
        Args:
            user_message: The user's message
            chat_history: Previous chat messages (optional)
            
        Yields:
            Dictionary containing event type and data
        """
        logger.info(f"Chat Stream: Received - {user_message[:50]}...")
        
        # Convert chat history to LangChain messages
        messages: List[BaseMessage] = []
        
        if chat_history:
            for msg in chat_history:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(AIMessage(content=msg['content']))
        
        # Add current user message
        messages.append(HumanMessage(content=user_message))
        
        try:
            # Stream events from the agent
            async for event in self.agent.astream_events({"messages": messages}, version="v1"):
                kind = event["event"]
                
                # Yield token events for streaming the response
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield {
                            "type": "token",
                            "content": content
                        }
                
                # Yield tool start events
                elif kind == "on_tool_start":
                    yield {
                        "type": "tool_start",
                        "tool": event["name"],
                        "input": event["data"].get("input")
                    }
                
                # Yield tool end events
                elif kind == "on_tool_end":
                    yield {
                        "type": "tool_end",
                        "tool": event["name"],
                        "output": event["data"].get("output")
                    }
                    
        except Exception as e:
            logger.error(f"Chat Stream: Agent failed - {e}")
            yield {
                "type": "error",
                "content": "I apologize, but I encountered an error processing your request."
            }

    def chat(self, user_message: str, chat_history: Optional[List[Dict]] = None) -> str:
        """
        Process a user message and return the response (Synchronous wrapper).
        DEPRECATED: Use chat_stream for async/streaming support.
        
        Args:
            user_message: The user's message
            chat_history: Previous chat messages (optional)
            
        Returns:
            The assistant's response
        """
        # This is a legacy wrapper. Ideally, the UI should use chat_stream.
        # Since we can't easily run async code here without an event loop,
        # we'll try to use asyncio.run if no loop is running.
        
        async def run_chat():
            full_response = ""
            async for event in self.chat_stream(user_message, chat_history):
                if event["type"] == "token":
                    full_response += event["content"]
            return full_response

        try:
            return asyncio.run(run_chat())
        except RuntimeError:
            # If loop is already running (e.g. in Streamlit), we can't use asyncio.run
            # This method shouldn't be used in async contexts anyway.
            return "Error: Synchronous chat called in async context. Use chat_stream."


def create_chatbot(user_id: int, username: str) -> ChatbotAgent:
    """
    Factory function to create a chatbot agent.
    
    Args:
        user_id: User ID
        username: Username
        
    Returns:
        Initialized ChatbotAgent
    """
    return ChatbotAgent(user_id, username)
