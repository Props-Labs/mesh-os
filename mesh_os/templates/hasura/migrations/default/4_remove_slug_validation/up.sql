-- Drop the valid_slug constraint from the agents table
ALTER TABLE public.agents DROP CONSTRAINT IF EXISTS valid_slug;

-- Drop the validate_slug function
DROP FUNCTION IF EXISTS validate_slug(text); 