
import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agenda.utils.db import execute_query_async

async def save_view_def():
    query = "SELECT pg_get_viewdef('upcoming_meetings', true)"
    try:
        result = await execute_query_async(query, fetch_one=True)
        with open('agenda/current_view_def.sql', 'w') as f:
            f.write(result[0])
        print("Saved view definition to agenda/current_view_def.sql")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(save_view_def())
