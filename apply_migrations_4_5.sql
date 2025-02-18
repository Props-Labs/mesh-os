-- Start transaction
BEGIN;

-- Migration 4: Remove slug validation
ALTER TABLE public.agents DROP CONSTRAINT IF EXISTS valid_slug;
DROP FUNCTION IF EXISTS validate_slug(text);

-- Migration 5: Entities
-- Create entities table with embedding support
CREATE TABLE IF NOT EXISTS public.entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ref_id TEXT UNIQUE,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    metadata JSONB,
    embedding vector(1536),
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create entity-memory links table
CREATE TABLE IF NOT EXISTS public.entity_memory_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES public.entities(id) ON DELETE CASCADE,
    memory_id UUID NOT NULL REFERENCES public.memories(id) ON DELETE CASCADE,
    relationship TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(entity_id, memory_id, relationship)
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_entities_embedding 
ON public.entities USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create trigger for updated_at
CREATE TRIGGER update_entities_updated_at
    BEFORE UPDATE ON public.entities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add normalization trigger for entities
CREATE TRIGGER normalize_entity_embedding
    BEFORE INSERT OR UPDATE OF embedding ON public.entities
    FOR EACH ROW
    EXECUTE FUNCTION normalize_embedding();

-- Create a view for combined search results
CREATE OR REPLACE VIEW public.search_results_with_similarity AS
SELECT 
    id,
    'memory'::text as type,
    content,
    metadata,
    0::float8 as similarity
FROM memories
UNION ALL
SELECT 
    id,
    'entity'::text as type,
    name as content,
    metadata,
    0::float8 as similarity
FROM entities;

