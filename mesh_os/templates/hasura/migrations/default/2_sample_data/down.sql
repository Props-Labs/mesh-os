-- Remove sample data in reverse order
DELETE FROM memory_edges WHERE metadata->>'created_by' = 'system';
DELETE FROM workflow_results WHERE metadata->>'tokens_processed' = '15';
DELETE FROM workflow_runs WHERE type = 'document_analysis';
DELETE FROM memory_chunks WHERE metadata->>'chunk_type' = 'full';
DELETE FROM memories WHERE type IN ('text_document', 'code_snippet');
DELETE FROM workflow_schemas WHERE type IN ('document_analysis', 'code_review');
DELETE FROM type_schemas WHERE type IN ('text_document', 'code_snippet'); 