-- Drop indexes
DROP INDEX IF EXISTS idx_memories_agent_id;
DROP INDEX IF EXISTS idx_memory_chunks_agent_id;
DROP INDEX IF EXISTS idx_memory_edges_agent_id;
DROP INDEX IF EXISTS idx_workflow_runs_agent_id;
DROP INDEX IF EXISTS idx_workflow_results_agent_id;

-- Remove agent_id columns
ALTER TABLE memories DROP COLUMN IF EXISTS agent_id;
ALTER TABLE memory_chunks DROP COLUMN IF EXISTS agent_id;
ALTER TABLE memory_edges DROP COLUMN IF EXISTS agent_id;
ALTER TABLE workflow_runs DROP COLUMN IF EXISTS agent_id;
ALTER TABLE workflow_results DROP COLUMN IF EXISTS agent_id;

-- Drop agents table and its trigger
DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;
DROP TABLE IF EXISTS agents CASCADE; 