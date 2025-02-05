-- Drop the updated search_memories function with metadata filtering
DROP FUNCTION public.search_memories(vector(1536), float8, integer, uuid, jsonb);

-- Note: The original search_memories function from 1_init will be restored when that migration is reapplied 