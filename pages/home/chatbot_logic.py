"""
Chatbot Logic with LangGraph Agent

This module implements the chatbot logic using LangGraph for agent orchestration
and OpenAI for language model capabilities. The agent can call MCP tools to
manage calendar tasks and events.
"""

from typing import Any, Dict, List, Optional, TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import StructuredTool
from utils.env_config import get_openai_api_key
import mcp_server
import json


class ChatState(TypedDict):
    """State definition for the chat graph."""
    messages: List[Any]
    user_id: int
    username: str


class ChatbotAgent:
    """LangGraph-powered chatbot agent with calendar tool integration."""
    
    def __init__(self, user_id: int, username: str):
        """
        Initialize the chatbot agent.
        
        Args:
            user_id: ID of the user chatting
            username: Username for personalization
        """
        self.user_id = user_id
        self.username = username
        
        # Initialize OpenAI client
        api_key = get_openai_api_key()
        self.llm = ChatOpenAI(
            model="gpt-5-mini", 
            temperature=0.7,
            api_key=api_key
        )
        
        # Create tools from MCP server
        self.tools = self._create_langchain_tools()
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _create_langchain_tools(self) -> List:
        """
        Create LangChain tools from MCP server tools.
        
        Returns:
            List of LangChain tool objects
        """
        mcp_tools = mcp_server.get_tools(self.user_id)
        langchain_tools = []
        
        for mcp_tool in mcp_tools:
            # Create a LangChain tool using StructuredTool
            tool_func = mcp_tool['function']
            tool_name = mcp_tool['name']
            tool_desc = mcp_tool['description']
            
            # Create structured tool
            structured_tool = StructuredTool.from_function(
                func=tool_func,
                name=tool_name,
                description=tool_desc
            )
            
            langchain_tools.append(structured_tool)
        
        return langchain_tools
    
    def _should_continue(self, state: ChatState) -> str:
        """
        Determine if we should continue to tools or end.
        
        Args:
            state: Current chat state
            
        Returns:
            "tools" if tool calls are needed, "end" otherwise
        """
        messages = state["messages"]
        last_message = messages[-1]
        
        # If there are tool calls, continue to tools
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        
        # Otherwise end
        return "end"
    
    def _call_model(self, state: ChatState) -> Dict:
        """
        Call the LLM with current state.
        
        Args:
            state: Current chat state
            
        Returns:
            Updated state with new message
        """
        messages = state["messages"]
        
        # Add system message if this is the first call
        if len(messages) == 1 or not any(isinstance(m, SystemMessage) for m in messages):
            system_message = SystemMessage(content=f"""You are a helpful AI assistant for {self.username}. 
You can help with general questions and also manage their calendar using Google Calendar API.

**Calendar Management:**
- Add a task, todo, or reminder → use the add_task_to_calendar tool
- Schedule a meeting, event, or appointment → use the schedule_event tool

**IMPORTANT - Ask for Missing Information:**
Before calling a tool, check if you have all required information:
- For tasks: MUST have title. If no date/time mentioned, ask the user or use "tomorrow at 10:00 AM" as default
- For events: MUST have title and start_time. If no time mentioned, ask the user
- If user says "add task X" without date → Ask: "When would you like this task due? (e.g., tomorrow at 3pm, next Monday)"
- If user says "schedule meeting Y" without time → Ask: "What time should I schedule this? (e.g., tomorrow at 2pm)"

**Default Time Handling:**
- If user doesn't specify time for a task → Use 10:00 AM the next day
- If user doesn't specify time for an event → Ask them
- Always use the current year (2025) - NEVER use past years like 2023 or future years like 2026
- Parse natural language: "tomorrow", "next Monday", "in 2 days", etc.

**CRITICAL - Google Calendar Sync:**
- Tasks and events are ALWAYS saved to the database
- They will also sync to Google Calendar if authorized
- When you receive a tool response, ALWAYS check the 'message' field and include it in your response
- If the message contains "✅ **Synced to Google Calendar!**" - tell the user it was synced
- If the message contains "⚠️ **Google Calendar Not Connected**" - tell the user to authorize in Calendar tab
- If the message contains "⚠️ **Google Calendar Sync Failed**" - tell the user about the error

**Response Format:**
When a task/event is created, your response MUST include:
1. Confirmation of what was created
2. The EXACT sync status from the tool's message field
3. Any instructions if authorization is needed

Be conversational and friendly. Parse dates and times naturally.
""")
            messages = [system_message] + messages
        
        response = self.llm_with_tools.invoke(messages)
        
        return {"messages": messages + [response]}
    
    def _execute_tools(self, state: ChatState) -> Dict:
        """
        Execute tool calls from the last message.
        
        Args:
            state: Current chat state
            
        Returns:
            Updated state with tool results
        """
        messages = state["messages"]
        last_message = messages[-1]
        
        tool_messages = []
        
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                
                # Execute the tool via MCP server
                result = mcp_server.execute_tool(
                    self.user_id,
                    tool_name,
                    tool_args
                )
                
                # Create tool message with result
                tool_message = ToolMessage(
                    content=json.dumps(result),
                    tool_call_id=tool_call['id']
                )
                tool_messages.append(tool_message)
        
        return {"messages": messages + tool_messages}
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph state graph.
        
        Returns:
            Compiled state graph
        """
        # Create the graph
        workflow = StateGraph(ChatState)
        
        # Add nodes
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", self._execute_tools)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "tools": "tools",
                "end": END
            }
        )
        
        # After tools, go back to agent
        workflow.add_edge("tools", "agent")
        
        # Compile the graph
        return workflow.compile()
    
    def chat(self, user_message: str, chat_history: Optional[List[Dict]] = None) -> str:
        """
        Process a user message and return the response.
        
        Args:
            user_message: The user's message
            chat_history: Previous chat messages (optional)
            
        Returns:
            The assistant's response
        """
        # Convert chat history to LangChain messages
        messages = []
        
        if chat_history:
            for msg in chat_history:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(AIMessage(content=msg['content']))
        
        # Add current user message
        messages.append(HumanMessage(content=user_message))
        
        # Create initial state
        initial_state = {
            "messages": messages,
            "user_id": self.user_id,
            "username": self.username
        }
        
        # Run the graph
        result = self.graph.invoke(initial_state)
        
        # Extract the final response
        final_messages = result["messages"]
        last_message = final_messages[-1]
        
        if isinstance(last_message, AIMessage):
            return last_message.content
        
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
