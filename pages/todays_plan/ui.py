
import streamlit as st
from streamlit_calendar import calendar
from datetime import datetime, date
from pages.todays_plan.logic import fetch_todays_items, generate_schedule_with_ai, update_task_times

def distinct_todays_plan_page():
    st.title("Today's AI Plan 🤖")
    
    if 'user' not in st.session_state or not st.session_state.user:
        st.error("Please login first.")
        return

    user_id = st.session_state.user['id']

    # --- Action Section ---
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("✨ Generate Plan", type="primary", use_container_width=True):
            with st.spinner("AI is thinking hard to schedule your day..."):
                # 1. Fetch Items
                items = fetch_todays_items(user_id)
                if not items:
                    st.warning("No tasks or meetings found for today! Enjoy your free time. 🎉")
                else:
                    # 2. Generate Schedule
                    schedule_updates = generate_schedule_with_ai(items)
                    
                    # 3. Update Database
                    if schedule_updates:
                        # Store for display
                        st.session_state['ai_schedule_reasoning'] = schedule_updates
                        
                        success = update_task_times(schedule_updates)
                        if success:
                            st.success("Plan generated and updated!")
                            st.rerun()
                        else:
                            st.error("Failed to update database.")
                    else:
                        # Could happen if AI fails or returns empty
                        st.warning("AI couldn't generate a schedule. check logs.")

    # --- Calendar View ---
    # Fetch latest data to display
    items = fetch_todays_items(user_id)
    
    calendar_events = []
    for item in items:
        # Only show items that have a start time assigned (scheduled)
        if item.get('start_time') and item.get('scheduled_date'):
            # Construct ISO datetime strings
            # item['scheduled_date'] is date object, item['start_time'] is time object
            start_dt = datetime.combine(item['scheduled_date'], item['start_time'])
            
            if item.get('end_time'):
                end_dt = datetime.combine(item['scheduled_date'], item['end_time'])
            else:
                # Default 1 hour if no end time, though logic should provide it
                from datetime import timedelta
                end_dt = start_dt + timedelta(hours=1)
                
            # Determine color based on status or priority
            color = "#3788d8" # default blue
            if item.get('status') == 'meeting':
                color = "#ff9f89" # reddish for meetings
            elif item.get('priority') == 'urgent':
                color = "#ff0000" # red for urgent
            
            calendar_events.append({
                "title": item['title'],
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "backgroundColor": color,
                "borderColor": color
            })

    calendar_options = {
        "headerToolbar": {
            "left": "",
            "center": "title",
            "right": ""
        },
        "initialView": "timeGridDay",
        "slotMinTime": "06:00:00",
        "slotMaxTime": "24:00:00",
        "allDaySlot": False,
        "height": "auto",
        "initialDate": datetime.now().strftime("%Y-%m-%d") 
    }
    
    # Custom CSS for modern look
    custom_css = """
        .fc-event { border-radius: 4px; }
        .fc-timegrid-slot { height: 40px !important; }
    """

    st.markdown("### Your Daily Schedule")
    calendar(
        events=calendar_events,
        options=calendar_options,
        custom_css=custom_css,
        key="todays_plan_calendar"
    )
    
    # --- Reasoning Panel ---
    if 'ai_schedule_reasoning' in st.session_state and st.session_state['ai_schedule_reasoning']:
        with st.expander("🤖 AI Reasoning (Why I changed things)", expanded=True):
            for update in st.session_state['ai_schedule_reasoning']:
                task_id = update.get('task_id')
                # Find task title from items list if possible, or just use ID
                task_title = next((i['title'] for i in items if i['task_id'] == task_id), f"Task #{task_id}")
                
                reason = update.get('reason', 'No reason provided')
                time_range = f"{update.get('start_time')} - {update.get('end_time')}"
                
                st.markdown(f"**{task_title}** ({time_range})")
                st.info(f"💡 {reason}")
    
    # Debug/List view below
    with st.expander("View Task List"):
        for item in items:
            status_icon = "✅" if item['status'] == 'done' else "📅" if item['scheduled_date'] else "📝"
            time_str = f"{item.get('start_time')} - {item.get('end_time')}" if item.get('start_time') else "Not scheduled"
            st.write(f"{status_icon} **{item['title']}** ({item['status']}) - {time_str}")

