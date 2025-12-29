"""
Authorization Logic Layer

OAuth flow helpers for third-party service connections.
"""

import streamlit as st
from utils.google_auth import get_flow, GMAIL_SCOPES
from pages.calendar.data import save_google_token_db
import os



def google_auth_flow():
    """
    Handles the Google Calendar OAuth flow.
    Returns True if already connected or connection successful.
    """
    # Allow oauthlib to accept scope changes
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    
    if not os.path.exists("client_secret.json"):
        st.error("Google Calendar is not configured.")
        st.info("Admin: Please place `client_secret.json` in the app root to enable this feature.")
        return False
    
    flow = get_flow() # Default scopes are Calendar
    if not flow:
        st.error("Failed to initialize Google OAuth flow.")
        return False
    
    # Generate authorization URL
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    st.write("Authorize access to your Google Calendar:")
    st.link_button("🔗 Connect Google Calendar", auth_url)
    
    # Handle callback (Streamlit reloads with params)
    query_params = st.query_params
    if "code" in query_params and query_params.get("state") != "gmail": # Simple way to distinguish? No, query_params are global.
        # We need a way to distinguish which flow initiated the callback.
        # Usually 'state' parameter is used. 
        # Streamlit query params persistence is tricky. 
        # For now, let's assume if there's a code, we try to exchange it. 
        # BUT if we have two buttons, we must know which one.
        # Let's check a specialized query param or just try both?
        # A cleaner way is to use the `state` param in OAuth flow.
        pass

    # Since we can't easily modify the callback URL handler without shared state, 
    # we'll use a specific query param trigger or just rely on the user clicking the right 'Complete' button if we were doing manual.
    # But here it's auto-rerun.
    
    # PROPOSAL: Use a 'type' param in the redirect URI if possible? No, redirect_uri is fixed in console usually.
    # We can use the 'state' parameter. get_flow doesn't expose it easily but flow.authorization_url does.
    
    return False

# Redefining to actually implement the logic with state check
def google_auth_flow():
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    if not os.path.exists("client_secret.json"):
        st.error("Google Calendar is not configured.")
        return False
        
    flow = get_flow()
    flow.redirect_uri = "http://localhost:8501" # Ensure match
    
    # We use state='calendar' to identify this flow
    auth_url, state = flow.authorization_url(prompt='consent', state='calendar')
    
    st.write("Authorize access to Google Calendar:")
    st.link_button("🔗 Connect Calendar", auth_url)

    query_params = st.query_params
    if "code" in query_params:
        # Check state if available, or try to infer
        # Google returns state param back
        returned_state = query_params.get("state")
        
        if returned_state == 'calendar':
            try:
                flow.fetch_token(code=query_params["code"])
                creds = flow.credentials
                user_id = st.session_state.user['id']
                save_google_token_db(user_id, creds)
                st.success("✅ Google Calendar connected successfully!")
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Calendar authorization failed: {e}")


def gmail_auth_flow():
    """
    Handles the Gmail OAuth flow.
    """
    from pages.calendar.data import save_gmail_token_db
    
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    if not os.path.exists("client_secret.json"):
        st.error("Google Client Secrets not found.")
        return False
        
    # Request ONLY Gmail scopes (and maybe basic profile implicitly)
    flow = get_flow(override_scopes=GMAIL_SCOPES)
    flow.redirect_uri = "http://localhost:8501"
    
    # State='gmail' to distinguish
    auth_url, state = flow.authorization_url(prompt='consent', state='gmail')
    
    st.write("Authorize access to Gmail:")
    st.link_button("🔗 Connect Gmail", auth_url)

    query_params = st.query_params
    if "code" in query_params:
        returned_state = query_params.get("state")
        
        if returned_state == 'gmail':
            try:
                flow.fetch_token(code=query_params["code"])
                creds = flow.credentials
                user_id = st.session_state.user['id']
                save_gmail_token_db(user_id, creds)
                st.success("✅ Gmail connected successfully!")
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Gmail authorization failed: {e}")


def github_auth_flow():
    """
    Handles the GitHub OAuth flow.
    Returns True if already connected or connection successful.
    """
    from utils.github_auth import (
        get_authorization_url, 
        exchange_code_for_token, 
        get_github_user,
        is_github_configured
    )
    from pages.authorization.data import save_github_credentials
    
    if not is_github_configured():
        st.error("GitHub is not configured.")
        st.info("Admin: Please add `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` to your .env file.")
        return False
    
    # Generate authorization URL
    auth_url = get_authorization_url()
    
    if not auth_url:
        st.error("Failed to generate GitHub authorization URL.")
        return False
    
    st.write("Authorize access to your GitHub account:")
    st.link_button("🔗 Connect GitHub Account", auth_url)
    
    # Handle callback (Streamlit reloads with params)
    query_params = st.query_params
    if "code" in query_params and "state" in query_params:
        code = query_params["code"]
        try:
            # Exchange code for token
            token_data = exchange_code_for_token(code)
            
            if not token_data or "access_token" not in token_data:
                st.error("Failed to get access token from GitHub.")
                return False
            
            access_token = token_data["access_token"]
            scopes = token_data.get("scope", "").split(",")
            
            # Get GitHub username
            user_info = get_github_user(access_token)
            
            if not user_info:
                st.error("Failed to fetch GitHub user info.")
                return False
            
            github_username = user_info.get("login")
            
            # Save to DB
            user_id = st.session_state.user['id']
            save_github_credentials(user_id, github_username, access_token, scopes)
            
            st.success(f"✅ GitHub connected as @{github_username}!")
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"GitHub authorization failed: {e}")
    
    return False


def linkedin_auth_flow():
    """
    Placeholder for LinkedIn OAuth flow.
    """
    st.info("🚧 LinkedIn integration coming soon!")
    return False

