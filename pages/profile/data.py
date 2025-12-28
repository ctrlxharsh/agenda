from utils.db import execute_query

def update_user_details_db(user_id, email, full_name):
    query = """
    UPDATE users 
    SET email = %s, full_name = %s
    WHERE id = %s
    """
    execute_query(query, (email, full_name, user_id))

def update_password_db(user_id, new_password):
    query = """
    UPDATE users 
    SET password_hash = crypt(%s, gen_salt('bf'))
    WHERE id = %s
    """
    execute_query(query, (new_password, user_id))

def get_user_by_id_db(user_id):
    query = "SELECT id, username, full_name, email FROM users WHERE id = %s"
    res = execute_query(query, (user_id,), fetch_one=True)
    if res:
        return {"id": res[0], "username": res[1], "full_name": res[2], "email": res[3]}
    return None
