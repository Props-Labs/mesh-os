-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create helper functions first
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE FUNCTION normalize_embedding()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.embedding IS NOT NULL THEN
        NEW.embedding = l2_normalize(NEW.embedding);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION validate_slug(slug text)
RETURNS boolean AS $$
BEGIN
    RETURN slug ~ '^[a-z][a-z0-9_-]*[a-z0-9]$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create type_schemas table
CREATE TABLE IF NOT EXISTS type_schemas (
    type TEXT PRIMARY KEY,
    schema JSONB NOT NULL,
    metadata_schema JSONB,
    embedding_config JSONB,
    chunking_config JSONB,
    validation_rules JSONB,
    behaviors JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create workflow_schemas table
CREATE TABLE IF NOT EXISTS workflow_schemas (
    type TEXT PRIMARY KEY,
    input_schema JSONB NOT NULL,
    output_schema JSONB NOT NULL,
    metadata_schema JSONB,
    validation_rules JSONB,
    behaviors JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create workflow_runs table
CREATE TABLE IF NOT EXISTS workflow_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type TEXT NOT NULL REFERENCES workflow_schemas(type),
    status TEXT NOT NULL DEFAULT 'pending',
    input JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_workflow_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

-- Create workflow_results table
CREATE TABLE IF NOT EXISTS workflow_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    result JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create memories table
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type TEXT NOT NULL REFERENCES type_schemas(type),
    status TEXT NOT NULL DEFAULT 'active',
    metadata JSONB DEFAULT '{}'::jsonb,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_memory_status CHECK (status IN ('active', 'archived', 'deleted'))
);

-- Create memory_chunks table
CREATE TABLE IF NOT EXISTS memory_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure ordering within a memory
    UNIQUE (memory_id, chunk_index)
);

-- Create memory_edges table
CREATE TABLE IF NOT EXISTS memory_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_memory UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    target_memory UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create all triggers safely
DO $$ 
DECLARE
    trigger_record record;
BEGIN
    -- First drop any existing user-defined triggers (excluding RI triggers)
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
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON public.%I;',
            trigger_record.trigger_name,
            trigger_record.table_name
        );
    END LOOP;

    -- Now create all triggers
    -- Type Schemas
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_type_schemas_updated_at') THEN
        CREATE TRIGGER update_type_schemas_updated_at
            BEFORE UPDATE ON type_schemas
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Workflow Schemas
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_workflow_schemas_updated_at') THEN
        CREATE TRIGGER update_workflow_schemas_updated_at
            BEFORE UPDATE ON workflow_schemas
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Workflow Runs
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_workflow_runs_updated_at') THEN
        CREATE TRIGGER update_workflow_runs_updated_at
            BEFORE UPDATE ON workflow_runs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Workflow Results
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_workflow_results_updated_at') THEN
        CREATE TRIGGER update_workflow_results_updated_at
            BEFORE UPDATE ON workflow_results
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Memories
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_memories_updated_at') THEN
        CREATE TRIGGER update_memories_updated_at
            BEFORE UPDATE ON memories
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Memory Chunks
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_memory_chunks_updated_at') THEN
        CREATE TRIGGER update_memory_chunks_updated_at
            BEFORE UPDATE ON memory_chunks
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'normalize_memory_chunk_embedding') THEN
        CREATE TRIGGER normalize_memory_chunk_embedding
            BEFORE INSERT OR UPDATE OF embedding ON memory_chunks
            FOR EACH ROW
            EXECUTE FUNCTION normalize_embedding();
    END IF;

    -- Memory Edges
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_memory_edges_updated_at') THEN
        CREATE TRIGGER update_memory_edges_updated_at
            BEFORE UPDATE ON memory_edges
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Create indexes safely
DO $$
BEGIN
    -- Drop existing indexes first
    DROP INDEX IF EXISTS idx_memory_chunks_embedding;
    DROP INDEX IF EXISTS idx_memory_edges_source;
    DROP INDEX IF EXISTS idx_memory_edges_target;
    DROP INDEX IF EXISTS idx_memory_edges_type;

    -- Create new indexes
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'idx_memory_chunks_embedding' AND n.nspname = 'public'
    ) THEN
        CREATE INDEX idx_memory_chunks_embedding 
        ON memory_chunks USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'idx_memory_edges_source' AND n.nspname = 'public'
    ) THEN
        CREATE INDEX idx_memory_edges_source ON memory_edges(source_memory);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'idx_memory_edges_target' AND n.nspname = 'public'
    ) THEN
        CREATE INDEX idx_memory_edges_target ON memory_edges(target_memory);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'idx_memory_edges_type' AND n.nspname = 'public'
    ) THEN
        CREATE INDEX idx_memory_edges_type ON memory_edges(type);
    END IF;
