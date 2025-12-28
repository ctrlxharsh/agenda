import streamlit as st
from utils.google_auth import get_flow, credentials_to_dict
from pages.calendar.data import save_google_token_db, get_google_token_db
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import datetime

def get_calendar_service(user_id):
    """
    Returns a Google Calendar Service object if authenticated, else None.
    """
    token_data = get_google_token_db(user_id)
    if not token_data:
        return None
    
    creds = Credentials(
        token=token_data['token'],
        refresh_token=token_data['refresh_token'],
        token_uri=token_data['token_uri'],
        client_id=token_data['client_id'],
        client_secret=token_data['client_secret'],
        scopes=token_data['scopes']
    )
    
    return build('calendar', 'v3', credentials=creds)

def auth_flow_step():
    """
    Handles the UI/Logic for starting Authorization.
    """
    flow = get_flow()
    if not flow:
        st.error("Missing `client_secret.json`. Please add it to the project root to enable Google Calendar.")
        return
    
    # 1. Generate URL
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    st.write("Authorize access to your Google Calendar:")
    st.link_button("Connect Google Account", auth_url)

    # 2. Handle Callback (Streamlit reloads with params)
    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
        try:
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            # Save to DB
            user_id = st.session_state.user['id']
            save_google_token_db(user_id, creds)
            
            st.success("Connected! Loading calendar...")
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Auth failed: {e}")

def get_events_by_range(service, time_min, time_max):
    """
    Fetches events within a specific time range.
    time_min, time_max: ISO format strings (with 'Z' or offset)
    """
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])
