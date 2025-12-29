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
