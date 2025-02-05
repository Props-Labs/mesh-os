-- Drop the existing search_memories function
DROP FUNCTION IF EXISTS public.search_memories;

-- Create the updated search_memories function with metadata filtering
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