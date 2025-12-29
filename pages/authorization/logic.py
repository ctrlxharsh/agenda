"""
Authorization Logic Layer

OAuth flow helpers for third-party service connections.
"""

import streamlit as st
from utils.google_auth import get_flow
from pages.calendar.data import save_google_token_db
import os


def google_auth_flow():
    """
    Handles the Google Calendar OAuth flow.
    Returns True if already connected or connection successful.
    """
    if not os.path.exists("client_secret.json"):
        st.error("Google Calendar is not configured.")
        st.info("Admin: Please place `client_secret.json` in the app root to enable this feature.")
        return False
    
    flow = get_flow()
    if not flow:
        st.error("Failed to initialize Google OAuth flow.")
        return False
    
    # Generate authorization URL
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    st.write("Authorize access to your Google Calendar:")
    st.link_button("🔗 Connect Google Account", auth_url)
    
    # Handle callback (Streamlit reloads with params)
    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
        try:
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            # Save to DB
            user_id = st.session_state.user['id']
            save_google_token_db(user_id, creds)
            
            st.success("✅ Google Calendar connected successfully!")
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Authorization failed: {e}")
    
    return False


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

