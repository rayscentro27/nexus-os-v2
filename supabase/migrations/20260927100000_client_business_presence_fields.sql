-- Client business / digital presence fields
-- Safe additive migration: no drops, no table duplication, no RLS changes.
begin;

alter table public.client_profiles add column if not exists business_website text;
alter table public.client_profiles add column if not exists business_phone text;
alter table public.client_profiles add column if not exists business_email text;
alter table public.client_profiles add column if not exists formation_date date;

alter table public.client_profiles add column if not exists google_business_profile_status text;
alter table public.client_profiles add column if not exists google_business_profile_url text;

alter table public.client_profiles add column if not exists linkedin_business_url text;
alter table public.client_profiles add column if not exists facebook_business_url text;
alter table public.client_profiles add column if not exists instagram_business_url text;
alter table public.client_profiles add column if not exists youtube_channel_url text;
alter table public.client_profiles add column if not exists other_business_social_url text;

alter table public.client_profiles add column if not exists business_address_verification_status text default 'UNKNOWN';
alter table public.client_profiles add column if not exists business_website_verification_status text default 'UNKNOWN';
alter table public.client_profiles add column if not exists business_phone_verification_status text default 'UNKNOWN';
alter table public.client_profiles add column if not exists business_email_verification_status text default 'UNKNOWN';
alter table public.client_profiles add column if not exists google_business_profile_verification_status text default 'UNKNOWN';

commit;
