import os
import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


CLIENT_SECRETS_FILE = "client_secret.json"

import streamlit as st

from utils.env_config import EnvConfig

# Standard Google OAuth 2.0 endpoints
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"

def _get_val(key):
    if key in st.secrets:
        return str(st.secrets[key])
    return os.getenv(key)

def get_flow(additional_scopes=None, override_scopes=None):
    if override_scopes:
        current_scopes = override_scopes
    else:
        current_scopes = SCOPES.copy()
        if additional_scopes:
            current_scopes.extend(additional_scopes)
            
    # Priority 1: Check for client_secret.json file
    if os.path.exists(CLIENT_SECRETS_FILE):
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=current_scopes)
            
    # Priority 2: Check for secrets/env vars
    else:
        client_id = _get_val("GOOGLE_CLIENT_ID")
        client_secret = _get_val("GOOGLE_CLIENT_SECRET")
        
        if client_id and client_secret:
            client_config = {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": GOOGLE_AUTH_URI,
                    "token_uri": GOOGLE_TOKEN_URI,
                }
            }
            flow = google_auth_oauthlib.flow.Flow.from_client_config(
                client_config, scopes=current_scopes)
        else:
            return None

    flow.redirect_uri = EnvConfig.get_app_url()
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
