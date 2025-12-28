-- Remove status column from event_collaborators table
-- This column is not needed as we don't currently track acceptance status

ALTER TABLE event_collaborators 
DROP COLUMN IF EXISTS status;
