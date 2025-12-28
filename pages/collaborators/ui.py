import streamlit as st
from pages.home.logic import search_users, send_request, get_pending_requests, handle_request, get_my_collaborators, remove_collaborator

def distinct_collaborators_page():
    # Only Main Content here, sidebar handled in app.py or parent
    st.title("Manage Collaborators")
    
    tab1, tab2, tab3 = st.tabs(["My Team", "Add Collaborator", "Pending Requests"])
    
    current_user = st.session_state.user

    # --- My Team ---
    with tab1:
        st.subheader("Your Team")
        collaborators = get_my_collaborators()
        if not collaborators:
            st.info("You haven't added any collaborators yet.")
        else:
            for col in collaborators:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.write(f"**{col['username']}**")
                        st.caption(f"Email: {col['email']}")
                        if col['full_name']:
                            st.caption(f"Name: {col['full_name']}")
                    with c2:
                        if st.button("Remove", key=f"rem_page_{col['id']}"):
                            remove_collaborator(col['id'])

    # --- Add Collaborator ---
    with tab2:
        st.subheader("Find People")
        search_term = st.text_input("Search by username or email", key="search_collab")
        if search_term:
            results = search_users(search_term)
            if not results:
                st.info("No users found.")
            else:
                for res in results:
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.write(f"**{res['username']}**")
                            st.caption(res['email'])
                        with c2:
                            # Check if already collaborator
                            if res['id'] in current_user.get('collaborator_ids', []):
                                st.success("Added")
                            else:
                                if st.button("Add", key=f"add_page_{res['id']}"):
                                    send_request(res['id'])
    
    # --- Pending Requests ---
    with tab3:
        st.subheader("Incoming Requests")
        requests = get_pending_requests()
        if not requests:
            st.info("No pending requests.")
        else:
            for req in requests:
                with st.container(border=True):
                    st.write(f"Request from: **{req['sender_username']}** ({req['sender_email']})")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Accept", key=f"acc_page_{req['request_id']}"):
                             handle_request(req['request_id'], req['sender_id'], 'accept')
                    with c2:
                        if st.button("Reject", key=f"rej_page_{req['request_id']}"):
                             handle_request(req['request_id'], None, 'reject')
