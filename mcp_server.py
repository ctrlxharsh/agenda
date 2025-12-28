"""
MCP Server for Calendar Management Tools

This module provides an MCP (Model Context Protocol) server that exposes
calendar management tools for the LangGraph agent to use.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from utils.db import execute_query
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json


class MCPCalendarTools:
    """MCP server providing calendar management tools."""
    
    def __init__(self, user_id: int):
        """
        Initialize MCP Calendar Tools for a specific user.
        
        Args:
            user_id: The ID of the user making the request
        """
        self.user_id = user_id
    
    def get_google_credentials(self) -> Optional[Credentials]:
        """
        Retrieve Google Calendar credentials for the user.
        
        Returns:
            Google OAuth credentials if available, None otherwise
        """
        query = """
        SELECT access_token, refresh_token, token_expiry, token_uri, 
               client_id, client_secret, scopes 
        FROM user_google_accounts 
        WHERE user_id = %s
        """
        result = execute_query(query, (self.user_id,), fetch_one=True)
        
        if not result:
            return None
        
        creds_dict = {
            'token': result[0],
            'refresh_token': result[1],
            'token_uri': result[3],
            'client_id': result[4],
            'client_secret': result[5],
            'scopes': result[6]
        }
        
        return Credentials(**creds_dict)
    
    def add_task_to_calendar(
        self,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        priority: str = "medium",
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        Add a task to the calendar and database.
        
        Args:
            title: Task title
            description: Task description
            due_date: Due date in ISO format (YYYY-MM-DD HH:MM:SS) or natural language
            priority: Task priority (low, medium, high, urgent)
            category: Task category
            
        Returns:
            Dict containing task_id, event_id, and status message
        """
        try:
            # Parse due date
            if due_date:
                try:
                    # Try parsing ISO format first
                    parsed_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                except ValueError:
                    # If that fails, try common formats
                    from dateutil import parser
                    parsed_date = parser.parse(due_date)
            else:
                # Default to tomorrow at 10 AM
                parsed_date = datetime.now() + timedelta(days=1)
                parsed_date = parsed_date.replace(hour=10, minute=0, second=0, microsecond=0)
            
            # Insert task into database
            task_query = """
            INSERT INTO tasks (
                user_id, title, description, status, priority, 
                category, due_date, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING task_id
            """
            
            task_result = execute_query(
                task_query,
                (self.user_id, title, description, 'todo', priority, category, parsed_date),
                fetch_one=True
            )
            
            task_id = task_result[0] if task_result else None
            
            if not task_id:
                return {
                    'success': False,
                    'error': 'Failed to create task in database'
                }
            
            # Create calendar event
            event_start = parsed_date
            event_end = parsed_date + timedelta(hours=1)
            
            # Insert into calendar_events table
            event_query = """
            INSERT INTO calendar_events (
                task_id, user_id, start_time, end_time, event_desc, created_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING event_id
            """
            
            event_result = execute_query(
                event_query,
                (task_id, self.user_id, event_start, event_end, description),
                fetch_one=True
            )
            
            event_id = event_result[0] if event_result else None
            
            # Try to sync with Google Calendar
            google_event_id = None
            google_sync_message = ""
            creds = self.get_google_credentials()
            
            if not creds:
                # User hasn't authorized Google Calendar
                google_sync_message = "\n\n⚠️ **Google Calendar Not Connected**: To sync this task to your Google Calendar, please go to the Calendar tab and authorize your Google account first."
            else:
                try:
                    service = build('calendar', 'v3', credentials=creds)
                    
                    event_body = {
                        'summary': f"📋 {title}",
                        'description': f"{description}\n\nPriority: {priority.upper()}\nCategory: {category}",
                        'start': {
                            'dateTime': event_start.isoformat(),
                            'timeZone': 'Asia/Kolkata',
                        },
                        'end': {
                            'dateTime': event_end.isoformat(),
                            'timeZone': 'Asia/Kolkata',
                        },
                        'colorId': '9' if priority == 'high' or priority == 'urgent' else '1',
                    }
                    
                    google_event = service.events().insert(
                        calendarId='primary',
                        body=event_body
                    ).execute()
                    
                    google_event_id = google_event.get('id')
                    
                    # Update calendar_events with Google event reference
                    if google_event_id and event_id:
                        update_query = """
                        UPDATE calendar_events 
                        SET google_event_ref = %s 
                        WHERE event_id = %s
                        """
                        execute_query(update_query, (google_event_id, event_id))
                        google_sync_message = "\n✅ **Synced to Google Calendar!**"
                
                except Exception as e:
                    # Google Calendar sync failed, but task is still created
                    error_msg = str(e)
                    if "invalid_grant" in error_msg or "Token has been expired" in error_msg:
                        google_sync_message = "\n\n⚠️ **Google Calendar Authorization Expired**: Please go to the Calendar tab and re-authorize your Google account to sync events."
                    else:
                        google_sync_message = f"\n\n⚠️ **Google Calendar Sync Failed**: {error_msg}. Task saved to database only."
                    print(f"Google Calendar sync failed: {e}")
            
            success_message = f"Task '{title}' added successfully! Due: {parsed_date.strftime('%Y-%m-%d %H:%M')}{google_sync_message}"
            
            return {
                'success': True,
                'task_id': task_id,
                'event_id': event_id,
                'google_event_id': google_event_id,
                'google_synced': google_event_id is not None,
                'message': success_message
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to add task: {str(e)}"
            }
    
    def schedule_event(
        self,
        title: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: str = "",
        meeting_link: str = ""
    ) -> Dict[str, Any]:
        """
        Schedule an event on the calendar.
        
        Args:
            title: Event title
            start_time: Start time in ISO format or natural language
            end_time: End time in ISO format or natural language (defaults to 1 hour after start)
            description: Event description
            meeting_link: Optional meeting link
            
        Returns:
            Dict containing event_id and status message
        """
        try:
            # Parse start time
            try:
                parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                from dateutil import parser
                parsed_start = parser.parse(start_time)
            
            # Parse end time
            if end_time:
                try:
                    parsed_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                except ValueError:
                    from dateutil import parser
                    parsed_end = parser.parse(end_time)
            else:
                # Default to 1 hour duration
                parsed_end = parsed_start + timedelta(hours=1)
            
            # Insert into calendar_events table
            event_query = """
            INSERT INTO calendar_events (
                user_id, start_time, end_time, event_desc, meeting_link, created_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING event_id
            """
            
            event_result = execute_query(
                event_query,
                (self.user_id, parsed_start, parsed_end, description, meeting_link),
                fetch_one=True
            )
            
            event_id = event_result[0] if event_result else None
            
            if not event_id:
                return {
                    'success': False,
                    'error': 'Failed to create event in database'
                }
            
            # Try to sync with Google Calendar
            google_event_id = None
            creds = self.get_google_credentials()
            
            if creds:
                try:
                    service = build('calendar', 'v3', credentials=creds)
                    
                    event_body = {
                        'summary': title,
                        'description': description,
                        'start': {
                            'dateTime': parsed_start.isoformat(),
                            'timeZone': 'UTC',
                        },
                        'end': {
                            'dateTime': parsed_end.isoformat(),
                            'timeZone': 'UTC',
                        },
                    }
                    
                    if meeting_link:
                        event_body['location'] = meeting_link
                    
                    google_event = service.events().insert(
                        calendarId='primary',
                        body=event_body
                    ).execute()
                    
                    google_event_id = google_event.get('id')
                    
                    # Update calendar_events with Google event reference
                    if google_event_id:
                        update_query = """
                        UPDATE calendar_events 
                        SET google_event_ref = %s 
                        WHERE event_id = %s
                        """
                        execute_query(update_query, (google_event_id, event_id))
                
                except Exception as e:
                    print(f"Google Calendar sync failed: {e}")
            
            return {
                'success': True,
                'event_id': event_id,
                'google_event_id': google_event_id,
                'message': f"Event '{title}' scheduled successfully! {parsed_start.strftime('%Y-%m-%d %H:%M')} - {parsed_end.strftime('%H:%M')}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to schedule event: {str(e)}"
            }


