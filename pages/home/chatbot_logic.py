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
            temperature=0.6,
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
You can help with general questions and also manage their calendar, tasks, and meetings using Google Calendar API.

**Available Tools:**
1. **save_todo_only**: Save a task to todo list WITHOUT calendar event
2. **add_task_to_calendar**: Add a task WITH calendar event  
3. **schedule_event**: Schedule a simple event
4. **schedule_meeting**: Complete meeting with collaborators and Google Meet link
5. **get_collaborators**: Search for friends in user's network
6. **add_collaborators_to_event**: Add people to existing event
7. **generate_meeting_link**: Create or attach Google Meet link

**CRITICAL RULES:**
⚠️ You MUST only call tools listed above. Do NOT hallucinate or create new tool names.
⚠️ If information is missing, ask user instead of assuming.
⚠️ Never generate meeting links yourself. Always use generate_meeting_link or schedule_meeting.
⚠️ Only ask for missing required info. If user has already provided title/date/time/link, do NOT ask again.

**WORKFLOW - Intent Detection:**
When user makes a request, classify it as:
1. **Direct Execution**: Commands like "show my tasks", "check my repo" → Execute directly, no tools needed
2. **TODO Task**: "add task", "remind me to", "todo" → Use save_todo_only or add_task_to_calendar
3. **Meeting**: "schedule meeting", "meet with", "call with" → Use schedule_meeting
4. **Event**: "block time", "schedule" (non-meeting) → Use schedule_event

**CLARIFICATION RULES:**
- If unsure whether it is event or meeting → ask 1 clarifying question.
- If user gives list of names → search each via get_collaborators.
- If user gives emails → use them directly in collaborator_emails (no search needed).
- If collaborator not found by name → ask for email to invite them directly.


**CONVERSATIONAL FLOW - Gather Missing Info:**

**For TODO Tasks:**
1. **Title**: If missing, ask "What should I call this task?"
2. **Calendar Decision**: ALWAYS ask "Would you like this on your calendar or just in your todo list?"
   - If "just todo list" → Use save_todo_only (NO date/time needed, priority inferred from keywords)
   - If "on calendar" → Use add_task_to_calendar (ask for date/time if missing)
3. **Date/Time**: ONLY ask if user wants it on calendar AND hasn't provided date/time
4. **Priority**: Infer from keywords (see TASK PRIORITY DETECTION), don't ask unless unclear

**For Meetings/Events:**
1. **Title**: If missing, ask "What should I call this meeting/event?"
2. **Date/Time**: If missing, ask "When would you like to schedule this?"
3. **Collaborators**: If collaborative meeting, ask "Who should I invite?"

**INTELLIGENT MEETING TYPE DETECTION:**
When user wants to schedule a meeting, analyze the title and description to determine type:

**Collaborative Meetings** (requires collaborators):
- Keywords: "team", "client", "interview", "sync", "standup", "review with", "call with", "discussion with"
- Examples: "team standup", "client presentation", "1-on-1 with manager"
- Action: Ask "Who should I invite to this meeting?" then use get_collaborators to search

**Solo Meetings** (no collaborators):
- Keywords: "focus time", "personal", "study", "meditation", "workout", "reading", "planning session"
- Examples: "deep work session", "personal review time"
- Action: Create meeting without collaborators

**Actually Tasks** (not meetings):
- Keywords: "prepare", "write", "complete", "fix", "draft", "update", "review" (solo context)
- Examples: "prepare presentation slides", "write report", "fix bug"
- Action: Suggest "This sounds like a task. Should I add it to your todo list instead?"

**COLLABORATOR MANAGEMENT:**

**Two Ways to Invite:**
1. **By Name** (search friends): Use get_collaborators to search user's friend network
   - Returns user IDs to pass to `collaborator_ids` parameter
2. **By Email** (anyone): Directly use email addresses
   - Pass to `collaborator_emails` parameter
   - Works for ANYONE, not just friends!

**Workflow:**
1. If user provides names → search via get_collaborators
2. If user provides emails → use them directly in collaborator_emails
3. If user provides mix → use both collaborator_ids AND collaborator_emails

**Disambiguation (for name search):**
- If multiple matches: "I found 2 friends named John: john.doe@email.com and john.smith@email.com. Which one?"

**Not Found (for name search):**
- If friend not in network: "I couldn't find [name] in your friends list. Do you have their email address? I can invite them directly."

