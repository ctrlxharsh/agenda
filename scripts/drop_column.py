
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db import execute_query

def drop_column():
    print("Dropping 'meeting_link' column from 'calendar_events' table...")
    try:
        query = "ALTER TABLE calendar_events DROP COLUMN IF EXISTS meeting_link;"
        execute_query(query)
        print("✅ Column dropped successfully!")
    except Exception as e:
        print(f"❌ Failed to drop column: {e}")

if __name__ == "__main__":
    drop_column()
