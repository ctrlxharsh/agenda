import os
import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
REDIRECT_URI = "http://localhost:8501" # Standard Streamlit local port

# In a real app, you would load this from a file or env vars.
# For now, we unfortunately MUST have a client_secret.json to behave like a web server flow.
# If the user doesn't have one, we can't do the real redirect flow easily without manual token pasting.
CLIENT_SECRETS_FILE = "client_secret.json"

def get_flow():
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return None
    
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)
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
