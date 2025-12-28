-- Migration for Enhanced Task/Event/Meeting Workflow
-- Created: 2025-12-29
-- Purpose: Add support for event collaborators, meeting links, and event type classification

-- ============================================================================
-- 1. Create event_collaborators table
-- ============================================================================
CREATE TABLE IF NOT EXISTS event_collaborators (
    collab_id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES calendar_events(event_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, user_id)
);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_event_collaborators_event_id ON event_collaborators(event_id);
CREATE INDEX IF NOT EXISTS idx_event_collaborators_user_id ON event_collaborators(user_id);

COMMENT ON TABLE event_collaborators IS 'Tracks which users are invited/participating in calendar events (meetings)';

-- ============================================================================
-- 2. Create meeting_links table
-- ============================================================================
CREATE TABLE IF NOT EXISTS meeting_links (
    link_id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES calendar_events(event_id) ON DELETE CASCADE,
    platform VARCHAR(50) DEFAULT 'google_meet', -- google_meet, zoom, teams, custom
    meeting_code VARCHAR(255),
    meeting_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id)
);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_meeting_links_event_id ON meeting_links(event_id);

COMMENT ON TABLE meeting_links IS 'Stores generated or user-provided meeting links for events';
COMMENT ON COLUMN meeting_links.platform IS 'Meeting platform: google_meet, zoom, teams, or custom';

-- ============================================================================
-- 3. Update calendar_events table
-- ============================================================================
-- Add event_type column to distinguish between tasks, meetings, and events
ALTER TABLE calendar_events 
ADD COLUMN IF NOT EXISTS event_type VARCHAR(20) DEFAULT 'task';

-- Add is_calendar_synced to track Google Calendar sync status
ALTER TABLE calendar_events 
ADD COLUMN IF NOT EXISTS is_calendar_synced BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN calendar_events.event_type IS 'Event classification: task, meeting, or event';
COMMENT ON COLUMN calendar_events.is_calendar_synced IS 'Whether this event has been synced to Google Calendar';

-- Add index for event type filtering
CREATE INDEX IF NOT EXISTS idx_calendar_events_event_type ON calendar_events(event_type);
CREATE INDEX IF NOT EXISTS idx_calendar_events_user_event_type ON calendar_events(user_id, event_type);

-- ============================================================================
-- 4. Add helpful views for common queries
-- ============================================================================

-- View: Upcoming meetings with collaborators
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
ORDER BY ce.start_time ASC;

COMMENT ON VIEW upcoming_meetings IS 'Shows all upcoming meetings with collaborator counts and meeting links';

-- View: User's tasks (non-meeting events)
CREATE OR REPLACE VIEW user_tasks AS
SELECT 
    t.task_id,
    t.user_id,
    t.title,
    t.description,
    t.status,
    t.priority,
    t.category,
    t.due_date,
    ce.event_id,
    ce.start_time AS scheduled_time
FROM tasks t
LEFT JOIN calendar_events ce ON t.task_id = ce.task_id
WHERE ce.event_type = 'task' OR ce.event_type IS NULL
ORDER BY t.due_date ASC;

COMMENT ON VIEW user_tasks IS 'Shows all user tasks with optional calendar event information';

-- ============================================================================
-- Migration complete
-- ============================================================================
