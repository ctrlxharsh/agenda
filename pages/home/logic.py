import streamlit as st
from pages.home.data import (
    search_users_db, create_request_db, get_incoming_requests_db, 
    accept_request_db, reject_request_db, get_collaborators_info_db
)

def search_users(term):
    if not term:
        return []
    current_id = st.session_state.user['id']
    results = search_users_db(term, current_id)
    # Map to dicts
    return [{"id": r[0], "username": r[1], "email": r[2]} for r in results]

def send_request(receiver_id):
    current_id = st.session_state.user['id']
    create_request_db(current_id, receiver_id)
    st.success("Request sent!")

def get_pending_requests():
    current_id = st.session_state.user['id']
    results = get_incoming_requests_db(current_id)
    return [{"request_id": r[0], "sender_username": r[1], "sender_email": r[2], "sender_id": r[3]} for r in results]

def handle_request(request_id, sender_id, action):
    current_id = st.session_state.user['id']
    if action == 'accept':
        accept_request_db(request_id, sender_id, current_id)
        st.success("Collaborator added!")
        # Update session state to reflect new collaborator immediately (optional, or rely on rerun)
        if st.session_state.user.get('collaborator_ids') is None:
             st.session_state.user['collaborator_ids'] = []
        st.session_state.user['collaborator_ids'].append(sender_id)
    else:
        reject_request_db(request_id)
        st.info("Request rejected.")
    st.rerun()

def get_my_collaborators():
    collab_ids = st.session_state.user.get('collaborator_ids', [])
    if not collab_ids:
        return []
    results = get_collaborators_info_db(collab_ids)
    return [{"id": r[0], "username": r[1], "email": r[2], "full_name": r[3]} for r in results]

def remove_collaborator(target_id):
    current_id = st.session_state.user['id']
    from pages.home.data import remove_collaborator_db # Local import to match style/avoid circular depending on top level
    remove_collaborator_db(current_id, target_id)
    # Update local session state
    if target_id in st.session_state.user.get('collaborator_ids', []):
        st.session_state.user['collaborator_ids'].remove(target_id)
    st.success("Collaborator removed.")
    st.rerun()
