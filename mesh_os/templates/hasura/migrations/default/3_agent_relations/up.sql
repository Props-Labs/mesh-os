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

-- Drop views that depend on memories table
DROP VIEW IF EXISTS memory_chunks_with_details CASCADE;
DROP VIEW IF EXISTS memory_search_results CASCADE;

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

-- Recreate the view with agent_id support
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
    m.agent_id
FROM memory_chunks mc
JOIN memories m ON mc.memory_id = m.id;

-- Create view for search results
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
WHERE false;  -- Empty by default, will be populated by function

-- Create search function
CREATE OR REPLACE FUNCTION search_memory_chunks(
    query_embedding vector,
    match_threshold double precision,
    match_count integer,
    filter_agent_id uuid DEFAULT NULL::uuid,
    memory_metadata_filter jsonb DEFAULT NULL::jsonb,
    chunk_metadata_filter jsonb DEFAULT NULL::jsonb,
    created_at_filter jsonb DEFAULT NULL::jsonb
)
RETURNS SETOF memory_search_results
LANGUAGE sql STABLE AS $$
    WITH normalized_query AS (
        SELECT l2_normalize(query_embedding) AS normalized_vector
    )
    SELECT
        cd.chunk_id,
        cd.memory_id,
        cd.chunk_index,
        cd.chunk_content,
        cd.chunk_metadata,
        cd.chunk_created_at,
        cd.chunk_updated_at,
        cd.memory_content,
        cd.memory_type,
        cd.memory_status,
        cd.memory_metadata,
        cd.memory_created_at,
        cd.memory_updated_at,
        cd.agent_id,
        -(cd.embedding <#> (SELECT normalized_vector FROM normalized_query)) as similarity
    FROM memory_chunks_with_details cd
    WHERE
        CASE
            WHEN filter_agent_id IS NOT NULL THEN cd.agent_id = filter_agent_id
            ELSE TRUE
        END
        AND CASE
            WHEN memory_metadata_filter IS NOT NULL THEN cd.memory_metadata @> memory_metadata_filter
            ELSE TRUE
        END
        AND CASE
            WHEN chunk_metadata_filter IS NOT NULL THEN cd.chunk_metadata @> chunk_metadata_filter
            ELSE TRUE
        END
        AND CASE
            WHEN created_at_filter IS NOT NULL THEN (
                CASE
                    WHEN created_at_filter ? '_gt' THEN cd.chunk_created_at > (created_at_filter->>'_gt')::timestamptz AT TIME ZONE 'UTC'
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_gte' THEN cd.chunk_created_at >= (created_at_filter->>'_gte')::timestamptz AT TIME ZONE 'UTC'
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_lt' THEN cd.chunk_created_at < (created_at_filter->>'_lt')::timestamptz AT TIME ZONE 'UTC'
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_lte' THEN cd.chunk_created_at <= (created_at_filter->>'_lte')::timestamptz AT TIME ZONE 'UTC'
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_eq' THEN cd.chunk_created_at = (created_at_filter->>'_eq')::timestamptz AT TIME ZONE 'UTC'
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_is_null' AND (created_at_filter->>'_is_null')::boolean THEN cd.chunk_created_at IS NULL
                    WHEN created_at_filter ? '_is_null' AND NOT (created_at_filter->>'_is_null')::boolean THEN cd.chunk_created_at IS NOT NULL
                    ELSE TRUE
                END
            )
            ELSE TRUE
        END
        AND cd.embedding IS NOT NULL
        AND -(cd.embedding <#> (SELECT normalized_vector FROM normalized_query)) >= match_threshold
    ORDER BY
        -(cd.embedding <#> (SELECT normalized_vector FROM normalized_query)) DESC
    LIMIT match_count;
$$;

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

-- Insert sample agent and data
INSERT INTO agents (id, name, description) VALUES 
('d7f3668d-5ebf-4f95-9b5c-07301f5d4c62'::uuid, 'TestAgent', 'A test agent for development and examples');

-- Insert sample memories and their chunks
WITH text_memory AS (
    INSERT INTO memories (id, type, content, metadata, agent_id) VALUES
    ('f7a6c2b1-d123-4567-8901-2345abcdef67'::uuid, 
     'text_document', 
     'The quick brown fox jumps over the lazy dog. This classic pangram contains every letter of the English alphabet at least once.',
     jsonb_build_object(
        'source', 'example_docs',
        'tags', array['pangram', 'example']
     ),
     'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62'::uuid
    ) RETURNING id, content
),
code_memory AS (
    INSERT INTO memories (id, type, content, metadata, agent_id) VALUES
    ('e8b7d3c2-e234-5678-9012-3456bcdef789'::uuid,
     'code_snippet',
     'def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)',
     jsonb_build_object(
        'repository', 'algorithms',
        'path', 'math/fibonacci.py',
        'tags', array['python', 'recursion']
     ),
     'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62'::uuid
    ) RETURNING id, content
)
-- Insert memory chunks with sample embeddings
INSERT INTO memory_chunks (id, memory_id, chunk_index, content, embedding, metadata, agent_id)
SELECT 
    'a1b2c3d4-1234-5678-90ab-cdef12345678'::uuid,
    id,
    0,
    content,
    l2_normalize((
        SELECT array_agg(val)::vector
        FROM (
            SELECT 
                CASE 
                    WHEN n <= 512 THEN 0.8 + random() * 0.4  -- Higher values for first third
                    WHEN n <= 1024 THEN 0.4 + random() * 0.4  -- Medium values for middle third
                    ELSE random() * 0.4  -- Lower values for last third
                END as val
            FROM generate_series(1, 1536) n
        ) vals
    )),  -- Use l2_normalize directly
    jsonb_build_object(
        'chunk_type', 'full',
        'embedding_model', 'text-embedding-3-small',
        'embedding_created_at', CURRENT_TIMESTAMP
    ),
    'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62'::uuid
FROM text_memory
UNION ALL
SELECT 
    'b2c3d4e5-2345-6789-01bc-def234567890'::uuid,
    id,
    0,
    content,
    l2_normalize((
        SELECT array_agg(val)::vector
        FROM (
            SELECT 
                CASE 
                    WHEN n <= 512 THEN random() * 0.4  -- Lower values for first third
                    WHEN n <= 1024 THEN 0.6 + random() * 0.4  -- Higher values for middle third
                    ELSE 0.3 + random() * 0.4  -- Medium values for last third
                END as val
            FROM generate_series(1, 1536) n
        ) vals
    )),  -- Use l2_normalize directly
    jsonb_build_object(
        'chunk_type', 'full',
        'embedding_model', 'text-embedding-3-small',
        'embedding_created_at', CURRENT_TIMESTAMP
    ),
    'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62'::uuid
FROM code_memory;

-- Insert sample workflow runs and results
WITH inserted_run AS (
    INSERT INTO workflow_runs (id, type, status, input, metadata, agent_id) VALUES
    ('c4d5e6f7-3456-7890-12cd-ef3456789012'::uuid,
     'document_analysis',
     'completed',
     jsonb_build_object(
        'document_id', 'f7a6c2b1-d123-4567-8901-2345abcdef67',
        'analysis_type', 'summary'
     ),
     jsonb_build_object(
        'model_version', '1.0.0',
        'processing_time', 0.5
     ),
     'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62'::uuid
    ) RETURNING id
)
INSERT INTO workflow_results (id, workflow_id, result, metadata, agent_id) VALUES
(
    'd5e6f7f8-4567-8901-23de-f45678901234'::uuid,
    (SELECT id FROM inserted_run),
    jsonb_build_object(
        'summary', 'A pangram demonstrating all English alphabet letters.',
        'confidence', 0.95
    ),
    jsonb_build_object(
        'completion_time', CURRENT_TIMESTAMP,
        'tokens_processed', 15
    ),
    'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62'::uuid
);

-- Create relationships between memories
INSERT INTO memory_edges (id, source_memory, target_memory, type, metadata, weight, agent_id)
SELECT 
    'e6f7a8a9-5678-9012-34ef-a56789012345'::uuid,
    m1.id,
    m2.id,
    'related_content',
    jsonb_build_object(
        'relationship_type', 'example',
        'created_by', 'system'
    ),
    0.8,
    'd7f3668d-5ebf-4f95-9b5c-07301f5d4c62'::uuid
FROM memories m1
JOIN memories m2 ON m1.type = 'text_document' AND m2.type = 'code_snippet'; 