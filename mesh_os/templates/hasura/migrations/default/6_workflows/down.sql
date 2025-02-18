-- Drop trigger first
DROP TRIGGER IF EXISTS update_workflows_updated_at ON public.workflows;

-- Drop table
DROP TABLE IF EXISTS public.workflows; 