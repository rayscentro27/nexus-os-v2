-- Nexus Credit Repair Case Engine
-- Additive only. Reuses existing credit_dispute_items, credit_dispute_letters,
-- credit_report_reviews, and docupost_mail_jobs for live dispute/DocuPost flow.

CREATE TABLE IF NOT EXISTS public.credit_repair_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  client_id text NOT NULL,
  status text NOT NULL DEFAULT 'intake',
  case_goal text NULL,
  current_round integer NOT NULL DEFAULT 1,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.credit_report_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  client_id text NOT NULL,
  case_id uuid NULL REFERENCES public.credit_repair_cases(id),
  bureau text NOT NULL DEFAULT 'other',
  furnisher_name text NULL,
  account_name text NULL,
  account_number_masked text NULL,
  item_type text NOT NULL DEFAULT 'other',
  reported_balance text NULL,
  date_opened text NULL,
  date_reported text NULL,
  reported_status text NULL,
  raw_notes text NULL,
  client_wants_challenged boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.credit_dispute_strategies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  client_id text NOT NULL,
  case_id uuid NULL REFERENCES public.credit_repair_cases(id),
  report_item_id uuid NULL REFERENCES public.credit_report_items(id),
  client_selected_reason text NOT NULL DEFAULT 'not_sure',
  strategy_type text NOT NULL DEFAULT 'bureau_dispute',
  evidence_needed jsonb DEFAULT '[]'::jsonb,
  evidence_uploaded boolean DEFAULT false,
  specialist_status text NOT NULL DEFAULT 'needs_review',
  specialist_notes text NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.credit_dispute_letter_options (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  client_id text NOT NULL,
  case_id uuid NULL REFERENCES public.credit_repair_cases(id),
  report_item_id uuid NULL REFERENCES public.credit_report_items(id),
  strategy_id uuid NULL REFERENCES public.credit_dispute_strategies(id),
  option_type text NOT NULL,
  title text NOT NULL,
  summary text NULL,
  recommended boolean DEFAULT false,
  risk_level text NOT NULL DEFAULT 'medium',
  why_recommended text NULL,
  draft_body text NULL,
  status text NOT NULL DEFAULT 'draft',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.credit_dispute_outcomes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  client_id text NOT NULL,
  case_id uuid NULL REFERENCES public.credit_repair_cases(id),
  report_item_id uuid NULL REFERENCES public.credit_report_items(id),
  strategy_id uuid NULL REFERENCES public.credit_dispute_strategies(id),
  letter_option_id uuid NULL REFERENCES public.credit_dispute_letter_options(id),
  round_number integer NOT NULL DEFAULT 1,
  sent_date date NULL,
  response_due_date date NULL,
  response_received_date date NULL,
  response_result text NOT NULL DEFAULT 'not_sent',
  bureau_or_furnisher text NULL,
  notes text NULL,
  next_recommended_action text NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE public.credit_repair_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_report_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_dispute_strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_dispute_letter_options ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_dispute_outcomes ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'credit_repair_cases_client_select' AND tablename = 'credit_repair_cases') THEN
    CREATE POLICY credit_repair_cases_client_select ON public.credit_repair_cases FOR SELECT TO authenticated
      USING (public.nexus_is_active_admin() OR EXISTS (SELECT 1 FROM public.tenant_memberships tm WHERE tm.tenant_id = credit_repair_cases.tenant_id AND tm.user_id = auth.uid() AND (tm.role IN ('super_admin','admin','operator') OR (tm.role = 'client' AND tm.client_id = credit_repair_cases.client_id))));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'credit_repair_cases_client_insert' AND tablename = 'credit_repair_cases') THEN
    CREATE POLICY credit_repair_cases_client_insert ON public.credit_repair_cases FOR INSERT TO authenticated
      WITH CHECK (public.nexus_is_active_admin() OR EXISTS (SELECT 1 FROM public.tenant_memberships tm WHERE tm.tenant_id = credit_repair_cases.tenant_id AND tm.user_id = auth.uid() AND (tm.role IN ('super_admin','admin','operator') OR (tm.role = 'client' AND tm.client_id = credit_repair_cases.client_id))));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'credit_repair_cases_client_update' AND tablename = 'credit_repair_cases') THEN
    CREATE POLICY credit_repair_cases_client_update ON public.credit_repair_cases FOR UPDATE TO authenticated
      USING (public.nexus_is_active_admin() OR EXISTS (SELECT 1 FROM public.tenant_memberships tm WHERE tm.tenant_id = credit_repair_cases.tenant_id AND tm.user_id = auth.uid() AND (tm.role IN ('super_admin','admin','operator') OR (tm.role = 'client' AND tm.client_id = credit_repair_cases.client_id))))
      WITH CHECK (public.nexus_is_active_admin() OR EXISTS (SELECT 1 FROM public.tenant_memberships tm WHERE tm.tenant_id = credit_repair_cases.tenant_id AND tm.user_id = auth.uid() AND (tm.role IN ('super_admin','admin','operator') OR (tm.role = 'client' AND tm.client_id = credit_repair_cases.client_id))));
  END IF;