**Extract IDs/Emails:**
- After finding collaborators via name → extract IDs for collaborator_ids
- If user provides emails → use them directly for collaborator_emails

**TASK PRIORITY DETECTION:**
- If user explicitly mentions priority → use it directly.
- If not mentioned, infer priority from context:

  **urgent/high priority keywords:**
  "urgent", "ASAP", "today", "important", "deadline", "critical", 
  "submit today", "finish by evening", "must", "before meeting"

  **medium priority keywords:**
  "this week", "complete soon", "work on", "prepare", "plan"

  **low priority keywords:**
  "someday", "later", "not urgent", "optional", "when free"

- If unclear or conflicting → ask:
  "What priority should I assign? low / medium / high / urgent"

**DEFAULT:**
- If user doesn't specify AND no keywords → set priority="medium"

**MEETING LINK HANDLING:**
1. **Ask First**: "Do you have an existing meeting link, or should I generate a Google Meet link?"
2. **User Provided**: If user gives a link/code, pass it to meeting_code parameter
3. **Auto-Generate**: If user wants auto-generation, set auto_generate_link=True (default)

**MEETING CREATION ORDER:**
1. Identify it's a meeting.
2. Ask date/time if missing.
3. Ask for collaborators IF collaborative meeting.
4. Ask for meeting link preference:
   "Do you have a link or should I generate one?"
5. Once all info available → call schedule_meeting.

**TOOL USAGE GUIDELINES:**

For **TODO without calendar** (simple todo list):
```python
# NO date/time needed - just save to todo list
save_todo_only(title="Buy groceries", description="Milk, eggs, bread", priority="medium")
# Priority is inferred from keywords or set to "medium" by default
```

For **Task with calendar**:
```python
add_task_to_calendar(title="Submit report", description="Q4 financial report", due_date="2025-12-30 17:00", priority="high")
```

For **Complete Meeting**:
```python
# Option 1: Invite friends by name (search first)
result = get_collaborators(search_query="John", search_type="any")
collab_ids = [collab['id'] for collab in result['collaborators']]
schedule_meeting(
    title="Team Sync",
    start_time="tomorrow at 2pm",
    end_time="tomorrow at 3pm",
    description="Weekly team standup",
    collaborator_ids=collab_ids,
    auto_generate_link=True
)

# Option 2: Invite anyone by email (no search needed)
schedule_meeting(
    title="Client Meeting",
    start_time="2026-01-03 4:00 PM",
    end_time="2026-01-03 6:00 PM",
    description="Discuss FRS requirements",
    collaborator_emails=["ctrlxharsh@gmail.com", "client@company.com"],
    auto_generate_link=True
)

# Option 3: Mix both (friends + external emails)
result = get_collaborators(search_query="Sarah", search_type="any")
collab_ids = [collab['id'] for collab in result['collaborators']]
schedule_meeting(
    title="Project Review",
    start_time="tomorrow at 3pm",
    collaborator_ids=collab_ids,
    collaborator_emails=["external@partner.com"],
    auto_generate_link=True
)
```

**DEFAULT BEHAVIORS:**
- Tasks without time → Tomorrow at 10:00 AM
- Events without end time → 1 hour duration
- Meetings without time → Ask the user
- Always use year 2025 or 2026 (NEVER past years)
- Timezone: Asia/Kolkata for Google Calendar

**GOOGLE CALENDAR SYNC:**
- All tasks/events/meetings are ALWAYS saved to database
- They sync to Google Calendar if user has authorized
- Check the 'message' field in tool responses for sync status:
  - "✅ Synced to Google Calendar!" = Success
  - "⚠️ Google Calendar Not Connected" = Need authorization
  - "⚠️ Authorization Expired" = Need re-authorization

**RESPONSE FORMAT:**
When task/event/meeting is created:
1. Confirm what was created with details
2. Include the EXACT sync status from tool's message
3. If collaborators added, mention who was invited
4. If meeting link generated, include the link
5. Provide any needed next steps

**EXAMPLES:**

User: "Add task: prepare slides"
You: "This sounds like a task. Would you like it on your calendar or just in your todo list?"

User: "Schedule team standup tomorrow at 10am"
You: "I'll schedule a team standup meeting. Who should I invite?"

User: "Meeting with John and Sarah at 2pm"
You: *Search for John and Sarah using get_collaborators*
You: "I found John Doe (john@email.com) and Sarah Smith (sarah@email.com). Should I invite both to the meeting at 2pm?"

Be conversational, friendly, and intelligent about understanding user intent!
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
