from utils.db import execute_query
import sys

def test_db_flow():
    print("Testing DB Connection and pgcrypto...")
    try:
        # 1. Test pgcrypto
        res = execute_query("SELECT crypt('test', gen_salt('bf'));", fetch_one=True)
        print(f"pgcrypto check: {res[0] if res else 'FAILED'}")
        
        # 2. Check recent users
        users = execute_query("SELECT id, username, email, password_hash FROM users ORDER BY created_at DESC LIMIT 5;", fetch_all=True)
        print("\nRecent Users:")
        for u in users:
            print(f"ID: {u[0]}, User: {u[1]}, Email: {u[2]}, HashStart: {u[3][:10]}...")

        # 3. Test verification manually for 'admin' (since we know it exists)
        # Note: We need to handle special chars in command line if we were passing args, but here hardcoded.
        print("\nVerifying 'admin' with 'admin123'...")
        q_verify = "SELECT id FROM users WHERE username = 'admin' AND password_hash = crypt('admin123', password_hash);"
        v_res = execute_query(q_verify, fetch_one=True)
        print(f"Verification result: {v_res}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_db_flow()
