import streamlit as st

def distinct_home_page():
    # Main Dashboard Content
    with st.container(border=True):
        st.title(f"Welcome, {st.session_state.user['username']}")
        st.subheader("Projects & Tasks")
        st.info("Tasks dashboard coming soon...")

