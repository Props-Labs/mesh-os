-- Create workflows table
CREATE TABLE IF NOT EXISTS public.workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result JSONB DEFAULT NULL,
    result_text TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create trigger for updated_at
CREATE TRIGGER update_workflows_updated_at
    BEFORE UPDATE ON public.workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add status check constraint
ALTER TABLE public.workflows
    ADD CONSTRAINT valid_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'cancelled')
    );

-- Add comment for Hasura GraphQL API
COMMENT ON TABLE public.workflows IS E'@graphql({"type": "Query"})';

-- Add helpful comment about workflow types and statuses
COMMENT ON COLUMN public.workflows.type IS 
'Common workflow types (not restricted):
- embedding: Vector embedding generation
- indexing: Database indexing operations
- search: Search operations
- inference: Model inference tasks
- training: Model training jobs
- import: Data import operations
- export: Data export operations';

COMMENT ON COLUMN public.workflows.status IS
'Available statuses:
- pending: Job is queued
- running: Job is currently executing
- completed: Job finished successfully
- failed: Job encountered an error
- cancelled: Job was cancelled';

COMMENT ON COLUMN public.workflows.metadata IS
'Additional workflow metadata as JSONB. Examples:
- embedding: {"model": "text-embedding-3-small", "input_tokens": 128}
- search: {"query": "search text", "threshold": 0.8}
- training: {"model": "gpt-4", "epochs": 10, "batch_size": 32}
- import: {"source": "file", "format": "csv", "row_count": 1000}';

COMMENT ON COLUMN public.workflows.result IS
'Workflow result as JSONB. Examples:
- embedding: {"embedding": [...], "tokens": 128}
- search: {"matches": [...], "total": 10}
- training: {"loss": 0.001, "accuracy": 0.98}
- error: {"error": "description", "code": "ERROR_CODE"}';

COMMENT ON COLUMN public.workflows.result_text IS
'Plain text result or error message. Useful for:
- Human readable summaries
- Error messages
- Text generation results
- Log outputs'; 