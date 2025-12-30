import streamlit as st
from pages.login.logic import login_user, register_user

def distinct_login_page():
    with st.container(border=True):
        st.title("Welcome to AGENDA")
        st.markdown("### Agent for Goal Execution, Navigation & Day Allocation")
        
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")
                
                if submitted:
                    if login_user(username, password):
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
        
        with tab2:
            with st.form("signup_form"):
                new_user = st.text_input("Username")
                new_pass = st.text_input("Password", type="password")
                email = st.text_input("Email")
                full_name = st.text_input("Full Name")
                signup_submitted = st.form_submit_button("Sign Up")
                
                if signup_submitted:
                    if register_user(new_user, new_pass, email, full_name):
                        st.success("Account created! Please log in.")
                    else:
                        st.error("Username or Email might already represent an account.")


