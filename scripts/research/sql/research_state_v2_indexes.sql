-- State v2 lookup indexes for the existing governed Supabase table.
-- Apply only through the separately approved database change procedure.
-- CREATE INDEX CONCURRENTLY must run outside an explicit transaction block.
CREATE INDEX CONCURRENTLY IF NOT EXISTS research_proactive_memory_objective_id_idx
    ON public.research_proactive_memory (objective_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS research_proactive_memory_project_id_idx
    ON public.research_proactive_memory ((payload ->> 'project_id'))
    WHERE payload ? 'project_id';

CREATE INDEX CONCURRENTLY IF NOT EXISTS research_proactive_memory_job_id_idx
    ON public.research_proactive_memory ((payload ->> 'job_id'))
    WHERE payload ? 'job_id';

CREATE INDEX CONCURRENTLY IF NOT EXISTS research_proactive_memory_kind_recorded_at_idx
    ON public.research_proactive_memory (memory_kind, recorded_at DESC);
