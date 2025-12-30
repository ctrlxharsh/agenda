import streamlit as st
from pages.login.logic import login_user, register_user

def distinct_login_page():
    # Two-column layout: Image on left, Login form on right
    left_col, right_col = st.columns([1, 2], gap="large")
    
    # Left Column - Image
    with left_col:
        st.image("assets/agenda.png", use_container_width=True)
        # Add some branding text below the image
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h2 style='color: #667eea; margin-bottom: 10px;'>🚀 AGENDA</h2>
            <p style='color: #718096; font-size: 14px;'>
                Your intelligent assistant for productivity and goal management.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Right Column - Login/Signup Form
    with right_col:
        with st.container(border=True):
            st.title("Welcome Back!")
            st.markdown("### Agent for Goal Execution, Navigation & Day Allocation")
            st.markdown("---")
            
            tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
            
            with tab1:
                st.markdown("##### Enter your credentials to continue")
                with st.form("login_form"):
                    username = st.text_input("Username", placeholder="Enter your username")
                    password = st.text_input("Password", type="password", placeholder="Enter your password")
                    submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
                    
                    if submitted:
                        if login_user(username, password):
                            st.success("Logged in successfully!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
            
            with tab2:
                st.markdown("##### Create a new account")
                with st.form("signup_form"):
                    new_user = st.text_input("Username", placeholder="Choose a username")
                    new_pass = st.text_input("Password", type="password", placeholder="Create a password")
                    email = st.text_input("Email", placeholder="your.email@example.com")
                    full_name = st.text_input("Full Name", placeholder="John Doe")
                    signup_submitted = st.form_submit_button("Sign Up", use_container_width=True, type="primary")
                    
                    if signup_submitted:
                        if register_user(new_user, new_pass, email, full_name):
                            st.success("Account created! Please log in.")
                        else:
                            st.error("Username or Email might already represent an account.")