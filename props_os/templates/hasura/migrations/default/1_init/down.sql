-- Drop functions
DROP FUNCTION IF EXISTS search_memories;
DROP FUNCTION IF EXISTS update_updated_at_column;

-- Drop tables
DROP TABLE IF EXISTS public.memories;
DROP TABLE IF EXISTS public.agents;

-- Drop extensions
DROP EXTENSION IF EXISTS vector;
DROP EXTENSION IF EXISTS "uuid-ossp"; 