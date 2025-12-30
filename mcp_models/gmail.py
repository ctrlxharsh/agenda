

from typing import Any, Dict, List, Optional
import base64
from email.mime.text import MIMEText
from datetime import datetime
import asyncio
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils.db import execute_query_async

class MCPGmailTools:
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    async def get_google_credentials(self) -> Optional[Credentials]:
        query = """
        SELECT access_token, refresh_token, token_expiry, token_uri, 
               client_id, client_secret, scopes 
        FROM user_gmail_accounts 
        WHERE user_id = %s
        """
        print(f"DEBUG: MCPGmailTools credentials query for user_id: {self.user_id}")
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

    async def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        try:
            creds = await self.get_google_credentials()
            if not creds:
                return {
                    'success': False,
                    'error': f"Gmail account not connected for user_id {self.user_id}. No credentials found in DB. Please authorize Gmail in the Settings/Authorization page."
                }
            
            def _send_message():
                service = build('gmail', 'v1', credentials=creds)
                
                message = MIMEText(body)
                message['to'] = to
                message['subject'] = subject
                
                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
                
                return service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()

            result = await asyncio.to_thread(_send_message)
            
            return {
                'success': True,
                'message': f"✅ Email sent to {to}",
                'message_id': result.get('id')
            }
            
        except Exception as e:
            error_msg = str(e)
            if "insufficient authentication scopes" in error_msg or "403" in error_msg:
                # Debugging info
                return {
                    'success': False,
                    'error': f"Insufficient Permissions. Your current token scopes are: {creds.scopes if creds else 'None'}. Please try disconnecting and reconnecting Google integration with Gmail enabled.",
                    'debug_error': error_msg
                }
            return {
                'success': False,
                'error': f"Failed to send email: {error_msg}"
            }

    async def read_emails(self, query: str = "", limit: int = 5) -> Dict[str, Any]:
        try:
            creds = await self.get_google_credentials()
            if not creds:
                return {
                    'success': False,
                    'error': f"Gmail account not connected for user_id {self.user_id}. No credentials found in DB. Please authorize Gmail in the Settings/Authorization page."
                }
            
            def _fetch_emails():
                service = build('gmail', 'v1', credentials=creds)
                
                # List messages
                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=limit
                ).execute()
                
                messages = results.get('messages', [])
                email_details = []
                
                if not messages:
                    return []
                
                for msg in messages:
                    # Get full message details
                    msg_detail = service.users().messages().get(
                        userId='me', 
                        id=msg['id'], 
                        format='full'
                    ).execute()
                    
                    headers = msg_detail.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown Sender)')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                    snippet = msg_detail.get('snippet', '')
                    
                    email_details.append({
                        'id': msg['id'],
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'snippet': snippet,
                        'link': f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}"
                    })
                    
                return email_details

            emails = await asyncio.to_thread(_fetch_emails)
            
            if not emails:
                return {
                    'success': True,
                    'emails': [],
                    'message': f"No emails found matching '{query}'"
                }

            return {
                'success': True,
                'emails': emails,
                'count': len(emails),
                'message': f"Found {len(emails)} emails matching '{query}'"
            }
            
        except Exception as e:
            error_msg = str(e)
            if "insufficient authentication scopes" in error_msg or "403" in error_msg:
                return {
                    'success': False,
                    'error': f"Insufficient Permissions. Your current token scopes are: {creds.scopes if creds else 'None'}. Please try disconnecting and reconnecting Google integration with Gmail enabled.",
                    'debug_error': error_msg
                }
            return {
                'success': False,
                'error': f"Failed to read emails: {error_msg}"
            }

def get_gmail_tools(user_id: int) -> List[Dict[str, Any]]:
    tools_instance = MCPGmailTools(user_id)
    
    return [
        {
            'name': 'gmail_send_email',
            'description': 'Send an email to a recipient.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'to': {'type': 'string', 'description': 'Recipient email address'},
                    'subject': {'type': 'string', 'description': 'Email subject'},
                    'body': {'type': 'string', 'description': 'Email body content'}
                },
                'required': ['to', 'subject', 'body']
            },
            'function': tools_instance.send_email
        },
        {
            'name': 'gmail_read_emails',
            'description': 'Read and summarize emails. Can filter by keyword.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string', 
                        'description': 'Gmail search query (e.g., "from:person", "subject:meeting", "hackathon")'
                    },
                    'limit': {
                        'type': 'integer', 
                        'description': 'Max number of emails to return (default 5)'
                    }
                },
                'required': ['query']  # Require a query to be safe, or make it optional? existing code makes it optional but let's encourage specific searches
            },
            'function': tools_instance.read_emails
        }
    ]

async def execute_gmail_tool(user_id: int, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a Gmail MCP tool by name.
    """
    tools_instance = MCPGmailTools(user_id)
    
    if tool_name == 'gmail_send_email':
        return await tools_instance.send_email(**parameters)
    elif tool_name == 'gmail_read_emails':
        return await tools_instance.read_emails(**parameters)
    else:
        return {
            'success': False,
            'error': f"Unknown Gmail tool: {tool_name}"
        }
