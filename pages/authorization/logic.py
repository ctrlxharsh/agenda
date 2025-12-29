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
    Placeholder for GitHub OAuth flow.
    """
    st.info("🚧 GitHub integration coming soon!")
    return False


def linkedin_auth_flow():
    """
    Placeholder for LinkedIn OAuth flow.
    """
    st.info("🚧 LinkedIn integration coming soon!")
    return False
