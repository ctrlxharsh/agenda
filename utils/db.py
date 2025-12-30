import psycopg2
from utils.env_config import get_db_connection_string
from contextlib import contextmanager

DB_CONNECTION_STRING = get_db_connection_string()
if not DB_CONNECTION_STRING:
    raise ValueError("DATABASE_URL not found in environment variables. Please check your .env file.")
@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
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
    """Asynchronously executes a query and returns results if requested."""
    return await asyncio.to_thread(execute_query, query, params, fetch_all, fetch_one)
