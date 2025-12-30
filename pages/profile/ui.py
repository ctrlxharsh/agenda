import streamlit as st
from pages.profile.logic import update_profile, update_password

def distinct_profile_page():
    st.title("My Profile")
    
    current_user = st.session_state.user
    
    with st.container(border=True):
        st.subheader("Personal Details")
        
        new_email = st.text_input("Email", value=current_user.get('email', ''))
        new_name = st.text_input("Full Name", value=current_user.get('full_name', ''))
        
        if st.button("Save Details"):
            update_profile(new_email, new_name)

    st.divider()

    with st.container(border=True):
        st.subheader("Security")
        st.info("Enter a new password to change it.")
        
        new_pass = st.text_input("New Password", type="password")
        confirm_pass = st.text_input("Confirm New Password", type="password")
        
        if st.button("Update Password"):
            if new_pass and new_pass == confirm_pass:
                update_password(new_pass)
            elif new_pass != confirm_pass:
                st.error("Passwords do not match.")
            else:
                st.warning("Please enter a password.")
