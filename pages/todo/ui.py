import streamlit as st
from utils.db import execute_query
from datetime import datetime, timedelta

def get_all_work_items(user_id):
    """Fetch all active items (tasks, todos, meetings) for the user."""
    # We fetch everything that is NOT completed
    query = """
    SELECT task_id, title, description, priority, due_date, category, status, created_at
    FROM tasks
    WHERE user_id = %s AND status != 'completed'
    """
    return execute_query(query, (user_id,), fetch_all=True)

def mark_task_complete(task_id):
    """Mark a task as completed in the database."""
    query = "UPDATE tasks SET status = 'completed', updated_at = NOW() WHERE task_id = %s"
    execute_query(query, (task_id,))

def distinct_todo_page():
    st.title("🧠 Workboard")
    st.caption("Your overview of all ongoing work.")
    
    if "user" not in st.session_state or not st.session_state.user:
        st.error("Please login to view your workboard.")
        return

    user_id = st.session_state.user['id']
    
    # Refresh & Filters
    col_filter1, col_filter2, col_refresh = st.columns([1, 1, 1])
    with col_filter1:
        filter_priority = st.selectbox("Priority", ["All", "Urgent", "High", "Medium", "Low"], key="filter_p")
    with col_filter2:
        filter_date = st.selectbox("Date", ["All", "Today", "This Week", "Overdue", "Custom Range"], key="filter_d")
    with col_refresh:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) # Spacer for label alignment
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Custom Date Inputs
    custom_start_date = None
    custom_end_date = None
    if filter_date == "Custom Range":
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            custom_start_date = st.date_input("Start Date", value=datetime.now().date())
        with c_col2:
            custom_end_date = st.date_input("End Date", value=datetime.now().date())
        st.markdown("---")
    else:
        st.markdown("---")
    
    # Fetch all items
    items = get_all_work_items(user_id)
    
    if not items:
        st.info("🎉 Your workboard is empty! Ask the AI assistant to add tasks, meetings, or reminders.")
        return

    # Categorize items
    tasks = []
    todos = []
    meetings = []

    today = datetime.now().date()
    # Logic for "All" - User requested "least 6 months up to today". 
    # Interpreting as: Exclude very old items (> 6 months ago), preserve future.
    six_months_ago = today - timedelta(days=180)



    for item in items:
        # Unpack
        # task_id, title, description, priority, due_date, category, status, created_at
        i_dict = {
            'id': item[0], 'title': item[1], 'description': item[2], 
            'priority': item[3], 'due_date': item[4], 'category': item[5], 
            'status': item[6], 'created_at': item[7]
        }
        
        # Apply Filters
        # 1. Priority
        if filter_priority != "All" and i_dict['priority'].lower() != filter_priority.lower():
            continue
            
        # 2. Category - REMOVED
            
        # 3. Date Filter
        item_date = i_dict['due_date'].date() if i_dict['due_date'] else (i_dict['created_at'].date() if i_dict['created_at'] else None)
        
        if not item_date:
            # If no date, usually keep it unless precise filter is on
            if filter_date in ["Today", "This Week", "Overdue", "Custom Range"]:
                continue
        else:
            if filter_date == "Today":
                if item_date != today: continue
            elif filter_date == "This Week":
                # Simple logic: within next 7 days or same ISO week
                # Let's use next 7 days + today
                if not (today <= item_date <= today + timedelta(days=7)): continue
            elif filter_date == "Overdue":
                if item_date >= today: continue
            elif filter_date == "Custom Range":
                if custom_start_date and custom_end_date:
                    if not (custom_start_date <= item_date <= custom_end_date): continue
            elif filter_date == "All":
                # "Least 6 months" logic
                # Keep if item is newer than 6 months ago OR is in the future
                if item_date < six_months_ago: continue

        status = i_dict['status']
        
        if status == 'meeting':
            meetings.append(i_dict)
        elif status == 'task':
            tasks.append(i_dict)
        elif status == 'todo':
            todos.append(i_dict)
        else:
            # Fallback
            todos.append(i_dict)

    # Sorting Logic helper
    priority_map = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    
    def get_priority_val(x):
        return priority_map.get(x['priority'].lower(), 4)
    
    # 1. Tasks: Deadline (Due Date) -> Progress (N/A) -> Priority
    tasks.sort(key=lambda x: (x['due_date'] or datetime.max, get_priority_val(x)))
    
    # 2. To-Do: Priority -> Date (Created/Due)
    todos.sort(key=lambda x: (get_priority_val(x), x['due_date'] or x['created_at'] or datetime.max))
    
    # 3. Meetings: Upcoming Date & Time
    meetings.sort(key=lambda x: x['due_date'] or datetime.max)
    

    # Display Functions
    def render_item(item, show_priority=True, show_date=True, show_desc_inline=False):
        p_emoji = "⚪"
        if item['priority'] == 'urgent': p_emoji = "🔴"
        elif item['priority'] == 'high': p_emoji = "🟠"
        elif item['priority'] == 'medium': p_emoji = "🔵"
            
        due_str = ""
        if item['due_date']:
            due_str = item['due_date'].strftime('%b %d')
            if item['status'] == 'meeting':
                 due_str = item['due_date'].strftime('%b %d, %H:%M')
        
        col1, col2, col3 = st.columns([0.7, 0.2, 0.1])
        with col1:
            title_text = f"{p_emoji} {item['title']}" if show_priority else item['title']
            
            # Additional visual cues
            if item['category']:
                title_text += f" <span style='color:grey; font-size:0.8em'>({item['category']})</span>"
                
            st.markdown(title_text, unsafe_allow_html=True)
            if show_desc_inline and item['description']:
                 st.caption(item['description'])
                 
        with col2:
            if show_date and due_str:
                st.caption(f"📅 {due_str}")
        with col3:
             if st.button("✅", key=f"done_{item['id']}", help="Mark as complete"):
                mark_task_complete(item['id'])
                st.rerun()

    # SECTION 1: TASKS (Work/project based)
    with st.expander(f"📂 Tasks ({len(tasks)})", expanded=True):
        if tasks:
            with st.container(border=True):
                for t in tasks:
                    render_item(t, show_priority=True, show_date=True)
        else:
            st.caption("No project tasks.")

    # SECTION 2: TO-DO (Quick actions)
    with st.expander(f"📝 To-Do ({len(todos)})", expanded=True):
        if todos:
            with st.container(border=True):
                for t in todos:
                    render_item(t, show_priority=True, show_date=True)
        else:
            st.caption("No quick to-dos.")

    # SECTION 3: MEETINGS
    with st.expander(f"📅 Meetings ({len(meetings)})", expanded=True):
        if meetings:
            with st.container(border=True):
                for m in meetings:
                    render_item(m, show_priority=False, show_date=True, show_desc_inline=True)
        else:
            st.caption("No upcoming meetings.")
