import psycopg2
import os
from contextlib import contextmanager

# Connection string (In a real app, use environment variables or st.secrets)
DB_CONNECTION_STRING = "postgresql://neondb_owner:npg_EXNMFbcp61KB@ep-purple-butterfly-a1ghjpd1-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Yields a cursor and handles commit/rollback automatically.
    """
    conn = None
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def execute_query(query, params=None, fetch_all=False, fetch_one=False):
    """
    Executes a query and returns results if requested.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch_all:
                return cur.fetchall()
            if fetch_one:
                return cur.fetchone()
            conn.commit()

import asyncio

async def execute_query_async(query, params=None, fetch_all=False, fetch_one=False):
    """
    Asynchronously executes a query and returns results if requested.
    Wraps the synchronous execute_query in a thread.
    """
    return await asyncio.to_thread(execute_query, query, params, fetch_all, fetch_one)
