-- Create agents table
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create trigger for agents updated_at
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add agent_id to memories
ALTER TABLE memories 
ADD COLUMN agent_id UUID REFERENCES agents(id) ON DELETE SET NULL;

-- Add agent_id to memory_chunks
ALTER TABLE memory_chunks 
ADD COLUMN agent_id UUID REFERENCES agents(id) ON DELETE SET NULL;

-- Add agent_id to memory_edges
ALTER TABLE memory_edges 
ADD COLUMN agent_id UUID REFERENCES agents(id) ON DELETE SET NULL;

-- Add agent_id to workflow_runs
ALTER TABLE workflow_runs 
ADD COLUMN agent_id UUID REFERENCES agents(id) ON DELETE SET NULL;

-- Add agent_id to workflow_results
ALTER TABLE workflow_results 
ADD COLUMN agent_id UUID REFERENCES agents(id) ON DELETE SET NULL;

-- Create indexes for agent_id fields
CREATE INDEX idx_memories_agent_id ON memories(agent_id);
CREATE INDEX idx_memory_chunks_agent_id ON memory_chunks(agent_id);
CREATE INDEX idx_memory_edges_agent_id ON memory_edges(agent_id);
CREATE INDEX idx_workflow_runs_agent_id ON workflow_runs(agent_id);
CREATE INDEX idx_workflow_results_agent_id ON workflow_results(agent_id);

-- Add helpful comments
COMMENT ON TABLE agents IS 
'Agents that can own and interact with memories and workflows.';

COMMENT ON COLUMN agents.name IS 
'Optional name for the agent.';

COMMENT ON COLUMN agents.description IS 
'Optional description of the agent''s purpose or capabilities.';

COMMENT ON COLUMN memories.agent_id IS 
'Reference to the agent that owns or created this memory.';

COMMENT ON COLUMN memory_chunks.agent_id IS 
'Reference to the agent that owns or created this memory chunk.';

COMMENT ON COLUMN memory_edges.agent_id IS 
'Reference to the agent that created this relationship.';

COMMENT ON COLUMN workflow_runs.agent_id IS 
'Reference to the agent that initiated this workflow run.';

COMMENT ON COLUMN workflow_results.agent_id IS 
'Reference to the agent that owns this workflow result.'; 