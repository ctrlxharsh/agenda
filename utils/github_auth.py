"""GitHub OAuth Authentication Utilities."""

import os
import requests
from typing import Optional, Dict, Any
from utils.env_config import EnvConfig

# GitHub OAuth endpoints
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE = "https://api.github.com"

# Required scopes for full functionality
GITHUB_SCOPES = [
    "repo",           # Full control of private repositories
    "user",           # Read user profile data
    "notifications",  # Access notifications
    "workflow",       # Update GitHub Action workflows
    "read:org",       # Read org membership
]

REDIRECT_URI = "http://localhost:8501"  # Streamlit port


def get_authorization_url(state: str = "github_auth") -> Optional[str]:
    """Generate GitHub OAuth authorization URL."""
    client_id = EnvConfig.get_github_client_id()
    
    if not client_id:
        return None
    
    scopes = " ".join(GITHUB_SCOPES)
    
    auth_url = (
        f"{GITHUB_AUTHORIZE_URL}"
        f"?client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scopes}"
        f"&state={state}"
    )
    
    return auth_url


def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
    """Exchange authorization code for access token."""
    client_id = EnvConfig.get_github_client_id()
    client_secret = EnvConfig.get_github_client_secret()
    
    if not client_id or not client_secret:
        return None
    
    response = requests.post(
        GITHUB_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Accept": "application/json"}
    )
    
    if response.status_code != 200:
        return None
    
    data = response.json()
    
    if "error" in data:
        print(f"GitHub OAuth error: {data.get('error_description', data['error'])}")
        return None
    
    return data


def get_github_user(access_token: str) -> Optional[Dict[str, Any]]:
    """Fetch authenticated user's GitHub profile."""
    response = requests.get(
        f"{GITHUB_API_BASE}/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    )
    
    if response.status_code != 200:
        return None
    
    return response.json()


def is_github_configured() -> bool:
    """Check if GitHub OAuth is configured in environment."""
    return bool(EnvConfig.get_github_client_id() and EnvConfig.get_github_client_secret())
