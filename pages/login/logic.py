import streamlit as st
from pages.login.data import verify_credentials, create_user

def login_user(username, password):
    """
    Authenticates user and updates session state.
    """
    user = verify_credentials(username, password)
    if user:
        st.session_state.authenticated = True
        st.session_state.user = user
        return True
    return False

def register_user(username, password, email, full_name):
    """
    Registers a new user.
    """
    user_id = create_user(username, password, email, full_name)
    return user_id is not None
