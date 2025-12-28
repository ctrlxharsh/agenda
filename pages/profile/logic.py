import streamlit as st
from pages.profile.data import update_user_details_db, update_password_db, get_user_by_id_db

def update_profile(email, full_name):
    user_id = st.session_state.user['id']
    try:
        update_user_details_db(user_id, email, full_name)
        # Update session state to reflect changes immediately
        st.session_state.user['email'] = email
        st.session_state.user['full_name'] = full_name
        st.success("Profile updated successfully!")
    except Exception as e:
        st.error(f"Failed to update profile: {e}")

def update_password(new_password):
    user_id = st.session_state.user['id']
    try:
        update_password_db(user_id, new_password)
        st.success("Password changed successfully!")
    except Exception as e:
        st.error(f"Failed to change password: {e}")
