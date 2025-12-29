"""
Session Management

Provides persistent session handling using database-stored tokens.
"""

import secrets
from datetime import datetime, timedelta
from utils.db import execute_query


def create_session(user_id: int) -> str:
    """
    Create a new session for the user.
    
    Args:
        user_id: User ID
        
    Returns:
        Session token string
    """
    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=7)  # 7 day expiry
    
    # Delete any existing sessions for this user
    execute_query("DELETE FROM user_sessions WHERE user_id = %s", (user_id,))
    
    # Create new session
    execute_query(
        """
        INSERT INTO user_sessions (user_id, session_token, expires_at, created_at)
        VALUES (%s, %s, %s, NOW())
        """,
        (user_id, token, expires_at)
    )
    
    return token


def validate_session(token: str) -> dict | None:
    """
    Validate a session token and return user data if valid.
    
    Args:
        token: Session token
        
    Returns:
        User dict if valid, None otherwise
    """
    if not token:
        return None
    
    result = execute_query(
        """
        SELECT u.id, u.username, u.email, u.full_name, s.expires_at
        FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_token = %s AND s.expires_at > NOW()
        """,
        (token,),
        fetch_one=True
    )
    
    if result:
        return {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'full_name': result[3]
        }
    return None


def delete_session(token: str) -> None:
    """Delete a session token."""
    if token:
        execute_query("DELETE FROM user_sessions WHERE session_token = %s", (token,))
