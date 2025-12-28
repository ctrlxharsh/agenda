from utils.db import execute_query

def verify_credentials(username, password):
    """
    Verifies user credentials against the database using pgcrypto.
    Returns the user dictionary if valid, None otherwise.
    """
    query = """
    SELECT id, username, full_name, email, is_admin, collaborator_ids
    FROM users 
    WHERE username = %s 
    AND password_hash = crypt(%s, password_hash);
    """
    result = execute_query(query, (username, password), fetch_one=True)
    
    if result:
        # Map tuple to dictionary based on query order
        return {
            "id": result[0],
            "username": result[1],
            "full_name": result[2],
            "email": result[3],
            "is_admin": result[4],
            "collaborator_ids": result[5] if result[5] else []
        }
    return None

def create_user(username, password, email, full_name):
    """
    Creates a new user with hashed password.
    """
    query = """
    INSERT INTO users (username, password_hash, email, full_name)
    VALUES (%s, crypt(%s, gen_salt('bf')), %s, %s)
    RETURNING id;
    """
    try:
        result = execute_query(query, (username, password, email, full_name), fetch_one=True)
        return result[0]
    except Exception as e:
        print(f"Error creating user: {e}")
        return None
