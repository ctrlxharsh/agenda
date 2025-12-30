import streamlit as st
from utils.db import execute_query
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
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = ""

def main():
    # Attempt session recovery from OAuth state
    if not st.session_state.authenticated:
        qp = st.query_params
        if "code" in qp and "state" in qp:
            try:
                state_val = qp["state"]
                if isinstance(state_val, list): state_val = state_val[0]
                
                if "|" in state_val:
                    action, uid = state_val.split("|", 1)
                    if action in ["github_auth", "calendar", "gmail"]:
                        # Fetch user
                        user_data = execute_query(
                            "SELECT id, username, email, full_name FROM users WHERE id = %s",
                            (int(uid),), fetch_one=True
                        )
                        if user_data:
                            st.session_state.user = {
                                "id": user_data[0],
                                "username": user_data[1],
                                "email": user_data[2],
                                "full_name": user_data[3]
                            }
                            st.session_state.authenticated = True
                            print(f"DEBUG: Recovered session for user {user_data[1]}")
            except Exception as e:
                print(f"Recovery Error: {e}")

    if not st.session_state.authenticated:
        distinct_login_page()
    else:
        # Auto-route to Authorization page if OAuth callback is detected
        # Check standard query params location (Streamlit >= 1.30)
        query_params = st.query_params
        
        if "code" in query_params and "state" in query_params:
            state_val = query_params["state"]
            
            # Handle list if older streamlit version or unexpected behavior
            if isinstance(state_val, list):
                state_val = state_val[0]
            
            # Handle composite state "action|user_id"
            action = state_val.split('|')[0] if '|' in state_val else state_val
            
            if action in ["github_auth", "calendar", "gmail"]:
                st.session_state.current_page = "Authorization"

        # Navigation State
        if "current_page" not in st.session_state:
            st.session_state.current_page = "Dashboard"

        with st.sidebar:
            st.markdown(f"### Welcome {st.session_state.user['username']} 👋")
            st.title("Agenda")
            
            # Navigation Buttons
            if st.button("Dashboard", type="primary" if st.session_state.current_page == "Dashboard" else "secondary", width="stretch"):
                st.session_state.current_page = "Dashboard"
                st.rerun()
            
            if st.button("Collaborators", type="primary" if st.session_state.current_page == "Collaborators" else "secondary", width="stretch"):
                st.session_state.current_page = "Collaborators"
                st.rerun()

            if st.button("Profile", type="primary" if st.session_state.current_page == "Profile" else "secondary", width="stretch"):
                st.session_state.current_page = "Profile"
                st.rerun()

            if st.button("Calendar", type="primary" if st.session_state.current_page == "Calendar" else "secondary", width="stretch"):
                st.session_state.current_page = "Calendar"
                st.rerun()

            if st.button("Today's Plan", type="primary" if st.session_state.current_page == "TodaysPlan" else "secondary", width="stretch"):
                st.session_state.current_page = "TodaysPlan"
                st.rerun()

            if st.button("Workboard", type="primary" if st.session_state.current_page == "Workboard" else "secondary", width="stretch"):
                st.session_state.current_page = "Workboard"
                st.rerun()

            if st.button("Authorization", type="primary" if st.session_state.current_page == "Authorization" else "secondary", width="stretch"):
                st.session_state.current_page = "Authorization"
                st.rerun()

            st.markdown("### Settings")
            
            # API Key Input - Using shadowing pattern for better persistence
            if "openai_api_key" not in st.session_state:
                st.session_state.openai_api_key = ""
            if "openai_model" not in st.session_state:
                st.session_state.openai_model = "gpt-5-mini"
                
            # Model Selection
            st.selectbox(
                "AI Model",
                ["gpt-5.2", "gpt-5-mini", "gpt-5-nano", "gpt-4o-mini", "gpt-4-turbo"],
                key="openai_model",
                help="Select the OpenAI model to use."
            )
            
            current_key = st.text_input(
                "OpenAI API Key", 
                value=st.session_state.openai_api_key,
                type="password", 
                help="Enter your OpenAI API key here"
            )
            
            # Immediately update session state
            st.session_state.openai_api_key = current_key
            
            # Status Indicator
            key_val = st.session_state.openai_api_key.strip()
            if key_val:
                if key_val.startswith("sk-"):
                    st.caption(f"✅ Key saved ({key_val[:3]}...{key_val[-4:]})")
                else:
                    st.caption("⚠️ Key format might be invalid")
            else:
                st.caption("ℹ️ Please enter key to enable AI features")

            st.divider()
            if st.button("Logout", width="stretch"):
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
        elif st.session_state.current_page == "TodaysPlan":
            from pages.todays_plan.ui import distinct_todays_plan_page
            distinct_todays_plan_page()
        elif st.session_state.current_page == "Workboard":
            from pages.todo.ui import distinct_todo_page
            distinct_todo_page()
        elif st.session_state.current_page == "Authorization":
            from pages.authorization.ui import distinct_authorization_page
            distinct_authorization_page()

if __name__ == "__main__":
    main()
