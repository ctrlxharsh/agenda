"""
Authorization Data Layer

Database functions for checking and managing third-party service connections.
"""

from utils.db import execute_query


def check_google_connection(user_id: int) -> dict | None:
    """
    Check if user has Google Calendar connected.
    Returns connection details if connected, None otherwise.
    """
    query = """
    SELECT access_token, created_at 
    FROM user_google_accounts 
    WHERE user_id = %s
    """
    result = execute_query(query, (user_id,), fetch_one=True)
    if result:
        return {
            "connected": True,
            "connected_at": result[1]
        }
    return None


def check_github_connection(user_id: int) -> dict | None:
    """
    Check if user has GitHub connected.
    Returns connection details if connected, None otherwise.
    """
    query = """
    SELECT github_username, connected_at 
    FROM user_github_accounts 
    WHERE user_id = %s
    """
    result = execute_query(query, (user_id,), fetch_one=True)
    if result:
        return {
            "connected": True,
            "username": result[0],
            "connected_at": result[1]
        }
    return None


def disconnect_google(user_id: int) -> bool:
    """
    Remove Google Calendar connection for user.
    """
    query = "DELETE FROM user_google_accounts WHERE user_id = %s"
    execute_query(query, (user_id,))
    return True


def disconnect_github(user_id: int) -> bool:
    """
    Remove GitHub connection for user.
    """
    query = "DELETE FROM user_github_accounts WHERE user_id = %s"
    execute_query(query, (user_id,))
    return True


def save_github_credentials(
    user_id: int,
    github_username: str,
    access_token: str,
    scopes: list = None
) -> bool:
    """
    Save GitHub OAuth credentials for user.
    
    Args:
        user_id: User's ID
        github_username: GitHub username
        access_token: OAuth access token
        scopes: List of authorized scopes
        
    Returns:
        True on success
    """
    import json
    
    # Delete existing connection first
    disconnect_github(user_id)
    
    query = """
    INSERT INTO user_github_accounts (
        user_id, github_username, access_token, scopes, connected_at
    )
    VALUES (%s, %s, %s, %s, NOW())
    """
    
    scopes_json = json.dumps(scopes) if scopes else None
    execute_query(query, (user_id, github_username, access_token, scopes_json))
    return True


def get_github_access_token(user_id: int) -> str | None:
    """
    Get GitHub access token for user.
    
    Args:
        user_id: User's ID
        
    Returns:
        Access token if connected, None otherwise
    """
    query = "SELECT access_token FROM user_github_accounts WHERE user_id = %s"
    result = execute_query(query, (user_id,), fetch_one=True)
    return result[0] if result else None
