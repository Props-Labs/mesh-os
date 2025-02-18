-- Insert sample type schemas
INSERT INTO type_schemas (type, schema, metadata_schema, embedding_config, chunking_config) VALUES
('text_document', 
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'title', jsonb_build_object(
                'type', 'string',
                'description', 'The title or heading of the text document'
            ),
            'content', jsonb_build_object(
                'type', 'string',
                'description', 'The main content or body of the text document'
            )
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'source', jsonb_build_object(
                'type', 'string',
                'description', 'The origin or source of the document'
            ),
            'tags', jsonb_build_object(
                'type', 'array',
                'description', 'List of tags or categories for the document',
                'items', jsonb_build_object('type', 'string')
            )
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
            'language', jsonb_build_object(
                'type', 'string',
                'description', 'The programming language of the code snippet'
            ),
            'code', jsonb_build_object(
                'type', 'string',
                'description', 'The actual code content'
            )
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'repository', jsonb_build_object(
                'type', 'string',
                'description', 'The source repository containing the code'
            ),
            'path', jsonb_build_object(
                'type', 'string',
                'description', 'The file path within the repository'
            ),
            'tags', jsonb_build_object(
                'type', 'array',
                'description', 'List of tags or categories for the code snippet',
                'items', jsonb_build_object('type', 'string')
            )
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
            'document_id', jsonb_build_object(
                'type', 'string',
                'description', 'The unique identifier of the document to analyze'
            ),
            'analysis_type', jsonb_build_object(
                'type', 'string',
                'description', 'The type of analysis to perform on the document',
                'enum', array['sentiment', 'summary', 'key_points']
            )
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'result', jsonb_build_object(
                'type', 'object',
                'description', 'The analysis results for the document'
            ),
            'confidence', jsonb_build_object(
                'type', 'number',
                'description', 'Confidence score of the analysis result'
            )
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'model_version', jsonb_build_object(
                'type', 'string',
                'description', 'Version of the model used for analysis'
            ),
            'processing_time', jsonb_build_object(
                'type', 'number',
                'description', 'Time taken to process the document in seconds'
            )
        )
    )
),
('code_review',
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'code_id', jsonb_build_object(
                'type', 'string',
                'description', 'The unique identifier of the code to review'
            ),
            'review_type', jsonb_build_object(
                'type', 'string',
                'description', 'The type of code review to perform',
                'enum', array['security', 'performance', 'style']
            )
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'issues', jsonb_build_object(
                'type', 'array',
                'description', 'List of identified issues in the code'
            ),
            'suggestions', jsonb_build_object(
                'type', 'array',
                'description', 'List of improvement suggestions for the code'
            )
        )
    ),
    jsonb_build_object(
        'type', 'object',
        'properties', jsonb_build_object(
            'reviewer_version', jsonb_build_object(
                'type', 'string',
                'description', 'Version of the code review system used'
            ),
            'review_duration', jsonb_build_object(
                'type', 'number',
                'description', 'Time taken to complete the code review in seconds'
            )
        )
    )
); 