-- Create combined search function
CREATE OR REPLACE FUNCTION search_memories_and_entities(
    query_embedding vector(1536),
    match_threshold float8,
    match_count integer,
    include_entities boolean DEFAULT true,
    include_memories boolean DEFAULT true,
    metadata_filter jsonb DEFAULT NULL,
    created_at_filter jsonb DEFAULT NULL
)
RETURNS SETOF public.search_results_with_similarity
LANGUAGE sql STABLE AS $$
    WITH normalized_query AS (
        SELECT l2_normalize(query_embedding) AS normalized_vector
    )
    (
        SELECT 
            m.id,
            'memory'::text as type,
            m.content,
            m.metadata,
            -(m.embedding <#> (SELECT normalized_vector FROM normalized_query)) as similarity
        FROM memories m
        WHERE include_memories = true
        AND CASE
            WHEN metadata_filter IS NOT NULL THEN m.metadata @> metadata_filter
            ELSE TRUE
        END
        AND CASE
            WHEN created_at_filter IS NOT NULL THEN (
                CASE
                    WHEN created_at_filter ? '_gt' THEN m.created_at > (created_at_filter->>'_gt')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_gte' THEN m.created_at >= (created_at_filter->>'_gte')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_lt' THEN m.created_at < (created_at_filter->>'_lt')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_lte' THEN m.created_at <= (created_at_filter->>'_lte')::timestamptz
                    ELSE TRUE
                END
            )
            ELSE TRUE
        END
        AND -(m.embedding <#> (SELECT normalized_vector FROM normalized_query)) >= match_threshold
    )
    UNION ALL
    (
        SELECT 
            e.id,
            'entity'::text as type,
            e.name as content,
            e.metadata,
            -(e.embedding <#> (SELECT normalized_vector FROM normalized_query)) as similarity
        FROM entities e
        WHERE include_entities = true
        AND CASE
            WHEN metadata_filter IS NOT NULL THEN e.metadata @> metadata_filter
            ELSE TRUE
        END
        AND CASE
            WHEN created_at_filter IS NOT NULL THEN (
                CASE
                    WHEN created_at_filter ? '_gt' THEN e.created_at > (created_at_filter->>'_gt')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_gte' THEN e.created_at >= (created_at_filter->>'_gte')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_lt' THEN e.created_at < (created_at_filter->>'_lt')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_lte' THEN e.created_at <= (created_at_filter->>'_lte')::timestamptz
                    ELSE TRUE
                END
            )
            ELSE TRUE
        END
        AND -(e.embedding <#> (SELECT normalized_vector FROM normalized_query)) >= match_threshold
    )
    ORDER BY similarity DESC
    LIMIT match_count;
$$;

-- Update search_memories function to support entity filtering
DROP FUNCTION IF EXISTS public.search_memories;
CREATE OR REPLACE FUNCTION public.search_memories(
    query_embedding vector(1536),
    match_threshold float8,
    match_count integer,
    filter_agent_id uuid DEFAULT NULL,
    metadata_filter jsonb DEFAULT NULL,
    created_at_filter jsonb DEFAULT NULL,
    expires_at_filter jsonb DEFAULT NULL,
    filter_entity_id uuid DEFAULT NULL
)
RETURNS SETOF public.memories_with_similarity
LANGUAGE sql
STABLE
AS $$
    WITH normalized_query AS (
        SELECT l2_normalize(query_embedding) AS normalized_vector
    )
    SELECT DISTINCT ON (m.id)
        m.id,
        m.agent_id,
        m.content,
        m.metadata,
        m.embedding,
        m.created_at,
        m.updated_at,
        m.expires_at,
        -(m.embedding <#> (SELECT normalized_vector FROM normalized_query)) as similarity
    FROM memories m
    LEFT JOIN entity_memory_links eml ON m.id = eml.memory_id
    WHERE
        CASE 
            WHEN filter_agent_id IS NOT NULL THEN m.agent_id = filter_agent_id
            ELSE TRUE
        END
        AND CASE
            WHEN metadata_filter IS NOT NULL THEN m.metadata @> metadata_filter
            ELSE TRUE
        END
        AND CASE
            WHEN created_at_filter IS NOT NULL THEN (
                CASE
                    WHEN created_at_filter ? '_gt' THEN m.created_at > (created_at_filter->>'_gt')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_gte' THEN m.created_at >= (created_at_filter->>'_gte')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_lt' THEN m.created_at < (created_at_filter->>'_lt')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN created_at_filter ? '_lte' THEN m.created_at <= (created_at_filter->>'_lte')::timestamptz
                    ELSE TRUE
                END
            )
            ELSE TRUE
        END
        AND CASE
            WHEN expires_at_filter IS NOT NULL THEN (
                CASE
                    WHEN expires_at_filter ? '_gt' THEN m.expires_at > (expires_at_filter->>'_gt')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN expires_at_filter ? '_gte' THEN m.expires_at >= (expires_at_filter->>'_gte')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN expires_at_filter ? '_lt' THEN m.expires_at < (expires_at_filter->>'_lt')::timestamptz
                    ELSE TRUE
                END
                AND CASE
                    WHEN expires_at_filter ? '_lte' THEN m.expires_at <= (expires_at_filter->>'_lte')::timestamptz
                    ELSE TRUE
                END
            )
            ELSE TRUE
        END
        AND CASE
            WHEN filter_entity_id IS NOT NULL THEN eml.entity_id = filter_entity_id
            ELSE TRUE
        END
        AND -(m.embedding <#> (SELECT normalized_vector FROM normalized_query)) >= match_threshold
    ORDER BY m.id, -(m.embedding <#> (SELECT normalized_vector FROM normalized_query)) DESC
    LIMIT match_count;
$$;

-- Create sample data insertion function (optional for production)
CREATE OR REPLACE FUNCTION insert_sample_data()
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    agent_id uuid;
    memory1_id uuid;
    memory2_id uuid;
    entity1_id uuid;
    entity2_id uuid;
    test_embedding vector(1536);
BEGIN
    -- Create a test embedding (all 0.1 for simplicity)
    test_embedding := array_fill(0.1, ARRAY[1536]);

    -- Create a test agent with slug
    INSERT INTO public.agents (name, description, metadata, slug)
    VALUES ('Test Agent', 'Agent for testing', '{"purpose": "testing"}'::jsonb, 'test-agent')
    RETURNING id INTO agent_id;

    -- Create test memories
    INSERT INTO public.memories (agent_id, content, metadata, embedding)
    VALUES (
        agent_id,
        'This is a test memory about artificial intelligence and machine learning',
        '{"type": "knowledge", "subtype": "concept", "tags": ["AI", "ML"]}'::jsonb,
        test_embedding
    )
    RETURNING id INTO memory1_id;

    INSERT INTO public.memories (agent_id, content, metadata, embedding)
    VALUES (
        agent_id,
        'Another memory about programming and software development',
        '{"type": "knowledge", "subtype": "concept", "tags": ["programming", "development"]}'::jsonb,
        test_embedding
    )
    RETURNING id INTO memory2_id;

    -- Create test entities
    INSERT INTO public.entities (ref_id, type, name, description, metadata, embedding)
    VALUES (
        'ai-concept',
        'concept',
        'Artificial Intelligence',
        'The field of AI and machine learning',
        '{"domain": "computer_science", "tags": ["technology", "AI"]}'::jsonb,
        test_embedding
    )
    RETURNING id INTO entity1_id;

    INSERT INTO public.entities (ref_id, type, name, description, metadata, embedding)
    VALUES (
        'programming',
        'concept',
        'Programming',
        'The art of software development',
        '{"domain": "computer_science", "tags": ["technology", "development"]}'::jsonb,
        test_embedding
    )
    RETURNING id INTO entity2_id;

    -- Create entity-memory links
    INSERT INTO public.entity_memory_links (entity_id, memory_id, relationship, confidence, metadata)
    VALUES
        (entity1_id, memory1_id, 'about', 0.9, '{"source": "test"}'::jsonb),
        (entity2_id, memory2_id, 'about', 0.95, '{"source": "test"}'::jsonb),
        (entity2_id, memory1_id, 'related_to', 0.7, '{"source": "test"}'::jsonb);

    -- Create a memory edge
    INSERT INTO public.memory_edges (source_memory, target_memory, relationship, weight)
    VALUES (memory1_id, memory2_id, 'related_to', 0.8);

    RETURN 'Sample data inserted successfully';
END;
$$;

-- Track the functions in Hasura
COMMENT ON FUNCTION search_memories_and_entities IS E'@graphql({"type": "Query"})';
COMMENT ON FUNCTION public.search_memories IS E'@graphql({"type": "Query"})';

-- Commit transaction
COMMIT; 