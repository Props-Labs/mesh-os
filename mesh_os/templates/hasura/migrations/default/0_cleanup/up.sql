-- Drop all views
DROP VIEW IF EXISTS public.memories_with_similarity CASCADE;
DROP VIEW IF EXISTS public.search_results_with_similarity CASCADE;
DROP VIEW IF EXISTS public.memory_chunks_with_similarity CASCADE;

-- Drop all functions (with their overloaded versions)
DROP FUNCTION IF EXISTS public.search_memories(vector(1536), float8, integer, uuid) CASCADE;
DROP FUNCTION IF EXISTS public.search_memories(vector(1536), float8, integer, uuid, jsonb, jsonb, jsonb) CASCADE;
DROP FUNCTION IF EXISTS public.search_chunks_and_entities(vector(1536), float8, integer, boolean, boolean, jsonb, jsonb) CASCADE;
DROP FUNCTION IF EXISTS public.get_connected_memories(uuid, text, integer) CASCADE;
DROP FUNCTION IF EXISTS public.inspect_memory_embeddings() CASCADE;
DROP FUNCTION IF EXISTS public.debug_vector_info(vector(1536)) CASCADE;
DROP FUNCTION IF EXISTS public.normalize_embedding() CASCADE;
DROP FUNCTION IF EXISTS public.update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS public.validate_slug(text) CASCADE;

-- Drop all indexes explicitly (in case CASCADE didn't catch them)
DROP INDEX IF EXISTS public.idx_memories_embedding CASCADE;
DROP INDEX IF EXISTS public.idx_memory_chunks_embedding CASCADE;
DROP INDEX IF EXISTS public.idx_memory_edges_source CASCADE;
DROP INDEX IF EXISTS public.idx_memory_edges_target CASCADE;
DROP INDEX IF EXISTS public.idx_memory_edges_type CASCADE;

-- Drop all user-defined triggers (excluding referential integrity triggers)
DO $$ 
DECLARE
    trigger_record record;
BEGIN
    FOR trigger_record IN 
        SELECT 
            tgname as trigger_name,
            relname as table_name
        FROM pg_trigger t
        JOIN pg_class c ON t.tgrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = 'public'
        AND NOT tgname LIKE 'RI_ConstraintTrigger_%'  -- Exclude referential integrity triggers
        AND NOT tgname LIKE 'pg_trigger_%'  -- Exclude other system triggers
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON public.%I CASCADE;',
            trigger_record.trigger_name,
            trigger_record.table_name
        );
    END LOOP;
END $$;

-- Drop all tables in correct order
DROP TABLE IF EXISTS public.memory_edges CASCADE;
DROP TABLE IF EXISTS public.memory_chunks CASCADE;
DROP TABLE IF EXISTS public.memories CASCADE;
DROP TABLE IF EXISTS public.workflow_results CASCADE;
DROP TABLE IF EXISTS public.workflow_runs CASCADE;
DROP TABLE IF EXISTS public.workflow_schemas CASCADE;
DROP TABLE IF EXISTS public.type_schemas CASCADE;
DROP TABLE IF EXISTS public.agents CASCADE;

-- Drop extensions (only if you're sure no other databases/schemas need them)
-- DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;
-- DROP EXTENSION IF EXISTS "vector" CASCADE; 