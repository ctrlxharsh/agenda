
import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agenda.utils.db import execute_query_async

async def get_view_def():
    query = "SELECT pg_get_viewdef('upcoming_meetings', true)"
    try:
        result = await execute_query_async(query, fetch_one=True)
        print(f"View Definition:\n{result[0]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(get_view_def())
