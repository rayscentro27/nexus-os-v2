-- Nexus Credit Repair Workflow v1
-- Adds credit report reviews, dispute items, dispute letters, and DocuPost mail jobs.
-- Additive only. No RLS changes to existing tables.

-- 1. credit_report_reviews
CREATE TABLE IF NOT EXISTS public.credit_report_reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  client_id text NOT NULL,
  document_id uuid NULL,
  assigned_specialist text NULL,
  status text NOT NULL DEFAULT 'pending_review',
  review_notes text NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE public.credit_report_reviews ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'client_read_own_credit_report_reviews' AND tablename = 'credit_report_reviews') THEN
    CREATE POLICY client_read_own_credit_report_reviews ON public.credit_report_reviews
      FOR SELECT USING (
        client_id IN (SELECT client_id FROM public.tenant_memberships WHERE user_id = auth.uid())
      );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'admin_all_credit_report_reviews' AND tablename = 'credit_report_reviews') THEN
    CREATE POLICY admin_all_credit_report_reviews ON public.credit_report_reviews
      FOR ALL USING (public.nexus_is_active_admin());
  END IF;
END $$;

-- 2. credit_dispute_items
CREATE TABLE IF NOT EXISTS public.credit_dispute_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  client_id text NOT NULL,
  review_id uuid NULL REFERENCES public.credit_report_reviews(id),
  bureau text NOT NULL DEFAULT 'unknown',
  furnisher_name text NULL,
  account_name text NULL,
  account_number_mask text NULL,
  item_type text NULL,
  dispute_reason text NULL,
  factual_basis text NULL,
  requested_action text NULL,
  evidence_document_ids jsonb DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'identified',
  specialist_notes text NULL,
  client_visible boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE public.credit_dispute_items ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'client_read_own_dispute_items' AND tablename = 'credit_dispute_items') THEN
    CREATE POLICY client_read_own_dispute_items ON public.credit_dispute_items
      FOR SELECT USING (
        client_id IN (SELECT client_id FROM public.tenant_memberships WHERE user_id = auth.uid())
      );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'admin_all_dispute_items' AND tablename = 'credit_dispute_items') THEN
    CREATE POLICY admin_all_dispute_items ON public.credit_dispute_items
      FOR ALL USING (public.nexus_is_active_admin());
  END IF;
END $$;

-- 3. credit_dispute_letters
CREATE TABLE IF NOT EXISTS public.credit_dispute_letters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  client_id text NOT NULL,
  dispute_item_ids jsonb DEFAULT '[]'::jsonb,
  recipient_type text NOT NULL DEFAULT 'bureau',
  recipient_name text NULL,
  letter_body text NOT NULL,
  status text NOT NULL DEFAULT 'draft',
  generated_by text DEFAULT 'nexus_draft_engine',
  approval_required boolean DEFAULT true,
  client_approved_at timestamptz NULL,
  specialist_approved_at timestamptz NULL,
  docupost_job_id text NULL,
  sent_at timestamptz NULL,
  response_due_at timestamptz NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE public.credit_dispute_letters ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'client_read_own_dispute_letters' AND tablename = 'credit_dispute_letters') THEN
    CREATE POLICY client_read_own_dispute_letters ON public.credit_dispute_letters
      FOR SELECT USING (
        client_id IN (SELECT client_id FROM public.tenant_memberships WHERE user_id = auth.uid())
      );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'admin_all_dispute_letters' AND tablename = 'credit_dispute_letters') THEN
    CREATE POLICY admin_all_dispute_letters ON public.credit_dispute_letters
      FOR ALL USING (public.nexus_is_active_admin());
  END IF;
END $$;

-- 4. docupost_mail_jobs
CREATE TABLE IF NOT EXISTS public.docupost_mail_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  client_id text NOT NULL,
  letter_id uuid NULL REFERENCES public.credit_dispute_letters(id),
  provider text NOT NULL DEFAULT 'docupost',
  provider_job_id text NULL,
  status text NOT NULL DEFAULT 'not_sent',
  recipient_name text NULL,
  recipient_address jsonb DEFAULT '{}'::jsonb,
  mail_type text DEFAULT 'certified',
  tracking_number text NULL,
  request_payload jsonb DEFAULT '{}'::jsonb,
  response_payload jsonb DEFAULT '{}'::jsonb,
  error_message text NULL,
  approval_required boolean DEFAULT true,
  approved_by_client boolean DEFAULT false,
  approved_by_specialist boolean DEFAULT false,
  queued_at timestamptz NULL,
  mailed_at timestamptz NULL,
  delivered_at timestamptz NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE public.docupost_mail_jobs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'client_read_own_mail_jobs' AND tablename = 'docupost_mail_jobs') THEN
    CREATE POLICY client_read_own_mail_jobs ON public.docupost_mail_jobs
      FOR SELECT USING (
        client_id IN (SELECT client_id FROM public.tenant_memberships WHERE user_id = auth.uid())
      );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'admin_all_mail_jobs' AND tablename = 'docupost_mail_jobs') THEN
    CREATE POLICY admin_all_mail_jobs ON public.docupost_mail_jobs
      FOR ALL USING (public.nexus_is_active_admin());
  END IF;
END $$;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_credit_report_reviews_client ON public.credit_report_reviews(client_id);
CREATE INDEX IF NOT EXISTS idx_credit_dispute_items_client ON public.credit_dispute_items(client_id);
CREATE INDEX IF NOT EXISTS idx_credit_dispute_items_review ON public.credit_dispute_items(review_id);
CREATE INDEX IF NOT EXISTS idx_credit_dispute_letters_client ON public.credit_dispute_letters(client_id);
CREATE INDEX IF NOT EXISTS idx_docupost_mail_jobs_client ON public.docupost_mail_jobs(client_id);
CREATE INDEX IF NOT EXISTS idx_docupost_mail_jobs_letter ON public.docupost_mail_jobs(letter_id);
