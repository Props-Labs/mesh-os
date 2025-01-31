-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Create agents table
CREATE TABLE IF NOT EXISTS public.agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    data JSONB,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create memories table
CREATE TABLE IF NOT EXISTS public.memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES public.agents(id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL,
    content_vector vector(1536),
    data JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_retrieved TIMESTAMPTZ
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_memories_content_vector ON public.memories 
USING ivfflat (content_vector vector_cosine_ops)
WITH (lists = 100);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON public.agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON public.memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function for vector similarity search
CREATE OR REPLACE FUNCTION search_memories(
    query_vector vector(1536),
    similarity_threshold float8 DEFAULT 0.8,
    max_results integer DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    agent_id UUID,
    memory_type TEXT,
    similarity float8,
    data JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.agent_id,
        m.memory_type,
        1 - (m.content_vector <=> query_vector) as similarity,
        m.data,
        m.metadata,
        m.created_at
    FROM public.memories m
    WHERE m.content_vector IS NOT NULL
    AND 1 - (m.content_vector <=> query_vector) > similarity_threshold
    ORDER BY m.content_vector <=> query_vector
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql STABLE; 