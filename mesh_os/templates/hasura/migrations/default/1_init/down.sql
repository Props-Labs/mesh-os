-- Drop views first since they depend on tables
DROP VIEW IF EXISTS public.memories_with_similarity CASCADE;
DROP VIEW IF EXISTS public.search_results_with_similarity CASCADE;
DROP VIEW IF EXISTS public.memory_connections_with_details CASCADE;
DROP VIEW IF EXISTS public.memory_embeddings_info CASCADE;
DROP VIEW IF EXISTS public.memory_chunks_with_details CASCADE;
DROP VIEW IF EXISTS public.memory_search_results CASCADE;

-- Drop all tables in correct order (respecting foreign key constraints)
-- Using CASCADE will automatically handle dependent objects (triggers, indexes, etc)
DROP TABLE IF EXISTS memory_edges CASCADE;
DROP TABLE IF EXISTS memory_chunks CASCADE;
DROP TABLE IF EXISTS memories CASCADE;
DROP TABLE IF EXISTS workflow_results CASCADE;
DROP TABLE IF EXISTS workflow_runs CASCADE;
DROP TABLE IF EXISTS workflow_schemas CASCADE;
DROP TABLE IF EXISTS type_schemas CASCADE;

-- Drop functions (using CASCADE to handle any remaining dependencies)
DROP FUNCTION IF EXISTS get_connected_memories CASCADE;
DROP FUNCTION IF EXISTS inspect_memory_embeddings CASCADE;
DROP FUNCTION IF EXISTS search_memory_chunks CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;
DROP FUNCTION IF EXISTS normalize_embedding CASCADE;
DROP FUNCTION IF EXISTS validate_slug CASCADE;

-- Drop custom types
DROP TYPE IF EXISTS memory_embedding_info CASCADE;

-- Finally drop extensions
DROP EXTENSION IF EXISTS vector CASCADE;
DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE; 