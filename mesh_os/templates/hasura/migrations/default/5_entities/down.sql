-- Drop the combined search function
DROP FUNCTION IF EXISTS search_memories_and_entities;

-- Drop the combined search results view
DROP VIEW IF EXISTS public.search_results_with_similarity;

-- Drop triggers
DROP TRIGGER IF EXISTS update_entities_updated_at ON public.entities;
DROP TRIGGER IF EXISTS normalize_entity_embedding ON public.entities;

-- Drop tables (order matters due to foreign key constraints)
DROP TABLE IF EXISTS public.entity_memory_links;
DROP TABLE IF EXISTS public.entities;