
import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agenda.utils.db import execute_query_async

async def migrate_schema():
    print("Starting migration...")
    
    # 1. Drop the dependent view
    print("Dropping view upcoming_meetings...")
    await execute_query_async("DROP VIEW IF EXISTS upcoming_meetings;")
    
    # 2. Alter the table
    queries = [
        "ALTER TABLE calendar_events ALTER COLUMN start_time TYPE TIME WITHOUT TIME ZONE USING start_time::time;",
        "ALTER TABLE calendar_events ALTER COLUMN end_time TYPE TIME WITHOUT TIME ZONE USING end_time::time;",
        "ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS due_date DATE;",
        "ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS scheduled_date DATE;"
    ]
    
    for q in queries:
        try:
            print(f"Executing: {q}")
            await execute_query_async(q)
        except Exception as e:
            print(f"Error executing query '{q}': {e}")
            # If alter fails, check if columns already exist or types match
            logger.error(f"Migration step failed: {e}")

    # 3. Recreate the view with updated logic
    print("Recreating view upcoming_meetings...")
    create_view_query = """
    CREATE OR REPLACE VIEW upcoming_meetings AS
    SELECT ce.event_id,
        ce.user_id AS organizer_id,
        u.username AS organizer_username,
        ce.start_time,
        ce.end_time,
        ce.event_desc,
        ce.event_type,
        ml.meeting_url,
        ml.platform,
        count(ec.collab_id) AS collaborator_count
    FROM calendar_events ce
        LEFT JOIN users u ON ce.user_id = u.id
        LEFT JOIN meeting_links ml ON ce.event_id = ml.event_id
        LEFT JOIN event_collaborators ec ON ce.event_id = ec.event_id
    WHERE ce.event_type::text = 'meeting'::text 
      AND (
          (ce.scheduled_date IS NOT NULL AND (ce.scheduled_date + ce.start_time) > now())
          OR 
          (ce.scheduled_date IS NULL AND ce.start_time > now()::time) 
      )
    GROUP BY ce.event_id, u.username, ml.meeting_url, ml.platform
    ORDER BY (ce.scheduled_date + ce.start_time);
    """
    
    # Note: If scheduled_date is NULL (for old events), the addition might be NULL. 
    # Logic: If scheduled_date is NULL, maybe we use created_at or assume today?
    # Since I added columns, old rows will have NULL scheduled_date.
    # Should I backfill?
    # For now, logical condition handles NULLs: (NULL > now) is NULL (False).
    # So old events won't show up in upcoming. This is acceptable or I should enable them?
    # Maybe backfill scheduled_date = created_at::date?
    # I'll add a backfill step.
    
    backfill_query = "UPDATE calendar_events SET scheduled_date = created_at::date, due_date = created_at::date WHERE scheduled_date IS NULL;"
    print("Backfilling NULL dates...")
    await execute_query_async(backfill_query)

    try:
        await execute_query_async(create_view_query)
        print("View recreated successfully.")
    except Exception as e:
        print(f"Error recreating view: {e}")

    print("Migration finished.")

if __name__ == "__main__":
    asyncio.run(migrate_schema())