END $$;

-- Create views for search results
CREATE OR REPLACE VIEW memory_connections_with_details AS
SELECT 
    e.source_memory as source_id,
    e.target_memory as target_id,
    e.type as relationship,
    e.weight,
    e.metadata,
    e.created_at,
    e.updated_at,
    source_mem.content as source_content,
    target_mem.content as target_content,
    source_mem.type as source_type,
    target_mem.type as target_type
FROM memory_edges e
JOIN memories source_mem ON e.source_memory = source_mem.id
JOIN memories target_mem ON e.target_memory = target_mem.id;

-- Create view for memory embeddings info
CREATE OR REPLACE VIEW memory_embeddings_info AS
SELECT 
    id as memory_id,
    content,
    sqrt(embedding <-> embedding) as embedding_norm,
    abs(1 - sqrt(embedding <-> embedding)) < 0.000001 as is_normalized
FROM memory_chunks
WHERE embedding IS NOT NULL;

-- Create helper functions
CREATE OR REPLACE FUNCTION get_connected_memories(
    memory_id uuid,
    relationship_type text DEFAULT NULL,
    max_depth integer DEFAULT 1
)
RETURNS SETOF memory_connections_with_details
LANGUAGE sql STABLE AS $$
    WITH RECURSIVE memory_graph AS (
        -- Base case
        SELECT 
            source_memory,
            target_memory,
            type as relationship,
            weight,
            metadata,
            created_at,
            updated_at,
            1 as depth
        FROM memory_edges
        WHERE 
            (source_memory = memory_id OR target_memory = memory_id)
            AND (relationship_type IS NULL OR type = relationship_type)
        
        UNION
        
        -- Recursive case
        SELECT 
            e.source_memory,
            e.target_memory,
            e.type,
            e.weight,
            e.metadata,
            e.created_at,
            e.updated_at,
            g.depth + 1
        FROM memory_edges e
        INNER JOIN memory_graph g ON 
            (e.source_memory = g.target_memory OR e.target_memory = g.source_memory)
        WHERE 
            g.depth < max_depth
            AND (relationship_type IS NULL OR e.type = relationship_type)
    )
    SELECT DISTINCT
        mc.*
    FROM memory_graph g
    JOIN memory_connections_with_details mc ON 
        (mc.source_id = g.source_memory AND mc.target_id = g.target_memory);
$$;

CREATE OR REPLACE FUNCTION inspect_memory_embeddings()
RETURNS SETOF memory_embeddings_info
LANGUAGE sql STABLE AS $$
    SELECT * FROM memory_embeddings_info;
$$;

-- Add helpful comments
COMMENT ON TABLE type_schemas IS 
'Defines valid types for memories and their associated schemas and configurations.';

COMMENT ON TABLE workflow_schemas IS 
'Defines valid workflow types and their input/output schemas.';

COMMENT ON TABLE workflow_runs IS 
'Records of workflow executions with their inputs and status.';

COMMENT ON TABLE workflow_results IS 
'Results of completed workflow runs.';

COMMENT ON TABLE memories IS 
'Core memory storage with type validation against type_schemas.';

COMMENT ON TABLE memory_chunks IS 
'Chunked content from memories with vector embeddings for semantic search.';

COMMENT ON TABLE memory_edges IS 
'Relationships between memories with type and weight.';

COMMENT ON VIEW memory_embeddings_info IS 
'View providing information about memory chunk embeddings including normalization status.';

COMMENT ON FUNCTION inspect_memory_embeddings IS 
'Inspect memory chunk embeddings to verify normalization and get embedding norms.'; 