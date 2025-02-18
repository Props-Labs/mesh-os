-- Insert sample type schemas
INSERT INTO type_schemas (type, schema, metadata_schema, embedding_config, chunking_config) VALUES
('text_document', 
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'title', jsonb_build_object('type', 'string'),
            'content', jsonb_build_object('type', 'string')
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'source', jsonb_build_object('type', 'string'),
            'tags', jsonb_build_object('type', 'array', 'items', jsonb_build_object('type', 'string'))
        )
    ),
    jsonb_build_object(
        'model', 'text-embedding-3-small',
        'dimensions', 1536
    ),
    jsonb_build_object(
        'chunk_size', 1000,
        'chunk_overlap', 100
    )
),
('code_snippet', 
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'language', jsonb_build_object('type', 'string'),
            'code', jsonb_build_object('type', 'string')
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'repository', jsonb_build_object('type', 'string'),
            'path', jsonb_build_object('type', 'string'),
            'tags', jsonb_build_object('type', 'array', 'items', jsonb_build_object('type', 'string'))
        )
    ),
    jsonb_build_object(
        'model', 'text-embedding-3-small',
        'dimensions', 1536
    ),
    jsonb_build_object(
        'chunk_size', 500,
        'chunk_overlap', 50
    )
);

-- Insert sample workflow schemas
INSERT INTO workflow_schemas (type, input_schema, output_schema, metadata_schema) VALUES
('document_analysis',
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'document_id', jsonb_build_object('type', 'string'),
            'analysis_type', jsonb_build_object('type', 'string', 'enum', array['sentiment', 'summary', 'key_points'])
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'result', jsonb_build_object('type', 'object'),
            'confidence', jsonb_build_object('type', 'number')
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'model_version', jsonb_build_object('type', 'string'),
            'processing_time', jsonb_build_object('type', 'number')
        )
    )
),
('code_review',
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'code_id', jsonb_build_object('type', 'string'),
            'review_type', jsonb_build_object('type', 'string', 'enum', array['security', 'performance', 'style'])
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'issues', jsonb_build_object('type', 'array'),
            'suggestions', jsonb_build_object('type', 'array')
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'reviewer_version', jsonb_build_object('type', 'string'),
            'review_duration', jsonb_build_object('type', 'number')
        )
    )
);

-- Insert sample memories and their chunks
WITH text_memory AS (
    INSERT INTO memories (type, content, metadata) VALUES
    ('text_document', 
        'The quick brown fox jumps over the lazy dog. This classic pangram contains every letter of the English alphabet at least once.',
        jsonb_build_object(
            'source', 'example_docs',
            'tags', array['pangram', 'example']
        )
    ) RETURNING id, content
),
code_memory AS (
    INSERT INTO memories (type, content, metadata) VALUES
    ('code_snippet',
        'def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)',
        jsonb_build_object(
            'repository', 'algorithms',
            'path', 'math/fibonacci.py',
            'tags', array['python', 'recursion']
        )
    ) RETURNING id, content
)
-- Insert memory chunks for both memories
INSERT INTO memory_chunks (memory_id, chunk_index, content, metadata)
SELECT 
    id,
    0,
    content,
    jsonb_build_object('chunk_type', 'full')
FROM text_memory
UNION ALL
SELECT 
    id,
    0,
    content,
    jsonb_build_object('chunk_type', 'full')
FROM code_memory;

-- Insert sample workflow runs and results
WITH inserted_run AS (
    INSERT INTO workflow_runs (type, status, input, metadata) VALUES
    ('document_analysis',
        'completed',
        jsonb_build_object(
            'document_id', (SELECT id FROM memories WHERE type = 'text_document' LIMIT 1),
            'analysis_type', 'summary'
        ),
        jsonb_build_object(
            'model_version', '1.0.0',
            'processing_time', 0.5
        )
    ) RETURNING id
)
INSERT INTO workflow_results (workflow_id, result, metadata) VALUES
(
    (SELECT id FROM inserted_run),
    jsonb_build_object(
        'summary', 'A pangram demonstrating all English alphabet letters.',
        'confidence', 0.95
    ),
    jsonb_build_object(
        'completion_time', CURRENT_TIMESTAMP,
        'tokens_processed', 15
    )
);

-- Create relationships between memories
INSERT INTO memory_edges (source_memory, target_memory, type, metadata, weight)
SELECT 
    m1.id,
    m2.id,
    'related_content',
    jsonb_build_object(
        'relationship_type', 'example',
        'created_by', 'system'
    ),
    0.8
FROM memories m1
JOIN memories m2 ON m1.type = 'text_document' AND m2.type = 'code_snippet'; 