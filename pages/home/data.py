from utils.db import execute_query

def search_users_db(search_term, current_user_id):
    query = """
    SELECT id, username, email FROM users
    WHERE (username ILIKE %s OR email ILIKE %s)
    AND id != %s
    LIMIT 10;
    """
    term = f"%{search_term}%"
    return execute_query(query, (term, term, current_user_id), fetch_all=True)

def create_request_db(sender_id, receiver_id):
    query = """
    INSERT INTO collaboration_requests (sender_id, receiver_id)
    VALUES (%s, %s)
    ON CONFLICT (sender_id, receiver_id) DO NOTHING;
    """
    execute_query(query, (sender_id, receiver_id))

def get_incoming_requests_db(user_id):
    query = """
    SELECT cr.request_id, u.username, u.email, u.id
    FROM collaboration_requests cr
    JOIN users u ON cr.sender_id = u.id
    WHERE cr.receiver_id = %s AND cr.status = 'pending';
    """
    return execute_query(query, (user_id,), fetch_all=True)

def accept_request_db(request_id, sender_id, receiver_id):
    update_q = "UPDATE collaboration_requests SET status = 'accepted' WHERE request_id = %s"
    execute_query(update_q, (request_id,))

    # Using array_append and COALESCE to handle nulls
    add_q = """
    UPDATE users 
    SET collaborator_ids = array_append(COALESCE(collaborator_ids, '{}'), %s)
    WHERE id = %s
    """
    execute_query(add_q, (sender_id, receiver_id))

    execute_query(add_q, (receiver_id, sender_id))

def reject_request_db(request_id):
    query = "UPDATE collaboration_requests SET status = 'rejected' WHERE request_id = %s"
    execute_query(query, (request_id,))

def get_collaborators_info_db(user_ids):
    if not user_ids:
        return []
    query = "SELECT id, username, email, full_name FROM users WHERE id = ANY(%s)"
    return execute_query(query, (user_ids,), fetch_all=True)

def remove_collaborator_db(user_id, collaborator_id):
    query = """
    UPDATE users 
    SET collaborator_ids = array_remove(collaborator_ids, %s)
    WHERE id = %s
    """
    execute_query(query, (collaborator_id, user_id))
    execute_query(query, (user_id, collaborator_id))
