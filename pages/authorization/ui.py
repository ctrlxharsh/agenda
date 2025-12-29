"""
Authorization UI

Centralized panel for managing all third-party service connections.
"""

import streamlit as st
from pages.authorization.data import (
    check_google_connection,
    check_github_connection,
    disconnect_google,
    disconnect_github
)
from pages.authorization.logic import google_auth_flow, github_auth_flow


def distinct_authorization_page():
    st.title("🔐 Authorizations")
    st.write("Manage your connected services and third-party integrations.")
    
    user_id = st.session_state.user['id']
    
    # --- Google Calendar Section ---
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("📅 Google Calendar")
            st.caption("Sync your events and manage your schedule")
        
        google_status = check_google_connection(user_id)
        
        with col2:
            if google_status:
                st.success("Connected", icon="✅")
            else:
                st.warning("Not Connected", icon="⚠️")
        
        if google_status:
            st.info(f"Connected since: {google_status['connected_at'].strftime('%b %d, %Y') if google_status['connected_at'] else 'Unknown'}")
            
            if st.button("🔌 Disconnect Google Calendar", key="disconnect_google", type="secondary"):
                disconnect_google(user_id)
                st.success("Google Calendar disconnected!")
                st.rerun()
        else:
            google_auth_flow()
    
    st.divider()
    
    # --- GitHub Section ---
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("🐙 GitHub")
            st.caption("Access repositories, issues, and pull requests")
        
        github_status = check_github_connection(user_id)
        
        with col2:
            if github_status:
                st.success("Connected", icon="✅")
            else:
                st.warning("Not Connected", icon="⚠️")
        
        if github_status:
            st.info(f"Connected as: @{github_status['username']}")
            
            if st.button("🔌 Disconnect GitHub", key="disconnect_github", type="secondary"):
                disconnect_github(user_id)
                st.success("GitHub disconnected!")
                st.rerun()
        else:
            st.write("GitHub integration will allow you to:")
            st.markdown("""
            - 📂 View and manage repositories
            - 🐛 Track issues and pull requests
            - 🔔 Get notifications in your dashboard
            - 🚀 Create new repos with starter templates
            """)
            github_auth_flow()
    
    st.divider()
    
    # --- LinkedIn Section ---
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("💼 LinkedIn")
            st.caption("Professional networking and job insights")
        
        with col2:
            st.info("Coming Soon", icon="🚧")
        
        st.write("LinkedIn integration will allow you to:")
        st.markdown("""
        - 👤 View your professional profile
        - 🤝 Manage connections
        - 📝 Schedule and create posts
        """)
        st.button("🔗 Connect LinkedIn", disabled=True, key="connect_linkedin")
