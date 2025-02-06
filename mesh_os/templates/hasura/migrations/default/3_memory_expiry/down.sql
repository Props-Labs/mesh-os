-- Drop the updated search_memories function
DROP FUNCTION IF EXISTS public.search_memories(vector(1536), float8, integer, uuid, jsonb, jsonb, jsonb);

-- Remove expires_at column
ALTER TABLE public.memories DROP COLUMN expires_at;

-- Drop and recreate the view without expires_at
DROP VIEW IF EXISTS public.memories_with_similarity;
CREATE OR REPLACE VIEW public.memories_with_similarity AS
SELECT 
    m.*,
    0::float8 as similarity
FROM memories m;

-- Restore the previous version of search_memories from 2_metadata_filtering
CREATE OR REPLACE FUNCTION public.search_memories(
    query_embedding vector(1536),
    match_threshold float8,
    match_count integer,
    filter_agent_id uuid DEFAULT NULL,
    metadata_filter jsonb DEFAULT NULL
)
RETURNS SETOF public.memories_with_similarity
LANGUAGE sql
STABLE
AS $$
    WITH normalized_query AS (
        SELECT l2_normalize(query_embedding) AS normalized_vector
    )
    SELECT 
        m.id,
        m.agent_id,
        m.content,
        m.metadata,
        m.embedding,
        m.created_at,
        m.updated_at,
        -(m.embedding <#> (SELECT normalized_vector FROM normalized_query)) as similarity
    FROM memories m
    WHERE
        CASE 
            WHEN filter_agent_id IS NOT NULL THEN m.agent_id = filter_agent_id
            ELSE TRUE
        END
        AND CASE
            WHEN metadata_filter IS NOT NULL THEN m.metadata @> metadata_filter
            ELSE TRUE
        END
        AND -(m.embedding <#> (SELECT normalized_vector FROM normalized_query)) >= match_threshold
    ORDER BY -(m.embedding <#> (SELECT normalized_vector FROM normalized_query)) DESC
    LIMIT match_count;
$$;

-- Track the function in Hasura
COMMENT ON FUNCTION public.search_memories IS E'@graphql({"type": "Query"})'; 