
import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db import execute_query_async

async def find_harsh():
    print("Searching for Harsh...")
    query = "SELECT id, full_name, email, username FROM users WHERE full_name ILIKE %s OR username ILIKE %s"
    result = await execute_query_async(query, ('%Harsh%', '%Harsh%'), fetch_all=True)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(find_harsh())
