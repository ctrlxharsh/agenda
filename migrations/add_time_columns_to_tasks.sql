-- Migration: Add start_time and end_time columns to tasks table
-- Change scheduled_date and due_date to DATE type only

-- Step 1: Add new time columns
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS start_time TIME,
ADD COLUMN IF NOT EXISTS end_time TIME;

-- Step 2: Migrate existing timestamp data to time columns
-- Extract time component from scheduled_date if it exists
UPDATE tasks 
SET start_time = scheduled_date::TIME 
WHERE scheduled_date IS NOT NULL 
  AND start_time IS NULL;

-- Step 3: Convert scheduled_date and due_date to DATE type
-- This will remove the time component, keeping only the date
ALTER TABLE tasks 
ALTER COLUMN scheduled_date TYPE DATE USING scheduled_date::DATE;

ALTER TABLE tasks 
ALTER COLUMN due_date TYPE DATE USING due_date::DATE;

-- Verification queries
-- Check the new schema
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'tasks' 
  AND column_name IN ('scheduled_date', 'due_date', 'start_time', 'end_time')
ORDER BY column_name;

-- Check sample data
SELECT task_id, title, scheduled_date, due_date, start_time, end_time 
FROM tasks 
LIMIT 5;
