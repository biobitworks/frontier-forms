-- Initial Frontier Forms schema (Project Spec §7.2) + RLS (§7.3).

create extension if not exists pgcrypto;

create table public.patient_passports (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references auth.users(id) on delete cascade,
  synthetic_id text unique not null,
  display_name text not null,
  demographics jsonb not null default '{}'::jsonb,
  contact jsonb not null default '{}'::jsonb,
  insurance jsonb not null default '{}'::jsonb,
  is_synthetic boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint hackathon_synthetic_only check (is_synthetic = true)
);

create table public.source_records (
  id uuid primary key default gen_random_uuid(),
  passport_id uuid not null references public.patient_passports(id) on delete cascade,
  fhir_resource_type text not null,
  fhir_resource_id text,
  clinical_code text,
  effective_at timestamptz,
  source_file_path text,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create table public.passport_facts (
  id uuid primary key default gen_random_uuid(),
  passport_id uuid not null references public.patient_passports(id) on delete cascade,
  source_record_id uuid references public.source_records(id) on delete set null,
  fact_key text not null,
  value jsonb not null,
  value_type text not null default 'string',
  status text not null default 'known'
    check (status in ('known','missing','conflicted','expired','needs_confirmation')),
  valid_from timestamptz,
  valid_until timestamptz,
  created_at timestamptz not null default now()
);

create index passport_facts_passport_key_idx
  on public.passport_facts(passport_id, fact_key);

create table public.form_templates (
  id uuid primary key default gen_random_uuid(),
  template_key text not null unique,
  name text not null,
  modality text not null check (modality in ('html','fillable_pdf','scan')),
  schema_version text not null default '1',
  schema jsonb not null,
  file_path text,
  created_at timestamptz not null default now()
);

create table public.model_variants (
  id uuid primary key default gen_random_uuid(),
  variant_key text not null unique,
  base_model text not null,
  checkpoint_id text,
  fine_tuned boolean not null default false,
  harness_version text not null,
  decoding_settings jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.form_runs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references auth.users(id) on delete cascade,
  passport_id uuid not null references public.patient_passports(id) on delete cascade,
  template_id uuid not null references public.form_templates(id),
  model_variant_id uuid references public.model_variants(id),
  status text not null default 'draft'
    check (status in ('draft','mapped','needs_review','applied','validated','failed')),
  fill_plan jsonb not null default '{}'::jsonb,
  metrics jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create table public.form_answers (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.form_runs(id) on delete cascade,
  field_key text not null,
  proposed_value jsonb,
  decision text not null
    check (decision in ('fill','needs_user_input','needs_review','skip')),
  evidence_fact_ids uuid[] not null default '{}',
  validation_status text not null default 'pending',
  error_code text,
  unique(run_id, field_key)
);

create table public.evaluation_cases (
  id uuid primary key default gen_random_uuid(),
  case_key text not null unique,
  split text not null check (split in ('train','validation','test')),
  dataset_version text not null,
  passport_id uuid not null references public.patient_passports(id),
  template_id uuid not null references public.form_templates(id),
  gold_answers jsonb not null,
  frozen boolean not null default false
);

create table public.evaluation_results (
  id uuid primary key default gen_random_uuid(),
  evaluation_case_id uuid not null references public.evaluation_cases(id),
  model_variant_id uuid not null references public.model_variants(id),
  repetition integer not null default 1,
  predicted_answers jsonb not null,
  metrics jsonb not null,
  completed_at timestamptz not null default now(),
  unique(evaluation_case_id, model_variant_id, repetition)
);

alter table public.patient_passports enable row level security;
alter table public.source_records enable row level security;
alter table public.passport_facts enable row level security;
alter table public.form_templates enable row level security;
alter table public.model_variants enable row level security;
alter table public.form_runs enable row level security;
alter table public.form_answers enable row level security;
alter table public.evaluation_cases enable row level security;
alter table public.evaluation_results enable row level security;

-- Sample owner-only passport read for a future authenticated app.
-- All other client access remains denied until explicit policies are added.
create policy "passport owners can read own passport"
on public.patient_passports for select to authenticated
using (owner_id = (select auth.uid()));

create index source_records_passport_idx
  on public.source_records(passport_id);