def get_tools(user_id: int) -> List[Dict[str, Any]]:
    """
    Get available MCP tools for the given user.
    
    Args:
        user_id: User ID to create tools for
        
    Returns:
        List of tool definitions in MCP format
    """
    tools_instance = MCPCalendarTools(user_id)
    
    return [
        {
            'name': 'add_task_to_calendar',
            'description': 'Add a task to the user\'s calendar and database. Use this when the user wants to create a new task or todo item.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'title': {
                        'type': 'string',
                        'description': 'The title or name of the task'
                    },
                    'description': {
                        'type': 'string',
                        'description': 'Detailed description of the task'
                    },
                    'due_date': {
                        'type': 'string',
                        'description': 'Due date and time for the task (e.g., "2024-12-30 17:00" or "tomorrow at 5pm")'
                    },
                    'priority': {
                        'type': 'string',
                        'enum': ['low', 'medium', 'high', 'urgent'],
                        'description': 'Priority level of the task'
                    },
                    'category': {
                        'type': 'string',
                        'description': 'Category or tag for the task (e.g., "work", "personal", "study")'
                    }
                },
                'required': ['title']
            },
            'function': tools_instance.add_task_to_calendar
        },
        {
            'name': 'schedule_event',
            'description': 'Schedule an event or meeting on the user\'s calendar. Use this for meetings, appointments, or time-blocked events.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'title': {
                        'type': 'string',
                        'description': 'The title of the event or meeting'
                    },
                    'start_time': {
                        'type': 'string',
                        'description': 'Start time of the event (e.g., "2024-12-30 14:00" or "tomorrow at 2pm")'
                    },
                    'end_time': {
                        'type': 'string',
                        'description': 'End time of the event (optional, defaults to 1 hour after start)'
                    },
                    'description': {
                        'type': 'string',
                        'description': 'Description or agenda for the event'
                    },
                    'meeting_link': {
                        'type': 'string',
                        'description': 'Meeting link (e.g., Zoom, Google Meet URL)'
                    }
                },
                'required': ['title', 'start_time']
            },
            'function': tools_instance.schedule_event
        }
    ]


def execute_tool(user_id: int, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an MCP tool by name.
    
    Args:
        user_id: User ID executing the tool
        tool_name: Name of the tool to execute
        parameters: Parameters to pass to the tool
        
    Returns:
        Tool execution result
    """
    tools_instance = MCPCalendarTools(user_id)
    
    if tool_name == 'add_task_to_calendar':
        return tools_instance.add_task_to_calendar(**parameters)
    elif tool_name == 'schedule_event':
        return tools_instance.schedule_event(**parameters)
    else:
        return {
            'success': False,
            'error': f"Unknown tool: {tool_name}"
        }