END $$;

DO $$
DECLARE
  table_name text;
  policy_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY['credit_report_items','credit_dispute_strategies','credit_dispute_letter_options','credit_dispute_outcomes']
  LOOP
    policy_name := table_name || '_client_select';
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE pg_policies.policyname = policy_name AND pg_policies.tablename = table_name) THEN
      EXECUTE format('CREATE POLICY %I ON public.%I FOR SELECT TO authenticated USING (public.nexus_is_active_admin() OR EXISTS (SELECT 1 FROM public.tenant_memberships tm WHERE tm.tenant_id = %I.tenant_id AND tm.user_id = auth.uid() AND (tm.role IN (''super_admin'',''admin'',''operator'') OR (tm.role = ''client'' AND tm.client_id = %I.client_id))))', policy_name, table_name, table_name, table_name);
    END IF;

    policy_name := table_name || '_client_insert';
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE pg_policies.policyname = policy_name AND pg_policies.tablename = table_name) THEN
      EXECUTE format('CREATE POLICY %I ON public.%I FOR INSERT TO authenticated WITH CHECK (public.nexus_is_active_admin() OR EXISTS (SELECT 1 FROM public.tenant_memberships tm WHERE tm.tenant_id = %I.tenant_id AND tm.user_id = auth.uid() AND (tm.role IN (''super_admin'',''admin'',''operator'') OR (tm.role = ''client'' AND tm.client_id = %I.client_id))))', policy_name, table_name, table_name, table_name);
    END IF;

    policy_name := table_name || '_client_update';
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE pg_policies.policyname = policy_name AND pg_policies.tablename = table_name) THEN
      EXECUTE format('CREATE POLICY %I ON public.%I FOR UPDATE TO authenticated USING (public.nexus_is_active_admin() OR EXISTS (SELECT 1 FROM public.tenant_memberships tm WHERE tm.tenant_id = %I.tenant_id AND tm.user_id = auth.uid() AND (tm.role IN (''super_admin'',''admin'',''operator'') OR (tm.role = ''client'' AND tm.client_id = %I.client_id)))) WITH CHECK (public.nexus_is_active_admin() OR EXISTS (SELECT 1 FROM public.tenant_memberships tm WHERE tm.tenant_id = %I.tenant_id AND tm.user_id = auth.uid() AND (tm.role IN (''super_admin'',''admin'',''operator'') OR (tm.role = ''client'' AND tm.client_id = %I.client_id))))', policy_name, table_name, table_name, table_name, table_name, table_name);
    END IF;
  END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS credit_repair_cases_tenant_client_idx ON public.credit_repair_cases(tenant_id, client_id, status);
CREATE INDEX IF NOT EXISTS credit_report_items_case_idx ON public.credit_report_items(case_id, client_id);
CREATE INDEX IF NOT EXISTS credit_dispute_strategies_item_idx ON public.credit_dispute_strategies(report_item_id, client_id);
CREATE INDEX IF NOT EXISTS credit_dispute_letter_options_item_idx ON public.credit_dispute_letter_options(report_item_id, client_id);
CREATE INDEX IF NOT EXISTS credit_dispute_outcomes_case_idx ON public.credit_dispute_outcomes(case_id, client_id);

GRANT SELECT, INSERT, UPDATE ON public.credit_repair_cases TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.credit_report_items TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.credit_dispute_strategies TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.credit_dispute_letter_options TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.credit_dispute_outcomes TO authenticated;
