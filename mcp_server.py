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
    
    def get_collaborators(
        self,
        search_query: str,
        search_type: str = "any"
    ) -> Dict[str, Any]:
        """
        Search for collaborators within the user's friend network.
        
        Args:
            search_query: Search term (name, email, or username)
            search_type: Type of search - "name", "email", "username", or "any"
            
        Returns:
            Dict containing list of matching collaborators
        """
        try:
            # Get user's friend network
            user_query = "SELECT collaborator_ids FROM users WHERE id = %s"
            user_result = execute_query(user_query, (self.user_id,), fetch_one=True)
            
            if not user_result or not user_result[0]:
                return {
                    'success': True,
                    'collaborators': [],
                    'message': "You don't have any friends added yet. Add friends first to invite them to meetings."
                }
            
            friend_ids = user_result[0]
            
            # Build search query based on type
            if search_type == "email":
                search_condition = "email ILIKE %s"
            elif search_type == "username":
                search_condition = "username ILIKE %s"
            elif search_type == "name":
                search_condition = "full_name ILIKE %s"
            else:  # "any"
                search_condition = "(full_name ILIKE %s OR email ILIKE %s OR username ILIKE %s)"
            
            # Search within friend network
            if search_type == "any":
                search_param = f"%{search_query}%"
                collab_query = f"""
                SELECT id, username, full_name, email 
                FROM users 
                WHERE id = ANY(%s) AND ({search_condition})
                """
                results = execute_query(
                    collab_query,
                    (friend_ids, search_param, search_param, search_param),
                    fetch_all=True
                )
            else:
                search_param = f"%{search_query}%"
                collab_query = f"""
                SELECT id, username, full_name, email 
                FROM users 
                WHERE id = ANY(%s) AND {search_condition}
                """
                results = execute_query(collab_query, (friend_ids, search_param), fetch_all=True)
            
            if not results:
                return {
                    'success': True,
                    'collaborators': [],
                    'message': f"No friends found matching '{search_query}'. Make sure they're in your friend list first."
                }
            
            collaborators = [
                {
                    'id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'email': row[3]
                }
                for row in results
            ]
            
            return {
                'success': True,
                'collaborators': collaborators,
                'count': len(collaborators),
                'message': f"Found {len(collaborators)} friend(s) matching '{search_query}'"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to search collaborators: {str(e)}"
            }
    
    def add_collaborators_to_event(
        self,
        event_id: int,
        collaborator_ids: Optional[List[int]] = None,
        collaborator_emails: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add collaborators to an existing event and sync to Google Calendar.
        
        Args:
            event_id: ID of the event
            collaborator_ids: List of user IDs to add as collaborators (from friends list)
            collaborator_emails: List of email addresses to invite (can be anyone)
            
        Returns:
            Dict containing success status and message
        """
        try:
            added_collaborators = []
            
            # Process user IDs (friends in the system)
            if collaborator_ids:
                for collab_id in collaborator_ids:
                    # Check if already added
                    check_query = """
                    SELECT collab_id FROM event_collaborators 
                    WHERE event_id = %s AND user_id = %s
                    """
                    existing = execute_query(check_query, (event_id, collab_id), fetch_one=True)
                    
                    if existing:
                        continue  # Skip if already added
                    
                    # Add collaborator
                    insert_query = """
                    INSERT INTO event_collaborators (event_id, user_id)
                    VALUES (%s, %s)
                    RETURNING collab_id
                    """
                    result = execute_query(insert_query, (event_id, collab_id), fetch_one=True)
                    
                    if result:
                        # Get collaborator info
                        user_query = "SELECT email, full_name FROM users WHERE id = %s"
                        user_info = execute_query(user_query, (collab_id,), fetch_one=True)
                        
                        if user_info:
                            added_collaborators.append({
                                'id': collab_id,
                                'email': user_info[0],
                                'name': user_info[1]
                            })
            
            # Process emails (anyone, not necessarily in the system)
            external_emails = []
            if collaborator_emails:
                for email in collaborator_emails:
                    # Check if this email belongs to a user in the system
                    user_query = "SELECT id, full_name FROM users WHERE email = %s"
                    user_info = execute_query(user_query, (email,), fetch_one=True)
                    
                    if user_info:
                        # User exists in system, add to event_collaborators
                        user_id = user_info[0]
                        user_name = user_info[1]
                        
                        # Check if already added
                        check_query = """
                        SELECT collab_id FROM event_collaborators 
                        WHERE event_id = %s AND user_id = %s
                        """
                        existing = execute_query(check_query, (event_id, user_id), fetch_one=True)
                        
                        if not existing:
                            insert_query = """
                            INSERT INTO event_collaborators (event_id, user_id)
                            VALUES (%s, %s)
                            """
                            execute_query(insert_query, (event_id, user_id))
                            
                            added_collaborators.append({
                                'id': user_id,
                                'email': email,
                                'name': user_name
                            })
                    else:
                        # External user (not in system), just add to Google Calendar
                        external_emails.append({
                            'email': email,
                            'name': email.split('@')[0]  # Use email prefix as name
                        })
                        added_collaborators.append({
                            'email': email,
                            'name': email.split('@')[0]
                        })
            
            # Update Google Calendar event with attendees
            event_query = "SELECT google_event_ref FROM calendar_events WHERE event_id = %s"
            event_result = execute_query(event_query, (event_id,), fetch_one=True)
            
            google_synced = False
            if event_result and event_result[0]:
                google_event_id = event_result[0]
                creds = self.get_google_credentials()
                
                if creds:
                    try:
                        service = build('calendar', 'v3', credentials=creds)
                        
                        # Get current event
                        event = service.events().get(
                            calendarId='primary',
                            eventId=google_event_id
                        ).execute()
                        
                        # Add attendees (both internal and external)
                        attendees = event.get('attendees', [])
                        for collab in added_collaborators:
                            attendees.append({'email': collab['email']})
                        
                        event['attendees'] = attendees
                        
                        # Update event
                        service.events().update(
                            calendarId='primary',
                            eventId=google_event_id,
                            body=event,
                            sendUpdates='all'  # Send email invitations
                        ).execute()
                        
                        google_synced = True
                    except Exception as e:
                        print(f"Failed to sync attendees to Google Calendar: {e}")
            
            collab_names = [c.get('name', c['email']) for c in added_collaborators]
            message = f"Added {len(added_collaborators)} collaborator(s): {', '.join(collab_names)}"
            
            if google_synced:
                message += "\n✅ Invitations sent via Google Calendar!"
            
            return {
                'success': True,
                'added_count': len(added_collaborators),
                'collaborators': added_collaborators,
                'google_synced': google_synced,
                'message': message
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to add collaborators: {str(e)}"
            }
    
    def generate_meeting_link(
        self,
        event_id: int,
        existing_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate or attach a Google Meet link to an event.
        
        Args:
            event_id: ID of the event
            existing_code: Optional existing meeting code/link provided by user
            
        Returns:
            Dict containing meeting link and status
        """
        try:
            # If user provided existing link/code
            if existing_code:
                # Normalize the code/link
                if existing_code.startswith('http'):
                    meeting_url = existing_code
                    # Extract code from URL if possible
                    meeting_code = existing_code.split('/')[-1] if '/' in existing_code else existing_code
                else:
                    meeting_code = existing_code
                    meeting_url = f"https://meet.google.com/{existing_code}"
                
                # Store in database
                insert_query = """
                INSERT INTO meeting_links (event_id, platform, meeting_code, meeting_url)
                VALUES (%s, 'custom', %s, %s)
                ON CONFLICT (event_id) DO UPDATE 
                SET meeting_code = EXCLUDED.meeting_code, meeting_url = EXCLUDED.meeting_url
                RETURNING link_id
                """
                execute_query(insert_query, (event_id, meeting_code, meeting_url))
                
                return {
                    'success': True,
                    'meeting_url': meeting_url,
                    'meeting_code': meeting_code,
                    'platform': 'custom',
                    'message': f"Meeting link attached: {meeting_url}"
                }
            
            # Auto-generate Google Meet link via Calendar API
            creds = self.get_google_credentials()
            
            if not creds:
                return {
                    'success': False,
                    'error': "Google Calendar not connected. Please authorize first or provide a meeting link manually."
                }
            
            try:
                service = build('calendar', 'v3', credentials=creds)
                
                # Get the calendar event
                event_query = "SELECT google_event_ref, start_time, end_time, event_desc FROM calendar_events WHERE event_id = %s"
                event_result = execute_query(event_query, (event_id,), fetch_one=True)
                
                if not event_result or not event_result[0]:
                    return {
                        'success': False,
                        'error': "Event not found or not synced to Google Calendar"
                    }
                
                google_event_id = event_result[0]
                
                # Get current event from Google Calendar
                event = service.events().get(
                    calendarId='primary',
                    eventId=google_event_id
                ).execute()
                
                # Add conferenceData to create Google Meet link
                event['conferenceData'] = {
                    'createRequest': {
                        'requestId': f"meet-{event_id}-{datetime.now().timestamp()}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }
                
                # Update event with conference data
                updated_event = service.events().update(
                    calendarId='primary',
                    eventId=google_event_id,
                    body=event,
                    conferenceDataVersion=1
                ).execute()
                
                # Extract meeting link
                conference_data = updated_event.get('conferenceData', {})
                entry_points = conference_data.get('entryPoints', [])
                
                meeting_url = None
                meeting_code = None
                
                for entry in entry_points:
                    if entry.get('entryPointType') == 'video':
                        meeting_url = entry.get('uri')
                        meeting_code = conference_data.get('conferenceId')
                        break
                
                if not meeting_url:
                    return {
                        'success': False,
                        'error': "Failed to generate Google Meet link"
                    }
                
                # Store in database
                insert_query = """
                INSERT INTO meeting_links (event_id, platform, meeting_code, meeting_url)
                VALUES (%s, 'google_meet', %s, %s)
                ON CONFLICT (event_id) DO UPDATE 
                SET meeting_code = EXCLUDED.meeting_code, meeting_url = EXCLUDED.meeting_url
                RETURNING link_id
                """
                execute_query(insert_query, (event_id, meeting_code, meeting_url))
                
                return {
                    'success': True,
                    'meeting_url': meeting_url,
                    'meeting_code': meeting_code,
                    'platform': 'google_meet',
                    'message': f"✅ Google Meet link generated: {meeting_url}"
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': f"Failed to generate Google Meet link: {str(e)}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to generate meeting link: {str(e)}"
            }
    
    def save_todo_only(
        self,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        priority: str = "medium",
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        Save a task to the database without creating a calendar event.
        
        Args:
            title: Task title
            description: Task description
            due_date: Optional due date
            priority: Task priority
            category: Task category
            
        Returns:
            Dict containing task_id and status
        """
        try:
            # Parse due date if provided
            parsed_date = None
            if due_date:
                try:
                    parsed_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                except ValueError:
                    from dateutil import parser
                    parsed_date = parser.parse(due_date)
            
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
                    'error': 'Failed to create task'
                }
            
            due_msg = f" (Due: {parsed_date.strftime('%Y-%m-%d %H:%M')})" if parsed_date else ""
            
            return {
                'success': True,
                'task_id': task_id,
                'message': f"✅ Task '{title}' added to your todo list{due_msg}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to save task: {str(e)}"
            }
    
    def schedule_meeting(
        self,
        title: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: str = "",
        collaborator_ids: Optional[List[int]] = None,
        collaborator_emails: Optional[List[str]] = None,
        meeting_code: Optional[str] = None,
        auto_generate_link: bool = True
    ) -> Dict[str, Any]:
        """
        Schedule a meeting with collaborators and meeting link.
        All-in-one tool for complete meeting creation.
        
        Args:
            title: Meeting title
            start_time: Start time
            end_time: End time (optional)
            description: Meeting description
            collaborator_ids: List of collaborator user IDs (from friends list)
            collaborator_emails: List of email addresses to invite (can be anyone)
            meeting_code: Existing meeting code/link (optional)
            auto_generate_link: Whether to auto-generate Google Meet link
            
        Returns:
            Dict containing event details and status
        """
        try:
            # Parse times
            try:
                parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                from dateutil import parser
                parsed_start = parser.parse(start_time)
            
            if end_time:
                try:
                    parsed_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                except ValueError:
                    from dateutil import parser
                    parsed_end = parser.parse(end_time)
            else:
                parsed_end = parsed_start + timedelta(hours=1)
            
            # Create calendar event with event_type = 'meeting'
            event_query = """
            INSERT INTO calendar_events (
                user_id, start_time, end_time, event_desc, event_type, created_at
            )
            VALUES (%s, %s, %s, %s, 'meeting', NOW())
            RETURNING event_id
            """
            
            event_result = execute_query(
                event_query,
                (self.user_id, parsed_start, parsed_end, description),
                fetch_one=True
            )
            
            event_id = event_result[0] if event_result else None
            
            if not event_id:
                return {
                    'success': False,
                    'error': 'Failed to create meeting event'
                }
            
            # Sync to Google Calendar
            google_event_id = None
            google_sync_message = ""
            creds = self.get_google_credentials()
            
            if creds:
                try:
                    service = build('calendar', 'v3', credentials=creds)
                    
                    event_body = {
                        'summary': f"🤝 {title}",
                        'description': description,
                        'start': {
                            'dateTime': parsed_start.isoformat(),
                            'timeZone': 'Asia/Kolkata',
                        },
                        'end': {
                            'dateTime': parsed_end.isoformat(),
                            'timeZone': 'Asia/Kolkata',
                        },
                    }
                    
                    # Add conference data if auto-generating
                    if auto_generate_link and not meeting_code:
                        event_body['conferenceData'] = {
                            'createRequest': {
                                'requestId': f"meet-{event_id}-{datetime.now().timestamp()}",
                                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                            }
                        }
                    
                    google_event = service.events().insert(
                        calendarId='primary',
                        body=event_body,
                        conferenceDataVersion=1 if auto_generate_link else 0
                    ).execute()
                    
                    google_event_id = google_event.get('id')
                    
                    # Update with Google event reference
                    if google_event_id:
                        update_query = """
                        UPDATE calendar_events 
                        SET google_event_ref = %s, is_calendar_synced = TRUE
                        WHERE event_id = %s
                        """
                        execute_query(update_query, (google_event_id, event_id))
                        google_sync_message = "\n✅ Synced to Google Calendar!"
                    
                    # Extract auto-generated meeting link
                    if auto_generate_link and not meeting_code:
                        conference_data = google_event.get('conferenceData', {})
                        entry_points = conference_data.get('entryPoints', [])
                        
                        for entry in entry_points:
                            if entry.get('entryPointType') == 'video':
                                meeting_url = entry.get('uri')
                                meeting_code_extracted = conference_data.get('conferenceId')
                                
                                # Store meeting link
                                link_query = """
                                INSERT INTO meeting_links (event_id, platform, meeting_code, meeting_url)
                                VALUES (%s, 'google_meet', %s, %s)
                                """
                                execute_query(link_query, (event_id, meeting_code_extracted, meeting_url))
                                google_sync_message += f"\n🔗 Google Meet: {meeting_url}"
                                break
                
                except Exception as e:
                    google_sync_message = f"\n⚠️ Google Calendar sync failed: {str(e)}"
            
            # Add collaborators if provided
            collab_message = ""
            if collaborator_ids or collaborator_emails:
                collab_result = self.add_collaborators_to_event(
                    event_id, 
                    collaborator_ids=collaborator_ids,
                    collaborator_emails=collaborator_emails
                )
                if collab_result['success']:
                    collab_message = f"\n👥 {collab_result['message']}"
            
            # Add custom meeting link if provided
            link_message = ""
            if meeting_code and not auto_generate_link:
                link_result = self.generate_meeting_link(event_id, meeting_code)
                if link_result['success']:
                    link_message = f"\n🔗 {link_result['message']}"
            
            return {
                'success': True,
                'event_id': event_id,
                'google_event_id': google_event_id,
                'message': f"Meeting '{title}' scheduled for {parsed_start.strftime('%Y-%m-%d %H:%M')}{google_sync_message}{collab_message}{link_message}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to schedule meeting: {str(e)}"
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
        },
        {
            'name': 'get_collaborators',
            'description': 'Search for collaborators (friends) by name, email, or username. Only searches within the user\'s friend network.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'search_query': {
                        'type': 'string',
                        'description': 'Name, email, or username to search for'
                    },
                    'search_type': {
                        'type': 'string',
                        'enum': ['any', 'name', 'email', 'username'],
                        'description': 'Type of search to perform (default: any)'
                    }
                },
                'required': ['search_query']
            },
            'function': tools_instance.get_collaborators
        },
        {
            'name': 'add_collaborators_to_event',
            'description': 'Add collaborators to an existing event/meeting. Can invite both friends (by ID) and anyone (by email). Sends Google Calendar invitations if synced.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'event_id': {
                        'type': 'integer',
                        'description': 'ID of the event to add collaborators to'
                    },
                    'collaborator_ids': {
                        'type': 'array',
                        'items': {'type': 'integer'},
                        'description': 'List of user IDs to add as collaborators (from friends list)'
                    },
                    'collaborator_emails': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'List of email addresses to invite (can be anyone, not just friends)'
                    }
                },
                'required': ['event_id']
            },
            'function': tools_instance.add_collaborators_to_event
        },
        {
            'name': 'generate_meeting_link',
            'description': 'Generate a Google Meet link for an event or attach a user-provided meeting link.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'event_id': {
                        'type': 'integer',
                        'description': 'ID of the event to add meeting link to'
                    },
                    'existing_code': {
                        'type': 'string',
                        'description': 'Optional existing meeting code or URL provided by user'
                    }
                },
                'required': ['event_id']
            },
            'function': tools_instance.generate_meeting_link
        },
        {
            'name': 'save_todo_only',
            'description': 'Save a task to the todo list WITHOUT creating a calendar event. Use when user explicitly does not want calendar scheduling.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'title': {
                        'type': 'string',
                        'description': 'Task title'
                    },
                    'description': {
                        'type': 'string',
                        'description': 'Task description'
                    },
                    'due_date': {
                        'type': 'string',
                        'description': 'Optional due date'
                    },
                    'priority': {
                        'type': 'string',
                        'enum': ['low', 'medium', 'high', 'urgent'],
                        'description': 'Task priority'
                    },
                    'category': {
                        'type': 'string',
                        'description': 'Task category'
                    }
                },
                'required': ['title']
            },
            'function': tools_instance.save_todo_only
        },
        {
            'name': 'schedule_meeting',
            'description': 'Schedule a complete meeting with collaborators and Google Meet link. All-in-one tool for meetings. Can invite anyone by email.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'title': {
                        'type': 'string',
                        'description': 'Meeting title'
                    },
                    'start_time': {
                        'type': 'string',
                        'description': 'Start time of the meeting'
                    },
                    'end_time': {
                        'type': 'string',
                        'description': 'End time (optional, defaults to 1 hour)'
                    },
                    'description': {
                        'type': 'string',
                        'description': 'Meeting description/agenda'
                    },
                    'collaborator_ids': {
                        'type': 'array',
                        'items': {'type': 'integer'},
                        'description': 'List of collaborator user IDs to invite (from friends list)'
                    },
                    'collaborator_emails': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'List of email addresses to invite (can be anyone, not just friends)'
                    },
                    'meeting_code': {
                        'type': 'string',
                        'description': 'Existing meeting code/link if user has one'
                    },
                    'auto_generate_link': {
                        'type': 'boolean',
                        'description': 'Whether to auto-generate Google Meet link (default: true)'
                    }
                },
                'required': ['title', 'start_time']
            },
            'function': tools_instance.schedule_meeting
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
    elif tool_name == 'get_collaborators':
        return tools_instance.get_collaborators(**parameters)
    elif tool_name == 'add_collaborators_to_event':
        return tools_instance.add_collaborators_to_event(**parameters)
    elif tool_name == 'generate_meeting_link':
        return tools_instance.generate_meeting_link(**parameters)
    elif tool_name == 'save_todo_only':
        return tools_instance.save_todo_only(**parameters)
    elif tool_name == 'schedule_meeting':
        return tools_instance.schedule_meeting(**parameters)
    else:
        return {
            'success': False,
            'error': f"Unknown tool: {tool_name}"
        }
