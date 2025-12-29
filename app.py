import streamlit as st
from pages.login.ui import distinct_login_page
# from pages.home.ui import distinct_home_page # Deferred import to avoid circular dependency or early load errors if not ready

# Set page config
st.set_page_config(
    page_title="AGENDA",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("styles/main.css")

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None

def main():
    if not st.session_state.authenticated:
        distinct_login_page()
    else:
        # Navigation State
        if "current_page" not in st.session_state:
            st.session_state.current_page = "Dashboard"

        with st.sidebar:
            st.markdown(f"### Welcome {st.session_state.user['username']} 👋")
            st.title("Agenda")
            
            # Navigation Buttons
            if st.button("Dashboard", type="primary" if st.session_state.current_page == "Dashboard" else "secondary", use_container_width=True):
                st.session_state.current_page = "Dashboard"
                st.rerun()
            
            if st.button("Collaborators", type="primary" if st.session_state.current_page == "Collaborators" else "secondary", use_container_width=True):
                st.session_state.current_page = "Collaborators"
                st.rerun()

            if st.button("Profile", type="primary" if st.session_state.current_page == "Profile" else "secondary", use_container_width=True):
                st.session_state.current_page = "Profile"
                st.rerun()

            if st.button("Calendar", type="primary" if st.session_state.current_page == "Calendar" else "secondary", use_container_width=True):
                st.session_state.current_page = "Calendar"
                st.rerun()

            if st.button("Workboard", type="primary" if st.session_state.current_page == "Workboard" else "secondary", use_container_width=True):
                st.session_state.current_page = "Workboard"
                st.rerun()

            if st.button("Authorization", type="primary" if st.session_state.current_page == "Authorization" else "secondary", use_container_width=True):
                st.session_state.current_page = "Authorization"
                st.rerun()

            st.divider()
            if st.button("Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user = None
                st.rerun()

        # Render Page
        if st.session_state.current_page == "Dashboard":
            from pages.home.ui import distinct_home_page
            distinct_home_page()
        elif st.session_state.current_page == "Collaborators":
            from pages.collaborators.ui import distinct_collaborators_page
            distinct_collaborators_page()
        elif st.session_state.current_page == "Profile":
            from pages.profile.ui import distinct_profile_page
            distinct_profile_page()
        elif st.session_state.current_page == "Calendar":
            from pages.calendar.ui import distinct_calendar_page
            distinct_calendar_page()
        elif st.session_state.current_page == "Workboard":
            from pages.todo.ui import distinct_todo_page
            distinct_todo_page()
        elif st.session_state.current_page == "Authorization":
            from pages.authorization.ui import distinct_authorization_page
            distinct_authorization_page()

if __name__ == "__main__":
    main()
