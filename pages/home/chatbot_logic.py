"""
Chatbot Logic with LangGraph Agent

This module implements the chatbot logic using LangGraph for agent orchestration
and OpenAI for language model capabilities. The agent can call MCP tools to
manage calendar tasks and events.
"""

import logging
import os
from typing import Any, Dict, List, Optional

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
SYSTEM_PROMPT = """You are a helpful AI assistant. You manage the user's calendar, tasks, and meetings using Google Calendar.

**Tools:**
- save_todo_only: Save task to todo list (no calendar)
- add_task_to_calendar: Add task/event to calendar
- schedule_meeting: Meeting with collaborators and Google Meet
- get_collaborators: Search friends in user's network
- add_collaborators_to_event: Add people to existing event
- generate_meeting_link: Create/attach Google Meet link
- get_calendar_events: List events for a date range

**Rules:**
1. Only use listed tools. Ask for missing info instead of assuming.
2. Never call multiple creation tools for the same request.
3. If asked something you can't do, say so clearly.
4. For todos: Ask if user wants calendar or just todo list.
5. For meetings: Gather title, time, attendees before scheduling.
6. Default: tasks → tomorrow 10 AM; events → 1 hour; priority → medium.
7. Timezone: Asia/Kolkata.

Be conversational and friendly!"""


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
        
        # Save graph visualization for debugging
        self._save_graph_debug()
        
        logger.info("LangGraph agent created successfully")
    
    def _create_langchain_tools(self) -> List[StructuredTool]:
        """
        Create LangChain tools from MCP server tools.
        
        Returns:
            List of LangChain StructuredTool objects
        """
        mcp_tools = mcp_models.get_tools(self.user_id)
        langchain_tools = []
        
        for mcp_tool in mcp_tools:
            tool_func = mcp_tool['function']
            tool_name = mcp_tool['name']
            tool_desc = mcp_tool['description']
            
            structured_tool = StructuredTool.from_function(
                func=tool_func,
                name=tool_name,
                description=tool_desc
            )
            langchain_tools.append(structured_tool)
        
        return langchain_tools
    
    def _save_graph_debug(self):
        """
        Save graph visualization for debugging.
        Creates a PNG diagram of the agent graph.
        """
        try:
            # Get the graph as PNG
            mermaid_png = self.agent.get_graph().draw_mermaid_png()
            
            # Save to debug directory
            debug_dir = os.path.join(os.path.dirname(__file__), "debug")
            os.makedirs(debug_dir, exist_ok=True)
            
            graph_path = os.path.join(debug_dir, "langgraph_agent.png")
            with open(graph_path, "wb") as f:
                f.write(mermaid_png)
            
            logger.info(f"Graph visualization saved to: {graph_path}")
            
        except Exception as e:
            logger.warning(f"Could not save graph visualization: {e}")
    
    def get_graph_mermaid(self) -> str:
        """
        Get the graph as a Mermaid diagram string.
        
        Returns:
            Mermaid diagram string
        """
        try:
            return self.agent.get_graph().draw_mermaid()
        except Exception as e:
            logger.warning(f"Could not generate Mermaid diagram: {e}")
            return ""
    
    def chat(self, user_message: str, chat_history: Optional[List[Dict]] = None) -> str:
        """
        Process a user message and return the response.
        
        Args:
            user_message: The user's message
            chat_history: Previous chat messages (optional)
            
        Returns:
            The assistant's response
        """
        logger.info(f"Chat: Received - {user_message[:50]}...")
        
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
            # Run the agent
            result = self.agent.invoke({"messages": messages})
            
            # Extract the final response
            final_messages = result["messages"]
            
            # Find the last AI message
            for msg in reversed(final_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    logger.info("Chat: Response generated successfully")
                    return msg.content
            
            logger.warning("Chat: No AI message found")
            return "I apologize, but I couldn't generate a response."
            
        except Exception as e:
            logger.error(f"Chat: Agent failed - {e}")
            return "I apologize, but I encountered an error processing your request."


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
