-- Credit Report Parser Results
-- Stores parser preview output for uploaded credit reports.
-- Admin-only access. No client-facing access yet.

CREATE TABLE IF NOT EXISTS public.credit_report_parser_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  client_id text NOT NULL,
  document_id text NULL,
  source_file_name text,
  source_storage_path text,
  parser_version text,
  extraction_mode text,
  extraction_success boolean DEFAULT false,
  text_length integer DEFAULT 0,
  confidence text,
  bureaus_detected jsonb DEFAULT '[]'::jsonb,
  accounts jsonb DEFAULT '[]'::jsonb,
  inquiries jsonb DEFAULT '[]'::jsonb,
  personal_info_variations jsonb DEFAULT '[]'::jsonb,
  utilization_summary jsonb DEFAULT '{}'::jsonb,
  negative_candidates jsonb DEFAULT '[]'::jsonb,
  structured_item_drafts jsonb DEFAULT '[]'::jsonb,
  dispute_strategy_suggestions jsonb DEFAULT '[]'::jsonb,
  letter_preview text,
  warnings jsonb DEFAULT '[]'::jsonb,
  status text DEFAULT 'suggested_extraction',
  needs_specialist_review boolean DEFAULT true,
  reviewed_by text,
  reviewed_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE public.credit_report_parser_results ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'credit_report_parser_results_admin_select' AND tablename = 'credit_report_parser_results') THEN
    CREATE POLICY credit_report_parser_results_admin_select ON public.credit_report_parser_results FOR SELECT TO authenticated
      USING (public.nexus_is_active_admin());
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'credit_report_parser_results_admin_insert' AND tablename = 'credit_report_parser_results') THEN
    CREATE POLICY credit_report_parser_results_admin_insert ON public.credit_report_parser_results FOR INSERT TO authenticated
      WITH CHECK (public.nexus_is_active_admin());
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'credit_report_parser_results_admin_update' AND tablename = 'credit_report_parser_results') THEN
    CREATE POLICY credit_report_parser_results_admin_update ON public.credit_report_parser_results FOR UPDATE TO authenticated
      USING (public.nexus_is_active_admin())
      WITH CHECK (public.nexus_is_active_admin());
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS credit_report_parser_results_document_idx ON public.credit_report_parser_results(document_id, client_id);
CREATE INDEX IF NOT EXISTS credit_report_parser_results_tenant_client_idx ON public.credit_report_parser_results(tenant_id, client_id, created_at);

GRANT SELECT, INSERT, UPDATE ON public.credit_report_parser_results TO authenticated;
