-- First drop the constraint since it depends on the function
ALTER TABLE public.agents DROP CONSTRAINT IF EXISTS valid_slug;

-- Now we can safely drop and recreate the function
DROP FUNCTION IF EXISTS validate_slug(text);
CREATE OR REPLACE FUNCTION validate_slug(slug text)
RETURNS boolean AS $$
BEGIN
    RETURN slug ~ '^[a-z][a-z0-9_-]*[a-z0-9]$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Update any existing invalid slugs to NULL
UPDATE public.agents 
SET slug = NULL 
WHERE slug IS NOT NULL AND NOT validate_slug(slug);

-- Finally add back the constraint
ALTER TABLE public.agents
ADD CONSTRAINT valid_slug CHECK (slug IS NULL OR validate_slug(slug)); 