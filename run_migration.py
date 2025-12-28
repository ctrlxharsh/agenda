"""
Run database migration for enhanced workflow
"""
from utils.db import execute_query

def run_migration():
    print("Starting database migration...")
    
    # 1. Create event_collaborators table
    print("\n1. Creating event_collaborators table...")
    execute_query("""
        CREATE TABLE IF NOT EXISTS event_collaborators (
            collab_id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES calendar_events(event_id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status VARCHAR(20) DEFAULT 'pending',
            added_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(event_id, user_id)
        )
    """)
    
    execute_query("""
        CREATE INDEX IF NOT EXISTS idx_event_collaborators_event_id ON event_collaborators(event_id)
    """)
    
    execute_query("""
        CREATE INDEX IF NOT EXISTS idx_event_collaborators_user_id ON event_collaborators(user_id)
    """)
    print("✓ event_collaborators table created")
    
    # 2. Create meeting_links table
    print("\n2. Creating meeting_links table...")
    execute_query("""
        CREATE TABLE IF NOT EXISTS meeting_links (
            link_id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES calendar_events(event_id) ON DELETE CASCADE,
            platform VARCHAR(50) DEFAULT 'google_meet',
            meeting_code VARCHAR(255),
            meeting_url TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(event_id)
        )
    """)
    
    execute_query("""
        CREATE INDEX IF NOT EXISTS idx_meeting_links_event_id ON meeting_links(event_id)
    """)
    print("✓ meeting_links table created")
    
    # 3. Update calendar_events table
    print("\n3. Updating calendar_events table...")
    execute_query("""
        ALTER TABLE calendar_events 
        ADD COLUMN IF NOT EXISTS event_type VARCHAR(20) DEFAULT 'task'
    """)
    
    execute_query("""
        ALTER TABLE calendar_events 
        ADD COLUMN IF NOT EXISTS is_calendar_synced BOOLEAN DEFAULT FALSE
    """)
    
    execute_query("""
        CREATE INDEX IF NOT EXISTS idx_calendar_events_event_type ON calendar_events(event_type)
    """)
    
    execute_query("""
        CREATE INDEX IF NOT EXISTS idx_calendar_events_user_event_type ON calendar_events(user_id, event_type)
    """)
    print("✓ calendar_events table updated")
    
    # 4. Create views
    print("\n4. Creating helpful views...")
    execute_query("""
        CREATE OR REPLACE VIEW upcoming_meetings AS
        SELECT 
            ce.event_id,
            ce.user_id AS organizer_id,
            u.username AS organizer_username,
            ce.start_time,
            ce.end_time,
            ce.event_desc,
            ce.event_type,
            ml.meeting_url,
            ml.platform,
            COUNT(ec.collab_id) AS collaborator_count
        FROM calendar_events ce
        LEFT JOIN users u ON ce.user_id = u.id
        LEFT JOIN meeting_links ml ON ce.event_id = ml.event_id
        LEFT JOIN event_collaborators ec ON ce.event_id = ec.event_id
        WHERE ce.event_type = 'meeting' 
          AND ce.start_time > NOW()
        GROUP BY ce.event_id, u.username, ml.meeting_url, ml.platform
        ORDER BY ce.start_time ASC
    """)
    print("✓ upcoming_meetings view created")
    
    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
