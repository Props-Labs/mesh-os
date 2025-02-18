-- Remove sample data in reverse order
DELETE FROM memory_edges WHERE agent_id = 'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62';
DELETE FROM workflow_results WHERE agent_id = 'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62';
DELETE FROM workflow_runs WHERE agent_id = 'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62';
DELETE FROM memory_chunks WHERE agent_id = 'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62';
DELETE FROM memories WHERE agent_id = 'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62';
DELETE FROM agents WHERE id = 'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62';

-- Drop views that depend on memories table
DROP VIEW IF EXISTS memory_chunks_with_details CASCADE;
DROP VIEW IF EXISTS memory_search_results CASCADE;

-- Drop function
DROP FUNCTION IF EXISTS search_memory_chunks(vector, double precision, integer, uuid, jsonb, jsonb, jsonb);

-- Drop indexes
DROP INDEX IF EXISTS idx_memories_agent_id;
DROP INDEX IF EXISTS idx_memory_chunks_agent_id;
DROP INDEX IF EXISTS idx_memory_edges_agent_id;
DROP INDEX IF EXISTS idx_workflow_runs_agent_id;
DROP INDEX IF EXISTS idx_workflow_results_agent_id;

-- Drop agent_id columns
ALTER TABLE workflow_results DROP COLUMN IF EXISTS agent_id;
ALTER TABLE workflow_runs DROP COLUMN IF EXISTS agent_id;
ALTER TABLE memory_edges DROP COLUMN IF EXISTS agent_id;
ALTER TABLE memory_chunks DROP COLUMN IF EXISTS agent_id;
ALTER TABLE memories DROP COLUMN IF EXISTS agent_id;

-- Drop trigger
DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;

-- Drop agents table
DROP TABLE IF EXISTS agents CASCADE;

-- Recreate the view without agent_id
CREATE OR REPLACE VIEW memory_chunks_with_details AS
SELECT 
    mc.id as chunk_id,
    mc.memory_id,
    mc.chunk_index,
    mc.content as chunk_content,
    mc.embedding,
    mc.metadata as chunk_metadata,
    mc.created_at as chunk_created_at,
    mc.updated_at as chunk_updated_at,
    m.content as memory_content,
    m.type as memory_type,
    m.status as memory_status,
    m.metadata as memory_metadata,
    m.created_at as memory_created_at,
    m.updated_at as memory_updated_at,
    NULL::uuid as agent_id
FROM memory_chunks mc
JOIN memories m ON mc.memory_id = m.id;

-- Recreate the search results view
CREATE OR REPLACE VIEW memory_search_results AS
SELECT 
    chunk_id,
    memory_id,
    chunk_index,
    chunk_content,
    chunk_metadata,
    chunk_created_at,
    chunk_updated_at,
    memory_content,
    memory_type,
    memory_status,
    memory_metadata,
    memory_created_at,
    memory_updated_at,
    agent_id,
    0.0::float as similarity
FROM memory_chunks_with_details
WHERE false; 