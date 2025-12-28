import streamlit as st
from streamlit_calendar import calendar
from pages.calendar.logic import get_calendar_service, auth_flow_step, get_events_by_range
from datetime import datetime, timedelta

def distinct_calendar_page():
    st.title("My Calendar")
    user_id = st.session_state.user['id']
    
    # 1. Check App Config
    import os
    if not os.path.exists("client_secret.json"):
        st.error("Google Login is not configured.")
        st.info("Admin: Please place `client_secret.json` in the app root to enable this feature.")
        return

    # 2. Check User Auth
    service = get_calendar_service(user_id)
    
    if not service:
        st.markdown("#### Connect your Calendar")
        st.write("Link your Google account to manage your schedule directly from Agenda.")
        auth_flow_step()
    else:
        st.success("Connected to Google Calendar")
        
        # --- Date Range Logic (Wide Window) ---
        # Strategy: Fetch 6 months back and 6 months forward to allow smooth navigation
        # without needing frequent server callbacks (which can be flaky).
        
        now = datetime.utcnow()
        start_date = now - timedelta(days=180) # ~6 months ago
        end_date = now + timedelta(days=180)   # ~6 months future
        
        # 3. Fetch Events for Wide Range
        try:
            events = get_events_by_range(service, start_date.isoformat() + "Z", end_date.isoformat() + "Z")
            
            calendar_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                calendar_events.append({
                    "title": event.get('summary', 'No Title'),
                    "start": start,
                    "end": end,
                    # Optional: Add colors or other props
                })
            
            # 4. Render Calendar
            calendar_options = {
                "headerToolbar": {
                    "left": "today prev,next",
                    "center": "title",
                    "right": "dayGridMonth,timeGridWeek,timeGridDay"
                },
                "initialView": "dayGridMonth",
            }
            
            custom_css = """
                .fc-event-past { opacity: 0.8; }
                .fc-event-time { font-style: italic; }
                .fc-event-title { font-weight: 700; }
                .fc-toolbar-title { font-size: 1.2rem; }
            """
            
            # Render (Client-side navigation for loaded events)
            calendar(
                events=calendar_events, 
                options=calendar_options, 
                custom_css=custom_css, 
                key="google_cal"
            )
            
            with st.expander("Raw Data (Debug)"):
                st.write(f"Loaded {len(events)} events from Google (Scanning +/- 6 months).")

        except Exception as e:
            st.error(f"Failed to fetch events: {e}")
            st.info("Token might be expired. Re-connecting...")
            auth_flow_step()

        except Exception as e:
            st.error(f"Failed to fetch events: {e}")
            st.info("Token might be expired. Re-connecting...")
            auth_flow_step()
