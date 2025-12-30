"""
MCP Calendar Tools

This module provides MCP (Model Context Protocol) tools for calendar management.
Includes Google Calendar integration, task management, meeting scheduling, and collaborator handling.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from utils.db import execute_query, execute_query_async
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import asyncio


class MCPCalendarTools:
    """MCP server providing calendar management tools."""
    
    def __init__(self, user_id: int):
        """
        Initialize MCP Calendar Tools for a specific user.
        
        Args:
            user_id: The ID of the user making the request
        """
        self.user_id = user_id
    
    async def get_google_credentials(self) -> Optional[Credentials]:
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
        result = await execute_query_async(query, (self.user_id,), fetch_one=True)
        
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
    
    async def add_task_to_calendar(
        self,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        scheduled_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        priority: str = "medium",
        category: str = "general",
        meeting_link: str = ""
    ) -> Dict[str, Any]:
        """
        Add a task or event to the calendar and database.
        
        Args:
            title: Task/Event title
            description: Description
            due_date: Deadline/completion DATE (YYYY-MM-DD)
            scheduled_date: When task is scheduled DATE (YYYY-MM-DD)
            start_time: Start TIME (HH:MM)
            end_time: End TIME (HH:MM)
            priority: Priority (low, medium, high, urgent)
            category: Category
            meeting_link: Optional meeting link
            
        Returns:
            Dict containing task_id, event_id, and status message
        """
        try:
            # Parse due date (DATE only)
            parsed_due_date = None
            if due_date:
                try:
                    dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    parsed_due_date = dt.date()
                except ValueError:
                    from dateutil import parser
                    dt = parser.parse(due_date)
                    parsed_due_date = dt.date()
            else:
                # Default to tomorrow
                parsed_due_date = (datetime.now() + timedelta(days=1)).date()
            
            # Parse scheduled date (DATE only)
            parsed_scheduled_date = None
            if scheduled_date:
                try:
                    dt = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00'))
                    parsed_scheduled_date = dt.date()
                except ValueError:
                    from dateutil import parser
                    dt = parser.parse(scheduled_date)
                    parsed_scheduled_date = dt.date()
            else:
                # Default scheduled date to same as due date
                parsed_scheduled_date = parsed_due_date
            
            # Parse start time (TIME only)
            parsed_start_time = None
            if start_time:
                try:
                    dt = datetime.strptime(start_time, '%H:%M')
                    parsed_start_time = dt.time()
                except ValueError:
                    # Try with seconds
                    dt = datetime.strptime(start_time, '%H:%M:%S')
                    parsed_start_time = dt.time()
            
            # Parse end time (TIME only)
            parsed_end_time = None
            if end_time:
                try:
                    dt = datetime.strptime(end_time, '%H:%M')
                    parsed_end_time = dt.time()
                except ValueError:
                    dt = datetime.strptime(end_time, '%H:%M:%S')
                    parsed_end_time = dt.time()
            
            # Insert task into database
            task_query = """
            INSERT INTO tasks (
                user_id, title, description, status, priority, 
                category, due_date, scheduled_date, start_time, end_time, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING task_id
            """
            
            task_result = await execute_query_async(
                task_query,
                (self.user_id, title, description, 'task', priority, category, parsed_due_date, parsed_scheduled_date, parsed_start_time, parsed_end_time),
                fetch_one=True
            )
            
            task_id = task_result[0] if task_result else None
            
            if not task_id:
                return {
                    'success': False,
                    'error': 'Failed to create task in database'
                }
            
            # Parse end time if provided
            parsed_end = None
            if end_time:
                try:
                    parsed_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                except ValueError:
                    from dateutil import parser
                    parsed_end = parser.parse(end_time)
            
            # Create calendar event
            # Combine date and time for Google Calendar and internal logic
            if parsed_start_time:
                event_start = datetime.combine(parsed_scheduled_date, parsed_start_time)
            else:
                # Default to 9 AM if no time specified ? or midnight
                event_start = datetime.combine(parsed_scheduled_date, datetime.min.time())

            if parsed_end_time:
                event_end = datetime.combine(parsed_scheduled_date, parsed_end_time)
            elif parsed_end:
                 event_end = parsed_end # from line 165
            else:
                 event_end = event_start + timedelta(hours=1)
            
            # Insert into calendar_events table
            event_query = """
            INSERT INTO calendar_events (
                task_id, user_id, start_time, end_time, due_date, scheduled_date, event_desc, event_type, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'task', NOW())
            RETURNING event_id
            """
            
            event_result = await execute_query_async(
                event_query,
                (task_id, self.user_id, parsed_start_time, parsed_end_time, parsed_due_date, parsed_scheduled_date, description),
                fetch_one=True
            )
            
            event_id = event_result[0] if event_result else None
            
            # If meeting_link provided, store it
            if meeting_link and event_id:
                link_query = """
                INSERT INTO meeting_links (event_id, platform, meeting_url, meeting_code)
                VALUES (%s, 'custom', %s, %s)
                """
                # Use link as code if no slash, else extract last part
                code = meeting_link.split('/')[-1] if '/' in meeting_link else meeting_link
                await execute_query_async(link_query, (event_id, meeting_link, code))
            
            # Try to sync with Google Calendar
            google_event_id = None
            google_sync_message = ""
            creds = await self.get_google_credentials()
            
            if not creds:
                # User hasn't authorized Google Calendar
                google_sync_message = "\n\n⚠️ **Google Calendar Not Connected**: To sync this task to your Google Calendar, please go to the Calendar tab and authorize your Google account first."
            else:
                try:
                    def _sync_google():
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
                        
                        if meeting_link:
                            event_body['location'] = meeting_link
                        
                        return service.events().insert(
                            calendarId='primary',
                            body=event_body
                        ).execute()

                    google_event = await asyncio.to_thread(_sync_google)
                    
                    google_event_id = google_event.get('id')
                    
                    # Update calendar_events with Google event reference
                    if google_event_id and event_id:
                        update_query = """
                        UPDATE calendar_events 
                        SET google_event_ref = %s 
                        WHERE event_id = %s
                        """
                        await execute_query_async(update_query, (google_event_id, event_id))
                        google_sync_message = "\n✅ **Synced to Google Calendar!**"
                
                except Exception as e:
                    # Google Calendar sync failed, but task is still created
                    error_msg = str(e)
                    if "invalid_grant" in error_msg or "Token has been expired" in error_msg:
                        google_sync_message = "\n\n⚠️ **Google Calendar Authorization Expired**: Please go to the Calendar tab and re-authorize your Google account to sync events."
                    else:
                        google_sync_message = f"\n\n⚠️ **Google Calendar Sync Failed**: {error_msg}. Task saved to database only."
                    print(f"Google Calendar sync failed: {e}")
            
            success_message = f"Task '{title}' added successfully! Due: {parsed_due_date.strftime('%Y-%m-%d')} {parsed_start_time.strftime('%H:%M') if parsed_start_time else ''}{google_sync_message}"
            
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
    
    async def get_collaborators(
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
            user_result = await execute_query_async(user_query, (self.user_id,), fetch_one=True)
            
            if not user_result or not user_result[0]:
                return {
                    'success': True,
                    'collaborators': [],
                    'message': "You don't have any friends added yet. Add friends first to invite them to meetings."
                }
            
            friend_ids = user_result[0]
            
            # Ensure search_type has a valid value
            if not search_type or search_type not in ['any', 'name', 'email', 'username']:
                search_type = 'any'
            
            # Build search query and parameters based on type
            search_param = f"%{search_query}%"
            
            if search_type == "any":
                # Search across all fields
                collab_query = """
                SELECT id, username, full_name, email 
                FROM users 
                WHERE id = ANY(%s) AND (full_name ILIKE %s OR email ILIKE %s OR username ILIKE %s)
                """
                query_params = (friend_ids, search_param, search_param, search_param)
            elif search_type == "email":
                collab_query = """
                SELECT id, username, full_name, email 
                FROM users 
                WHERE id = ANY(%s) AND email ILIKE %s
                """
                query_params = (friend_ids, search_param)
            elif search_type == "username":
                collab_query = """
                SELECT id, username, full_name, email 
                FROM users 
                WHERE id = ANY(%s) AND username ILIKE %s
                """
                query_params = (friend_ids, search_param)
            else:  # search_type == "name"
                collab_query = """
                SELECT id, username, full_name, email 
                FROM users 
                WHERE id = ANY(%s) AND full_name ILIKE %s
                """
                query_params = (friend_ids, search_param)
            
            results = await execute_query_async(collab_query, query_params, fetch_all=True)
            
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
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR in get_collaborators: {error_details}")  # Log to console
            return {
                'success': False,
                'error': f"Failed to search collaborators: {str(e)}",
                'error_details': error_details  # Include full traceback for debugging
            }
    
    async def add_collaborators_to_event(
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
                    existing = await execute_query_async(check_query, (event_id, collab_id), fetch_one=True)
                    
                    if existing:
                        continue  # Skip if already added
                    
                    # Add collaborator
                    insert_query = """
                    INSERT INTO event_collaborators (event_id, user_id)
                    VALUES (%s, %s)
                    RETURNING collab_id
                    """
                    result = await execute_query_async(insert_query, (event_id, collab_id), fetch_one=True)
                    
                    if result:
                        # Get collaborator info
                        user_query = "SELECT email, full_name FROM users WHERE id = %s"
                        user_info = await execute_query_async(user_query, (collab_id,), fetch_one=True)
                        
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
                    user_info = await execute_query_async(user_query, (email,), fetch_one=True)
                    
                    if user_info:
                        # User exists in system, add to event_collaborators
                        user_id = user_info[0]
                        user_name = user_info[1]
                        
                        # Check if already added
                        check_query = """
                        SELECT collab_id FROM event_collaborators 
                        WHERE event_id = %s AND user_id = %s
                        """
                        existing = await execute_query_async(check_query, (event_id, user_id), fetch_one=True)
                        
                        if not existing:
                            insert_query = """
                            INSERT INTO event_collaborators (event_id, user_id)
                            VALUES (%s, %s)
                            """
                            await execute_query_async(insert_query, (event_id, user_id))
                            
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
            event_result = await execute_query_async(event_query, (event_id,), fetch_one=True)
            
            google_synced = False
            if event_result and event_result[0]:
                google_event_id = event_result[0]
                creds = await self.get_google_credentials()
                
                if creds:
                    try:
                        def _sync_attendees():
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

                        await asyncio.to_thread(_sync_attendees)
                        
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
    
    async def generate_meeting_link(
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
                await execute_query_async(insert_query, (event_id, meeting_code, meeting_url))
                
                return {
                    'success': True,
                    'meeting_url': meeting_url,
                    'meeting_code': meeting_code,
                    'platform': 'custom',
                    'message': f"Meeting link attached: {meeting_url}"
                }
            
            # Auto-generate Google Meet link via Calendar API
            creds = await self.get_google_credentials()
            
            if not creds:
                return {
                    'success': False,
                    'error': "Google Calendar not connected. Please authorize first or provide a meeting link manually."
                }
            
            try:
                # Get the calendar event
                event_query = "SELECT google_event_ref, start_time, end_time, event_desc FROM calendar_events WHERE event_id = %s"
                event_result = await execute_query_async(event_query, (event_id,), fetch_one=True)
                
                if not event_result or not event_result[0]:
                    return {
                        'success': False,
                        'error': "Event not found or not synced to Google Calendar"
                    }
                
                google_event_id = event_result[0]
                
                def _generate_meet_link():
                    service = build('calendar', 'v3', credentials=creds)
                    
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
                    return service.events().update(
                        calendarId='primary',
                        eventId=google_event_id,
                        body=event,
                        conferenceDataVersion=1
                    ).execute()

                updated_event = await asyncio.to_thread(_generate_meet_link)
                
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
                await execute_query_async(insert_query, (event_id, meeting_code, meeting_url))
                
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
    
    async def save_todo_only(
        self,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        scheduled_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        priority: str = "medium",
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        Save a task to the database without creating a calendar event.
        
        Args:
            title: Task title
            description: Task description
            due_date: Deadline/completion DATE (YYYY-MM-DD)
            scheduled_date: When task is scheduled DATE (YYYY-MM-DD)
            start_time: Start TIME (HH:MM)
            end_time: End TIME (HH:MM)
            priority: Task priority
            category: Task category
            
        Returns:
            Dict containing task_id and status
        """
        try:
            # Parse due date (DATE only)
            parsed_due_date = None
            if due_date:
                try:
                    dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    parsed_due_date = dt.date()
                except ValueError:
                    from dateutil import parser
                    dt = parser.parse(due_date)
                    parsed_due_date = dt.date()
            
            # Parse scheduled date (DATE only)
            parsed_scheduled_date = None
            if scheduled_date:
                try:
                    dt = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00'))
                    parsed_scheduled_date = dt.date()
                except ValueError:
                    from dateutil import parser
                    dt = parser.parse(scheduled_date)
                    parsed_scheduled_date = dt.date()
            else:
                # Default scheduled date to same as due date
                parsed_scheduled_date = parsed_due_date
            
            # Parse start time (TIME only)
            parsed_start_time = None
            if start_time:
                try:
                    dt = datetime.strptime(start_time, '%H:%M')
                    parsed_start_time = dt.time()
                except ValueError:
                    dt = datetime.strptime(start_time, '%H:%M:%S')
                    parsed_start_time = dt.time()
            
            # Parse end time (TIME only)
            parsed_end_time = None
            if end_time:
                try:
                    dt = datetime.strptime(end_time, '%H:%M')
                    parsed_end_time = dt.time()
                except ValueError:
                    dt = datetime.strptime(end_time, '%H:%M:%S')
                    parsed_end_time = dt.time()
            
            # Insert task into database
            task_query = """
            INSERT INTO tasks (
                user_id, title, description, status, priority, 
                category, due_date, scheduled_date, start_time, end_time, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING task_id
            """
            
            task_result = await execute_query_async(
                task_query,
                (self.user_id, title, description, 'todo', priority, category, parsed_due_date, parsed_scheduled_date, parsed_start_time, parsed_end_time),
                fetch_one=True
            )
            
            task_id = task_result[0] if task_result else None
            
            if not task_id:
                return {
                    'success': False,
                    'error': 'Failed to create task'
                }
            
            due_msg = f" (Due: {parsed_due_date.strftime('%Y-%m-%d %H:%M')})" if parsed_due_date else ""
            
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
    
    async def schedule_meeting(
        self,
        title: str,
        scheduled_date: str,
        start_time: str,
        end_time: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: str = "medium",
        description: str = "",
        collaborator_ids: Optional[List[int]] = None,
        collaborator_emails: Optional[List[str]] = None,
        meeting_code: Optional[str] = None,
        auto_generate_link: bool = True,
        duration_hours: float = 2.0
    ) -> Dict[str, Any]:
        """
        Schedule a meeting with collaborators and meeting link.
        All-in-one tool for complete meeting creation.
        
        Args:
            title: Meeting title
            scheduled_date: Scheduled DATE (YYYY-MM-DD)
            start_time: Start TIME (HH:MM or HH:MM:SS)
            end_time: End TIME (optional)
            due_date: Deadline/completion date (optional, defaults to scheduled_date)
            priority: Priority (low, medium, high, urgent)
            description: Meeting description
            collaborator_ids: List of collaborator user IDs (from friends list)
            collaborator_emails: List of email addresses to invite
            meeting_code: Existing meeting code/link
            auto_generate_link: Whether to auto-generate Google Meet link
            duration_hours: Duration in hours (used if end_time not provided)
            
        Returns:
            Dict containing event details and status
        """
        try:
            # Parse scheduled date (DATE only)
            parsed_scheduled_date = None
            try:
                dt = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00'))
                parsed_scheduled_date = dt.date()
            except ValueError:
                from dateutil import parser
                dt = parser.parse(scheduled_date)
                parsed_scheduled_date = dt.date()

            # Parse due date (defaults to scheduled_date if not provided)
            parsed_due_date = None
            if due_date:
                try:
                    dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    parsed_due_date = dt.date()
                except ValueError:
                    from dateutil import parser
                    dt = parser.parse(due_date)
                    parsed_due_date = dt.date()
            else:
                parsed_due_date = parsed_scheduled_date

            # Parse start time (TIME only)
            parsed_start_time = None
            try:
                dt = datetime.strptime(start_time, '%H:%M')
                parsed_start_time = dt.time()
            except ValueError:
                try:
                    dt = datetime.strptime(start_time, '%H:%M:%S')
                    parsed_start_time = dt.time()
                except ValueError:
                    # Fallback if start_time contains date
                    from dateutil import parser
                    dt = parser.parse(start_time)
                    parsed_start_time = dt.time()

            # Parse end time or calculate from duration
            parsed_end_time = None
            if end_time:
                try:
                    dt = datetime.strptime(end_time, '%H:%M')
                    parsed_end_time = dt.time()
                except ValueError:
                    try:
                        dt = datetime.strptime(end_time, '%H:%M:%S')
                        parsed_end_time = dt.time()
                    except ValueError:
                         # Fallback
                        from dateutil import parser
                        dt = parser.parse(end_time)
                        parsed_end_time = dt.time()
            else:
                # Calculate end_time from duration
                start_dt_for_calc = datetime.combine(parsed_scheduled_date, parsed_start_time)
                end_dt_for_calc = start_dt_for_calc + timedelta(hours=float(duration_hours))
                parsed_end_time = end_dt_for_calc.time()

            # Construct datetimes for Google Calendar
            event_start = datetime.combine(parsed_scheduled_date, parsed_start_time)
            event_end = datetime.combine(parsed_scheduled_date, parsed_end_time)
            
            # Handle crossover to next day for event_end if needed
            if parsed_end_time < parsed_start_time:
                 event_end += timedelta(days=1)

            # Create backing task first
            task_query = """
            INSERT INTO tasks (
                user_id, title, description, status, priority, 
                category, due_date, scheduled_date, start_time, end_time, created_at, updated_at
            )
            VALUES (%s, %s, %s, 'meeting', %s, 'general', %s, %s, %s, %s, NOW(), NOW())
            RETURNING task_id
            """
            
            task_result = await execute_query_async(
                task_query,
                (self.user_id, title, description, priority, parsed_due_date, parsed_scheduled_date, parsed_start_time, parsed_end_time),
                fetch_one=True
            )
            task_id = task_result[0] if task_result else None
            
            # Create calendar event
            full_desc = f"Title: {title}\n\n{description}"
            
            event_query = """
            INSERT INTO calendar_events (
                task_id, user_id, start_time, end_time, due_date, scheduled_date, event_desc, event_type, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'meeting', NOW())
            RETURNING event_id
            """
            
            event_result = await execute_query_async(
                event_query,
                (task_id, self.user_id, parsed_start_time, parsed_end_time, parsed_due_date, parsed_scheduled_date, full_desc),
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
            creds = await self.get_google_credentials()
            
            if creds:
                try:
                    def _sync_meeting():
                        service = build('calendar', 'v3', credentials=creds)
                        
                        event_body = {
                            'summary': f"🤝 {title}",
                            'description': description,
                            'start': {
                                'dateTime': event_start.isoformat(),
                                'timeZone': 'Asia/Kolkata',
                            },
                            'end': {
                                'dateTime': event_end.isoformat(),
                                'timeZone': 'Asia/Kolkata',
                            },
                        }
                        
                        # Add conferenceData if auto-generating
                        if auto_generate_link and not meeting_code:
                            event_body['conferenceData'] = {
                                'createRequest': {
                                    'requestId': f"meet-{event_id}-{datetime.now().timestamp()}",
                                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                                }
                            }
                        
                        return service.events().insert(
                            calendarId='primary',
                            body=event_body,
                            conferenceDataVersion=1 if auto_generate_link else 0
                        ).execute()

                    google_event = await asyncio.to_thread(_sync_meeting)
                    
                    google_event_id = google_event.get('id')
                    
                    # Update with Google event reference
                    if google_event_id:
                        update_query = """
                        UPDATE calendar_events 
                        SET google_event_ref = %s, is_calendar_synced = TRUE
                        WHERE event_id = %s
                        """
                        await execute_query_async(update_query, (google_event_id, event_id))
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
                                await execute_query_async(link_query, (event_id, meeting_code_extracted, meeting_url))
                                google_sync_message += f"\n🔗 Google Meet: {meeting_url}"
                                break
                
                except Exception as e:
                    google_sync_message = f"\n⚠️ Google Calendar sync failed: {str(e)}"
            
            # Add collaborators if provided
            collab_message = ""
            if collaborator_ids or collaborator_emails:
                collab_result = await self.add_collaborators_to_event(
                    event_id, 
                    collaborator_ids=collaborator_ids,
                    collaborator_emails=collaborator_emails
                )
                if collab_result['success']:
                    collab_message = f"\n👥 {collab_result['message']}"
            
            # Add custom meeting link if provided
            link_message = ""
            if meeting_code and not auto_generate_link:
                link_result = await self.generate_meeting_link(event_id, meeting_code)
                if link_result['success']:
                    link_message = f"\n🔗 {link_result['message']}"
            
            return {
                'success': True,
                'event_id': event_id,
                'google_event_id': google_event_id,
                'message': f"Meeting '{title}' scheduled for {event_start.strftime('%Y-%m-%d %H:%M')}{google_sync_message}{collab_message}{link_message}"
            }
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return {
                'success': False,
                'error': f"Failed to schedule meeting: {str(e)}"
            }


    async def get_calendar_events(
        self,
        start_date: str,
        end_date: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get calendar events within a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD or ISO)
            end_date: End date (YYYY-MM-DD or ISO)
            limit: Max records to return
            
        Returns:
            Dict containing list of events
        """
        try:
            # Parse dates
            try:
                parsed_start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                from dateutil import parser
                parsed_start = parser.parse(start_date)
                
            try:
                parsed_end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                from dateutil import parser
                parsed_end = parser.parse(end_date)
            
            # If start and end are on the same day and end time is 00:00, assume end of day
            if parsed_start.date() == parsed_end.date() and parsed_end.hour == 0 and parsed_end.minute == 0:
                parsed_end = parsed_end.replace(hour=23, minute=59, second=59)
            
            # Query database
            query = """
            SELECT 
                e.event_id, 
                COALESCE(t.title, e.event_desc, 'Untitled Event') as title,
                e.start_time, 
                e.end_time, 
                ml.meeting_url,
                e.event_type,
                t.description as task_desc,
                e.event_desc,
                e.scheduled_date
            FROM calendar_events e
            LEFT JOIN tasks t ON e.task_id = t.task_id
            LEFT JOIN meeting_links ml ON e.event_id = ml.event_id
            WHERE e.user_id = %s 
            AND e.scheduled_date >= %s 
            AND e.scheduled_date <= %s
            ORDER BY e.scheduled_date ASC, e.start_time ASC
            LIMIT %s
            """
            
            results = await execute_query_async(
                query, 
                (self.user_id, parsed_start.date(), parsed_end.date(), limit),
                fetch_all=True
            )
            
            events = []
            if results:
                for row in results:
                    # Logic to determine description
                    # If it's a task, description is in task_desc (row[6])
                    # If it's a meeting, description is in event_desc (row[7])
                    description = row[6] if row[6] else row[7]
                    
                    scheduled_date = row[8]
                    start_time = row[2]
                    end_time = row[3]
                    
                    # Construct full ISO strings if date and time exist
                    start_iso = None
                    end_iso = None
                    
                    if scheduled_date and start_time:
                         start_iso = datetime.combine(scheduled_date, start_time).isoformat()
                    
                    if scheduled_date and end_time:
                        # Handle overnight events if needed, but for now assume same day or handle simplistic
                        # If end_time < start_time, it implies next day
                        if start_time and end_time < start_time:
                             end_iso = datetime.combine(scheduled_date + timedelta(days=1), end_time).isoformat()
                        else:
                             end_iso = datetime.combine(scheduled_date, end_time).isoformat()
                    
                    events.append({
                        'event_id': row[0],
                        'title': row[1],
                        'start_time': start_iso,
                        'end_time': end_iso,
                        'meeting_link': row[4],
                        'type': row[5] if row[5] else ('task' if row[6] else 'event'),
                        'description': description
                    })
            
            return {
                'success': True,
                'count': len(events),
                'events': events,
                'message': f"Found {len(events)} events from {parsed_start.date()} to {parsed_end.date()}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to fetch events: {str(e)}"
            }
    
    async def check_schedule_conflicts(
        self,
        scheduled_date: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        duration_hours: Optional[float] = 2.0
    ) -> Dict[str, Any]:
        """
        Check for scheduling conflicts on a given date/time.
        Checks tasks.scheduled_date and start_time/end_time for overlaps.
        
        Args:
            scheduled_date: The proposed scheduled date (YYYY-MM-DD)
            start_time: The proposed start time (HH:MM)
            end_time: The proposed end time (HH:MM)
            duration_hours: Expected duration in hours (default: 2.0)
            
        Returns:
            Dict containing conflicts and suggested alternative times
        """
        try:
            # Parse scheduled date
            try:
                parsed_date = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00')).date()
            except ValueError:
                from dateutil import parser
                parsed_date = parser.parse(scheduled_date).date()
            
            # Ensure duration_hours is float
            if duration_hours:
                try:
                    duration_hours = float(duration_hours)
                except (ValueError, TypeError):
                    duration_hours = 2.0
            else:
                duration_hours = 2.0
            
            # Parse start time
            parsed_start_time = None
            if start_time:
                try:
                    parsed_start_time = datetime.strptime(start_time, '%H:%M').time()
                except ValueError:
                    parsed_start_time = datetime.strptime(start_time, '%H:%M:%S').time()
            
            # Parse end time
            parsed_end_time = None
            if end_time:
                try:
                    parsed_end_time = datetime.strptime(end_time, '%H:%M').time()
                except ValueError:
                    parsed_end_time = datetime.strptime(end_time, '%H:%M:%S').time()
            elif parsed_start_time:
                # Calculate end time from duration
                duration = duration_hours if duration_hours is not None else 2.0
                start_dt = datetime.combine(parsed_date, parsed_start_time)
                end_dt = start_dt + timedelta(hours=duration)
                parsed_end_time = end_dt.time()
            
            # Query for tasks on the same day
            conflict_query = """
            SELECT 
                task_id,
                title,
                scheduled_date,
                due_date,
                start_time,
                end_time,
                priority,
                status,
                description
            FROM tasks
            WHERE user_id = %s 
              AND scheduled_date IS NOT NULL
              AND scheduled_date = %s
            ORDER BY start_time NULLS LAST, scheduled_date
            """
            
            results = await execute_query_async(
                conflict_query,
                (self.user_id, parsed_date),
                fetch_all=True
            )
            
            conflicts = []
            has_time_overlap = False
            
            for row in results:
                task_id, title, scheduled_date, due_date, start_time, end_time, priority, status, description = row
                
                # Check for time overlap if both tasks have start/end times
                is_time_overlap = False
                if parsed_start_time and parsed_end_time and start_time and end_time:
                    # Check if time ranges overlap
                    if start_time < parsed_end_time and end_time > parsed_start_time:
                        is_time_overlap = True
                        has_time_overlap = True
                
                conflicts.append({
                    'task_id': task_id,
                    'title': title,
                    'scheduled_date': scheduled_date.isoformat() if scheduled_date else None,
                    'due_date': due_date.isoformat() if due_date else None,
                    'start_time': start_time.strftime('%H:%M') if start_time else None,
                    'end_time': end_time.strftime('%H:%M') if end_time else None,
                    'priority': priority,
                    'status': status,
                    'description': description[:100] if description else None,
                    'is_time_overlap': is_time_overlap
                })
            
            # Suggest alternative times if conflicts exist
            suggested_times = []
            if has_time_overlap and parsed_start_time:
                # Find free time slots on the same day
                day_start = datetime.strptime('09:00', '%H:%M').time()
                day_end = datetime.strptime('18:00', '%H:%M').time()
                
                current_time = day_start
                while current_time < day_end and len(suggested_times) < 3:
                    # Calculate slot end time
                    slot_start_dt = datetime.combine(parsed_date, current_time)
                    slot_end_dt = slot_start_dt + timedelta(hours=duration_hours)
                    slot_end_time = slot_end_dt.time()
                    
                    # Check if this slot conflicts
                    is_free = True
                    for conflict in conflicts:
                        if conflict['start_time'] and conflict['end_time']:
                            conf_start = datetime.strptime(conflict['start_time'], '%H:%M').time()
                            conf_end = datetime.strptime(conflict['end_time'], '%H:%M').time()
                            
                            if current_time < conf_end and slot_end_time > conf_start:
                                is_free = False
                                break
                    
                    if is_free:
                        suggested_times.append(current_time.strftime('%H:%M'))
                    
                    # Move to next 30-minute slot
                    next_dt = datetime.combine(parsed_date, current_time) + timedelta(minutes=30)
                    current_time = next_dt.time()
            
            # Suggest alternative dates if no free times on same day
            suggested_dates = []
            if conflicts and not suggested_times:
                current_day = parsed_date + timedelta(days=1)
                days_checked = 0
                
                while len(suggested_dates) < 3 and days_checked < 7:
                    check_query = """
                    SELECT COUNT(*) 
                    FROM tasks 
                    WHERE user_id = %s 
                      AND scheduled_date = %s
                    """
                    count_result = await execute_query_async(
                        check_query,
                        (self.user_id, current_day),
                        fetch_one=True
                    )
                    
                    if count_result and count_result[0] == 0:
                        suggested_dates.append(current_day.isoformat())
                    
                    current_day += timedelta(days=1)
                    days_checked += 1
            
            return {
                'success': True,
                'has_conflicts': len(conflicts) > 0,
                'has_time_overlap': has_time_overlap,
                'conflict_count': len(conflicts),
                'conflicts': conflicts,
                'suggested_times': suggested_times,
                'suggested_dates': suggested_dates,
                'message': f"Found {len(conflicts)} task(s) on {parsed_date.strftime('%Y-%m-%d')}" + 
                          (f" ({len([c for c in conflicts if c['is_time_overlap']])} time overlap(s))" if has_time_overlap else "") 
                          if conflicts else "No conflicts found"
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR in check_schedule_conflicts: {error_details}")
            return {
                'success': False,
                'error': f"Failed to check conflicts: {str(e)}"
            }



def get_calendar_tools(user_id: int) -> List[Dict[str, Any]]:
    """
    Get available calendar MCP tools for the given user.
    
    Args:
        user_id: User ID to create tools for
        
    Returns:
        List of tool definitions in MCP format
    """
    tools_instance = MCPCalendarTools(user_id)
    
    return [
        {
            'name': 'get_calendar_events',
            'description': 'Get calendar events and meetings within a specified date range. Use this to show the user their schedule.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'start_date': {
                        'type': 'string',
                        'description': 'Start date (YYYY-MM-DD)'
                    },
                    'end_date': {
                        'type': 'string',
                        'description': 'End date (YYYY-MM-DD)'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Max number of events to return (default 50)'
                    }
                },
                'required': ['start_date', 'end_date']
            },
            'function': tools_instance.get_calendar_events
        },
        
        {
            'name': 'check_schedule_conflicts',
            'description': 'Check for scheduling conflicts on a given date/time. Shows existing tasks and checks for time overlaps using start_time and end_time.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'scheduled_date': {
                        'type': 'string',
                        'description': 'The proposed scheduled date (YYYY-MM-DD)'
                    },
                    'start_time': {
                        'type': 'string',
                        'description': 'The proposed start time (HH:MM format, e.g., "14:30")'
                    },
                    'end_time': {
                        'type': 'string',
                        'description': 'The proposed end time (HH:MM format, e.g., "16:00")'
                    },
                    'duration_hours': {
                        'type': 'number',
                        'description': 'Expected duration in hours (default: 2.0, used if end_time not provided)',
                        'default': 2.0
                    }
                },
                'required': ['scheduled_date']
            },
            'function': tools_instance.check_schedule_conflicts
        },
        
        {
            'name': 'add_task_to_calendar',
            'description': 'Add a task or event to the calendar with Google Calendar sync.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'title': {
                        'type': 'string',
                        'description': 'Task or event title'
                    },
                    'description': {
                        'type': 'string',
                        'description': 'Detailed description'
                    },
                    'due_date': {
                        'type': 'string',
                        'description': 'Deadline/completion DATE (YYYY-MM-DD)'
                    },
                    'scheduled_date': {
                        'type': 'string',
                        'description': 'When task is scheduled DATE (YYYY-MM-DD)'
                    },
                    'start_time': {
                        'type': 'string',
                        'description': 'Start TIME (HH:MM format)'
                    },
                    'end_time': {
                        'type': 'string',
                        'description': 'End TIME (HH:MM format)'
                    },
                    'priority': {
                        'type': 'string',
                        'enum': ['low', 'medium', 'high', 'urgent'],
                        'description': 'Task priority'
                    },
                    'category': {
                        'type': 'string',
                        'description': 'Category or tag'
                    },
                    'meeting_link': {
                        'type': 'string',
                        'description': 'Optional meeting link'
                    }
                },
                'required': ['title', 'priority', 'due_date', 'scheduled_date']
            },
            'function': tools_instance.add_task_to_calendar
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
                        'description': 'Type of search to perform (default: any)',
                        'default': 'any'
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
                        'description': 'Deadline/completion DATE (YYYY-MM-DD)'
                    },
                    'scheduled_date': {
                        'type': 'string',
                        'description': 'When task is scheduled DATE (YYYY-MM-DD)'
                    },
                    'start_time': {
                        'type': 'string',
                        'description': 'Start TIME (HH:MM format)'
                    },
                    'end_time': {
                        'type': 'string',
                        'description': 'End TIME (HH:MM format)'
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
                'required': ['title', 'priority', 'due_date', 'scheduled_date']
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
                    'scheduled_date': {
                        'type': 'string',
                        'description': 'Scheduled DATE (YYYY-MM-DD)'
                    },
                    'start_time': {
                        'type': 'string',
                        'description': 'Start TIME (HH:MM format)'
                    },
                    'end_time': {
                        'type': 'string',
                        'description': 'End TIME (HH:MM format)'
                    },
                    'due_date': {
                        'type': 'string',
                        'description': 'Deadline/completion DATE (YYYY-MM-DD)'
                    },
                    'priority': {
                        'type': 'string',
                        'enum': ['low', 'medium', 'high', 'urgent'],
                        'description': 'Meeting priority'
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
                    },
                    'duration_hours': {
                        'type': 'number',
                        'description': 'Duration in hours (used if end_time not provided)'
                    }
                },
                'required': ['title', 'scheduled_date', 'start_time', 'priority']
            },
            'function': tools_instance.schedule_meeting
        }
    ]


async def execute_calendar_tool(user_id: int, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a calendar MCP tool by name.
    
    Args:
        user_id: User ID executing the tool
        tool_name: Name of the tool to execute
        parameters: Parameters to pass to the tool
        
    Returns:
        Tool execution result
    """
    tools_instance = MCPCalendarTools(user_id)
    
    if tool_name == 'add_task_to_calendar':
        return await tools_instance.add_task_to_calendar(**parameters)
    elif tool_name == 'get_collaborators':
        return await tools_instance.get_collaborators(**parameters)
    elif tool_name == 'add_collaborators_to_event':
        return await tools_instance.add_collaborators_to_event(**parameters)
    elif tool_name == 'generate_meeting_link':
        return await tools_instance.generate_meeting_link(**parameters)
    elif tool_name == 'save_todo_only':
        return await tools_instance.save_todo_only(**parameters)
    elif tool_name == 'schedule_meeting':
        return await tools_instance.schedule_meeting(**parameters)
    elif tool_name == 'get_calendar_events':
        return await tools_instance.get_calendar_events(**parameters)
    else:
        return {
            'success': False,
            'error': f"Unknown calendar tool: {tool_name}"
        }

