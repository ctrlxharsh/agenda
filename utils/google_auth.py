import os
import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
REDIRECT_URI = "http://localhost:8501"  # Streamlit port

CLIENT_SECRETS_FILE = "client_secret.json"

def get_flow(additional_scopes=None, override_scopes=None):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return None
    
    if override_scopes:
        current_scopes = override_scopes
    else:
        current_scopes = SCOPES.copy()
        if additional_scopes:
            current_scopes.extend(additional_scopes)
    
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=current_scopes)
    flow.redirect_uri = REDIRECT_URI
    return flow

def credentials_to_dict(creds):
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
