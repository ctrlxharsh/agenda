from utils.db import execute_query
import json
from datetime import datetime

def save_google_token_db(user_id, creds):
    """
    Saves or updates Google OAuth tokens for a user.
    creds: google.oauth2.credentials.Credentials object
    """
    # Convert scopes list to array string for Postgres if needed, or rely on psycopg2 adapter
    scopes = list(creds.scopes) if creds.scopes else []
    
    query = """
    INSERT INTO user_google_accounts (
        user_id, access_token, refresh_token, token_expiry, 
        token_uri, client_id, client_secret, scopes
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (user_id) 
    DO UPDATE SET
        access_token = EXCLUDED.access_token,
        refresh_token = COALESCE(EXCLUDED.refresh_token, user_google_accounts.refresh_token), -- Keep old refresh if new one is missing (common in re-auth)
        token_expiry = EXCLUDED.token_expiry,
        scopes = EXCLUDED.scopes,
        created_at = now();
    """
    execute_query(query, (
        user_id,
        creds.token,
        creds.refresh_token,
        creds.expiry,
        creds.token_uri,
        creds.client_id,
        creds.client_secret,
        scopes
    ))

def get_google_token_db(user_id):
    """
    Retrieves credentials data for a user.
    """
    query = """
    SELECT access_token, refresh_token, token_expiry, token_uri, client_id, client_secret, scopes 
    FROM user_google_accounts 
    WHERE user_id = %s
    """
    res = execute_query(query, (user_id,), fetch_one=True)
    if res:
        return {
            "token": res[0],
            "refresh_token": res[1],
            "expiry": res[2],
            "token_uri": res[3],
            "client_id": res[4],
            "client_secret": res[5],
            "scopes": res[6]
        }
    return None

def save_gmail_token_db(user_id, creds):
    """
    Saves or updates Gmail OAuth tokens for a user.
    """
    scopes = list(creds.scopes) if creds.scopes else []
    
    query = """
    INSERT INTO user_gmail_accounts (
        user_id, access_token, refresh_token, token_expiry, 
        token_uri, client_id, client_secret, scopes
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::json)
    ON CONFLICT (user_id) 
    DO UPDATE SET
        access_token = EXCLUDED.access_token,
        refresh_token = COALESCE(EXCLUDED.refresh_token, user_gmail_accounts.refresh_token),
        token_expiry = EXCLUDED.token_expiry,
        scopes = EXCLUDED.scopes;
    """
    
    scopes_json = json.dumps(scopes)
    
    execute_query(query, (
        user_id,
        creds.token,
        creds.refresh_token,
        creds.expiry,
        creds.token_uri,
        creds.client_id,
        creds.client_secret,
        scopes_json
    ))

def get_gmail_token_db(user_id):
    """
    Retrieves Gmail credentials data for a user.
    """
    query = """
    SELECT access_token, refresh_token, token_expiry, token_uri, client_id, client_secret, scopes 
    FROM user_gmail_accounts 
    WHERE user_id = %s
    """
    res = execute_query(query, (user_id,), fetch_one=True)
    if res:
        return {
            "token": res[0],
            "refresh_token": res[1],
            "expiry": res[2],
            "token_uri": res[3],
            "client_id": res[4],
            "client_secret": res[5],
            "scopes": res[6]
        }
    return None
