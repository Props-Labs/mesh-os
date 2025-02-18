-- Remove sample data in reverse order
DELETE FROM workflow_schemas WHERE type IN ('document_analysis', 'code_review');
DELETE FROM type_schemas WHERE type IN ('text_document', 'code_snippet'); 