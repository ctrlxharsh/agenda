-- Drop old constraint if exists
ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_collaborator_fkey;

-- Change collaborator column to integer array
ALTER TABLE public.users 
    ALTER COLUMN collaborator TYPE integer[] USING ARRAY[collaborator];

-- Rename column to collaborator_ids
ALTER TABLE public.users 
    RENAME COLUMN collaborator TO collaborator_ids;

-- Create collaboration_requests table
CREATE TABLE IF NOT EXISTS public.collaboration_requests (
    request_id serial PRIMARY KEY,
    sender_id integer REFERENCES public.users(id) ON DELETE CASCADE,
    receiver_id integer REFERENCES public.users(id) ON DELETE CASCADE,
    status text CHECK (status IN ('pending', 'accepted', 'rejected')) DEFAULT 'pending',
    created_at timestamp without time zone DEFAULT now(),
    UNIQUE(sender_id, receiver_id)
);
