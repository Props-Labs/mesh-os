-- Drop all versions of search_memories function
DROP FUNCTION IF EXISTS public.search_memories(vector(1536), float8, integer, uuid, jsonb);
DROP FUNCTION IF EXISTS public.search_memories(vector(1536), float8, integer, uuid);
DROP FUNCTION IF EXISTS public.search_memories;

-- Drop other functions
DROP FUNCTION IF EXISTS get_connected_memories;

-- Drop triggers first
DROP TRIGGER IF EXISTS update_agents_updated_at ON public.agents;
DROP TRIGGER IF EXISTS update_memories_updated_at ON public.memories;

-- Now we can safely drop the trigger function
DROP FUNCTION IF EXISTS update_updated_at_column;

-- Drop views first
DROP VIEW IF EXISTS public.memories_with_similarity;

-- Drop tables
DROP TABLE IF EXISTS public.memory_edges;
DROP TABLE IF EXISTS public.memories;
DROP TABLE IF EXISTS public.agents;

-- Drop extensions (with CASCADE for vector since it has dependent objects)
DROP EXTENSION IF EXISTS vector CASCADE;
DROP EXTENSION IF EXISTS "uuid-ossp"; 