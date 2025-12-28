from utils.db import execute_query

def seed_friends_for_harsh():
    print("Seeding friends for 'harsh'...")
    
    # 1. Get harsh's ID
    res = execute_query("SELECT id FROM users WHERE username = 'harsh'", fetch_one=True)
    if not res:
        print("User 'harsh' not found! Please signup as 'harsh' first.")
        return
    
    harsh_id = res[0]
    print(f"Found 'harsh' with ID: {harsh_id}")
    
    # 2. Friends to add
    friends = ['alice', 'bob', 'eve']
    
    for f_name in friends:
        f_res = execute_query("SELECT id FROM users WHERE username = %s", (f_name,), fetch_one=True)
        if f_res:
            friend_id = f_res[0]
            
            # Add friend to harsh (idempotent via array logic or check)
            # Using simple update, assuming not already there or OK to overlap if set logic used
            # Postgres array_append adds even if exists, so we ideally check.
            # But let's use a robust query:
            
            q_add_to_harsh = """
            UPDATE users 
            SET collaborator_ids = array_append(COALESCE(collaborator_ids, '{}'), %s)
            WHERE id = %s AND NOT (COALESCE(collaborator_ids, '{}') @> ARRAY[%s]);
            """
            execute_query(q_add_to_harsh, (friend_id, harsh_id, friend_id))
            
            q_add_to_friend = """
            UPDATE users 
            SET collaborator_ids = array_append(COALESCE(collaborator_ids, '{}'), %s)
            WHERE id = %s AND NOT (COALESCE(collaborator_ids, '{}') @> ARRAY[%s]);
            """
            execute_query(q_add_to_friend, (harsh_id, friend_id, harsh_id))
            
            print(f"Linked 'harsh' <-> '{f_name}'")
        else:
            print(f"Friend '{f_name}' not found.")

if __name__ == "__main__":
    seed_friends_for_harsh()
