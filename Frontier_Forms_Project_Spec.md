# Frontier Forms — Technical Project Specification

**Project:** Frontier Forms  
**Purpose:** Fireworks AI hackathon prototype  
**Version:** 1.0 — November 2, 2026  
**Status:** Implementation blueprint; benchmark results not yet measured  
**Primary use case:** Populate healthcare intake forms from a reusable personal data passport  
**Data policy for hackathon:** Synthetic patients only

---

## 1. Executive summary

**Frontier Forms** is an AI-assisted form-completion system. A user maintains a personal data passport containing structured identity, contact, insurance, and healthcare information. When the user opens an intake form, Frontier Forms identifies the requested fields, matches them to facts in the passport, creates a field-by-field completion plan, and fills the form using **reusable, deterministic automation** rather than generating new browser code for each form.

The hackathon experiment tests whether **fine-tuning Qwen3.8-27B for medical form-to-passport mapping** improves accuracy, abstention on missing information, completion time, and cost compared with the same model before fine-tuning. A frontier model may be included as an external comparator, but **the central before-and-after study is untuned versus tuned Qwen with the same tools**.

### One-line pitch

> **Your information, not another blank form.** Frontier Forms uses a specialized AI model and reusable automation tools to accurately complete healthcare forms from a personal data passport, with fewer model calls and less repetitive data entry.

### What makes it different

- **Portable structured passport:** Data is stored once and reused across different form layouts.
- **Specialized mapping model:** Fine-tuned to translate heterogeneous medical questions into verifiable passport facts.
- **Deterministic execution:** Prebuilt form-filling operations handle typing, dropdowns, radio buttons, checkboxes, and validation rather than generating arbitrary scripts.
- **Evidence and abstention:** Every filled clinical field is traceable to a source fact; unknown or conflicting answers are flagged for user review rather than invented.
- **Measured optimization:** Separate the contribution of fine-tuning from the contribution of tool/harness optimization.

### Non-goals for the hackathon

- Live Epic integration or an assertion of Epic certification/compliance.
- Production handling of actual patient information.
- Autonomous submission of medical forms without user confirmation.
- Building a complete EHR, medical diagnosis assistant, or insurance claims platform.
- Running the 27B model on a Raspberry Pi; on-device inference is future work with a smaller model.

---

## 2. The core problem and target user

**Problem:** Patients repeatedly enter demographics, medications, allergies, medical history, insurance details, and contact information into different healthcare portals and paper intake forms. Conventional autofill handles simple names and addresses but does not reliably map clinical concepts, interpret differently worded questions, identify unknowns, or navigate conditional forms.

**Initial target:** A person completing a new-patient clinic intake questionnaire.

**Example:** A synthetic passport contains two active medications, one discontinued medication, a penicillin allergy, a prior surgery, and a current insurance plan. A form asks:

1. "List the medications you currently take."
2. "Do you have any medication allergies?"
3. "Have you undergone surgery before?"
4. "Who is your primary insurer?"
5. "Are you pregnant?" (which may not be answerable from the available record)

The system must fill supported answers, exclude discontinued medications, translate structured records into readable responses, and **ask instead of guessing** when data is missing.

### Business value hypothesis

- Less repeated data entry and fewer transcription errors.
- Better completion of long patient registration forms.
- Lower inference cost and latency than agents that reason and generate fresh automation code for every form.
- Potential for local-first privacy-preserving deployment with appropriately sized future models.

**Do not claim measured savings until they have been benchmarked.**

---

## 3. Hackathon scope and success criteria

### MVP: deliver one end-to-end web form

A user selects a **synthetic patient**, sees their passport, opens a sample medical intake form, selects **Autofill**, reviews a preview of proposed answers and gaps, then clicks **Apply to Form**. The system fills the form, validates results, and displays an evaluation report.

### Stretch goals, in priority order

1. Fine-tuned Qwen model outperforming untuned Qwen on a held-out benchmark.
2. Scanned **PDF/image form** support (extract fields and create a completed, annotated copy).
3. A second distinct HTML form template with conditional fields.
4. A measured comparison with a separate frontier-model baseline.
5. On-device demonstration using a much smaller quantized model, if hardware/time allow.

### Required scientific outputs

- A locked, independently labeled test set.
- Untuned Qwen baseline.
- Fine-tuned Qwen evaluation under **identical input and execution tools**.
- A separate harness ablation that demonstrates the speed benefit from reusable scripts.
- Per-field accuracy, full-form success, unsupported-answer rate, latency distribution, token usage, and cost.
- Exact model identifiers, checkpoints, dataset versions, parameters, and run logs.

### Success criteria (targets, not results)

- The end-to-end MVP successfully completes at least two synthetic intake templates.
- No invented clinical data in the live demo; missing answers require review.
- Test runs are repeatable and exportable as JSON/CSV.
- Fine-tuned accuracy improves over the base model **or**, if it does not, the findings are reported transparently.
- The reusable automation harness performs fewer unnecessary model calls than a free-form scripting baseline.

---

## 4. Sources and what they actually provide

### 4.1 Synthea — synthetic patient generator

Site: https://synthea.mitre.org/about  
Repository: https://github.com/synthetichealth/synthea

Use Synthea to generate synthetic patients and longitudinal clinical facts. It can export **FHIR R4**, C-CDA, and CSV. Relevant resources include `Patient`, `AllergyIntolerance`, `Condition`, `MedicationRequest`, `MedicationStatement` when available, `Observation`, `Encounter`, and `Coverage` when provided by the chosen export configuration. Actual resource availability should be checked per generated bundle.

**Important:** Synthea produces patient records; it does **not** automatically give us thousands of labeled, realistic *form-completion tasks*. We must create the form templates and answer mappings ourselves.

### 4.2 Epic / open.epic — interoperability guidance, not a dataset

Site: https://open.epic.com/TechnicalSpecifications

Use Epic's published FHIR/API specifications as design guidance for portable patient-data schemas and potential future interoperability. Epic describes FHIR resource support, OAuth workflows, and app integrations. We will **not** claim live Epic integration, Epic approval, or compliance based on reading the technical specifications.

### 4.3 Generated form templates

Create our own HTML forms and synthetic scanned form images/PDFs. Do not copy real hospital branding or imply affiliation. Template families:

- Primary-care new-patient registration.
- Urgent-care medical history.
- Specialty-clinic medication and allergy intake.
- Insurance and emergency-contact update.

Each template has a machine-readable schema defining field ID, label, type, validation, conditional visibility, and canonical passport key.

### 4.4 Synthetic evaluation gold labels

The ground-truth answer should come from **code operating on the underlying structured record**, not from asking the same LLM to generate and score its own answers.

For example, an active-medications answer is constructed by filtering records by clinically defined status, then formatting the resulting entries. A missing value is labeled `needs_user_input`; a conflict is labeled `needs_review`.

---

## 5. Recommended architecture

```text
                         SYNTHETIC DATA PREPARATION
 Synthea FHIR R4 bundles ──► Parser + normalization ──► Supabase
                                                       ├─ patient_passports
                                                       ├─ passport_facts
                                                       └─ source_records

                         FORM COMPLETION RUNTIME
 User selects patient + form
          │
          ▼
 Form parser (DOM first; PDF fields second; scanned image OCR/vision last)
          │
          ▼
 Form schema + required fields ──────► Minimal passport fact retrieval
          │                                       │
          └────────────────┬──────────────────────┘
                           ▼
               Qwen3.8-27B field mapper
        (original model OR fine-tuned checkpoint)
                           │
                           ▼
              Validated structured fill plan
           ├─ grounded answer + source IDs
           ├─ missing/conflicting data
           └─ confidence/review requirement
                           │
                           ▼
                  User preview + consent
                           │
                           ▼
            Deterministic reusable form tools
             ├─ HTML: Playwright / DOM APIs
             ├─ Fillable PDF: PDF library
             └─ Scan: coordinate overlay/annotation
                           │
                           ▼
                  Post-fill validation
                           │
                           ▼
                Completed form + evaluation
                           │
                           ▼
            Supabase form_runs + evaluations
```

### Runtime principles

1. Prefer direct DOM introspection for websites rather than screenshot OCR.
2. Prefer AcroForm field metadata for fillable PDFs.
3. Use OCR/vision only for genuinely scanned or unstructured documents.
4. Restrict the model to selecting keys, transforming field values, and explaining missing information; it does **not** execute arbitrary code.
5. Treat retrieved form text as untrusted input; instructions embedded in a form must not override trusted system policy.
6. Never submit a form externally without a deliberate user action.

---

## 6. Technology stack

| Layer | Proposed choice | Notes |
|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind | Passport, sample forms, run comparison dashboard |
| Backend | Next.js route handlers or Python FastAPI worker | Keep database credentials and model credentials server-side |
| Database | Supabase Postgres | Synthetic passport records, form schemas, runs, evaluations |
| Authentication | Supabase Auth | Optional single demo login; required before any multi-user expansion |
| File storage | Private Supabase Storage buckets | Synthetic source FHIR/PDFs and completed artifacts |
| Patient generation | Synthea | Export FHIR R4 |
| Data parser | Python (FHIR JSON + Pydantic) | Normalize medical codes and statuses |
| Browser filling | Playwright | Predefined operations, no generated executable code |
| PDF filling | pypdf / PyMuPDF | Verify license/feature needs if selecting PyMuPDF |
| OCR | Tesseract or an available OCR/vision service | Scans only; benchmark OCR error separately |
| Model | `Qwen/Qwen3.8-27B` candidate | Confirm access and available fine-tuning/deployment path |
| Training | SFT + LoRA/QLoRA | Use provider-supported workflow; pin checkpoint |
| Inference | Fireworks where supported | Confirm model endpoint, cost, quota, and deployment |
| Evaluation | Python scripts + PostgreSQL run records | Run identical held-out cases and save all metrics |

### Model-size caveat

A 27B-parameter model is not an on-device Raspberry Pi solution. The **initial MVP uses cloud-hosted inference** and a browser/client-side executor. For genuine on-device operation, evaluate a separate smaller 1–4B model with quantization; that is a different benchmark and must be labeled accordingly.

---

## 7. Supabase data design

### 7.1 Data ownership

For the hackathon, each dataset patient belongs to a synthetic cohort. In a future production design, **every passport must be associated with its authenticated owner**. Never expose records solely because the client knows a patient ID.

Recommended tables:

| Table | Purpose |
|---|---|
| `patient_passports` | One synthetic person and canonical contact metadata |
| `passport_facts` | Typed, normalized facts with provenance and status |
| `source_records` | FHIR resource references, codes, effective periods, and source metadata |
| `form_templates` | Reusable form schema and modality |
| `form_fields` | Canonical field definitions, types, validators, conditional rules |
| `form_runs` | Patient/template/model combination, execution status, timings |
| `form_answers` | Proposed field values, evidence, final validation, review flags |
| `model_variants` | Base checkpoint, fine-tuned checkpoint, and harness version |
| `evaluation_cases` | Immutable test cases and gold label references |
| `evaluation_results` | Per-model per-case metrics and comparison records |

### 7.2 Initial schema (SQL)

Run through the Supabase SQL editor or a migration after configuring a fresh demo project. This schema is intentionally small enough to implement quickly but preserves source evidence and benchmark lineage.

```sql
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
```

### 7.3 Security and Row Level Security (RLS)

**Do not launch this schema to arbitrary logged-in users without access policies.** By default, we should deny browser access to benchmark and source tables. All writes for the initial synthetic demo can use a **server-side worker** with a restricted credential. No service-role key or database password may be exposed in Next.js client code.

Enable RLS even for the synthetic demo:

```sql
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
```

The initial demo endpoints should only be available to an authorized demo operator and should check ownership on every request. For a real multi-user app, add complete RLS policies (including joins/parent ownership for facts, answers, and runs), separate administrative evaluation access, encryption, retention, deletion flows, and audit logging before considering real data.

### 7.4 Supabase Storage buckets

Use private buckets:

- `synthetic-fhir`: imported Synthea bundles (server worker only).
- `form-templates`: example PDFs/scans/templates.
- `completed-forms`: generated files, preferably short-lived.

Do not create public buckets for patient-related content. Use authenticated access and short-lived signed URLs when necessary. Build cleanup rules for demo artifacts.

---

## 8. Local secrets and Supabase connection

**The supplied chat message did not include the actual connection string. Do not paste a database password into this document, source code, screenshots, Discord, or Git.** Put the correct credentials in local `.env.local` and ensure it is ignored by Git.

### `.env.local.example` (safe to commit)

```dotenv
# Supabase project configuration — safe placeholders only
NEXT_PUBLIC_SUPABASE_URL="https://YOUR_PROJECT_REF.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY"

# Server-only Postgres connection, copied from Supabase Dashboard > Connect
# For short-lived serverless access, prefer the transaction pooler (port 6543).
DATABASE_URL="postgresql://DB_USER:DB_PASSWORD@YOUR_POOLER_HOST:6543/postgres?sslmode=require"

# Direct/session connection for migrations, never sent to the browser
DIRECT_URL="postgresql://DB_USER:DB_PASSWORD@YOUR_DB_OR_SESSION_HOST:5432/postgres?sslmode=require"

# Server-only; omit unless deliberately using admin APIs
SUPABASE_SERVICE_ROLE_KEY="SERVER_ONLY_SECRET"

# Model credentials must also remain server-side
FIREWORKS_API_KEY="SERVER_ONLY_SECRET"
FIREWORKS_BASE_MODEL="Qwen/Qwen3.8-27B"
FIREWORKS_FINETUNED_MODEL="YOUR_DEPLOYED_CHECKPOINT_IDENTIFIER"

# Explicit demo controls
DEMO_SYNTHETIC_ONLY="true"
ALLOW_AUTOMATIC_FORM_SUBMISSION="false"
```

**Note:** Supabase's current connection guidance distinguishes direct (often IPv6), session-pooler (port 5432), and transaction-pooler (port 6543) access. Copy the exact host and username from your dashboard rather than constructing them. For a serverless database driver using transaction pooling, disable prepared statements if required by the driver.

### `.gitignore`

```gitignore
.env
.env.*
!.env.example
!.env.local.example
node_modules/
.next/
artifacts/private/
```

### Connection validation

- Confirm the exact project host and connection mode.
- Confirm the local DB password stays only in `.env.local`.
- Run a server-side `select 1` health check (no returned credentials).
- Apply schema migrations using a direct/session connection.
- Insert a synthetic patient and retrieve it through a server route.
- Ensure client-side code cannot read another user's records.
- Rotate any credential that is accidentally committed or shared.

### Hosting caveat

A local `.env.local` does not magically become available to a Vercel/production deployment. Configure deployment secrets separately in the host's secret manager; do not store real values in the repo. The `NEXT_PUBLIC_` prefix is only for values intended to be sent to the browser.

---

## 9. Canonical passport format

A normalized passport contains medical facts, record status, and provenance. Preserve original FHIR source references rather than merging everything into one untraceable summary.

Example **synthetic** passport:

```json
{
  "synthetic_id": "SYN-00017",
  "demographics": {
    "given_name": "Jordan",
    "family_name": "Rivera",
    "date_of_birth": "1988-04-12",
    "address": { "city": "Sampletown", "state": "MA", "postal_code": "00000" }
  },
  "facts": [
    {
      "fact_key": "allergy.medication",
      "value": { "substance": "penicillin", "reaction": "rash" },
      "status": "known",
      "source": { "resource_type": "AllergyIntolerance", "resource_id": "allergy-31" }
    },
    {
      "fact_key": "medication.active",
      "value": { "name": "Example Drug A", "dose": "10 mg", "frequency": "daily" },
      "status": "known",
      "source": { "resource_type": "MedicationRequest", "resource_id": "med-29" }
    },
    {
      "fact_key": "pregnancy.status",
      "value": null,
      "status": "missing",
      "source": null
    }
  ]
}
```

**Synthetic examples must be clearly labeled** so there is no confusion with real medical records. Do not infer current medication use solely from the existence of an old prescription: define the record-status and effective-date interpretation used by the generator/scorer.

---

## 10. Form schema and model input/output contracts

### 10.1 Example form template

```json
{
  "template_key": "new_patient_intake_v1",
  "modality": "html",
  "fields": [
    {
      "field_key": "patient_name",
      "label": "Full legal name",
      "type": "text",
      "required": true,
      "selector": "[name=patient_name]"
    },
    {
      "field_key": "current_medications",
      "label": "List all medications you currently take",
      "type": "textarea",
      "required": false,
      "selector": "[name=current_medications]"
    },
    {
      "field_key": "medication_allergies",
      "label": "Do you have any medication allergies? If yes, list them",
      "type": "textarea",
      "required": true,
      "selector": "[name=medication_allergies]"
    }
  ]
}
```

### 10.2 Required model output

Return a **structured fill plan**, never generated Playwright/Python code:

```json
{
  "answers": [
    {
      "field_key": "patient_name",
      "decision": "fill",
      "value": "Jordan Rivera",
      "evidence_fact_ids": ["demographics.given_name", "demographics.family_name"],
      "reason": "Name is directly present in the synthetic passport."
    },
    {
      "field_key": "current_medications",
      "decision": "fill",
      "value": "Example Drug A, 10 mg daily",
      "evidence_fact_ids": ["medication.active:med-29"],
      "reason": "Active medication record matched."
    },
    {
      "field_key": "pregnancy_status",
      "decision": "needs_user_input",
      "value": null,
      "evidence_fact_ids": [],
      "reason": "No current answer is available."
    }
  ]
}
```

**Contract requirements:** All returned field keys must appear in the form schema; evidence references must resolve to records from the selected passport; unsupported answers must be rejected. JSON syntax validity is necessary but not sufficient: validate clinical grounding and formatting in code.

### 10.3 Reusable tool interface

Define deterministic tool operations:

```text
inspect_form(form_handle) -> FormSchema
retrieve_passport_facts(passport_id, requested_fact_keys) -> Facts
map_fields(form_schema, facts, model_variant) -> FillPlan
validate_fill_plan(fill_plan, facts, schema) -> ValidatedPlan
preview_fill_plan(validated_plan) -> ReviewSummary
apply_html_form(validated_plan, browser_page) -> ExecutionResult
apply_fillable_pdf(validated_plan, pdf_bytes) -> OutputPDF
annotate_scanned_pdf(validated_plan, scan, field_regions) -> OutputPDF
validate_completed_form(output, expected_plan) -> ValidationResult
```

For web forms, `apply_html_form` should use stable selectors, `fill`, `selectOption`, and `check` operations, wait for conditional fields, and verify resulting values. If selectors are ambiguous, stop and request review rather than guessing.

---

## 11. Data generation and training pipeline

### 11.1 Generate synthetic patients

1. Install/run Synthea in a development environment.
2. Generate an initial cohort of ~100–300 synthetic patients for the hackathon; scale if practical.
3. Export FHIR R4 JSON bundles.
4. Parse each bundle and normalize a fixed subset of resources into passport facts.
5. Store source record IDs and statuses for traceability.
6. Inspect a sampling of output to ensure no unrealistic or malformed facts distort the benchmark.

### 11.2 Generate diverse forms

Build 5–10 HTML templates with different field order, labels, input types, mandatory-field rules, and conditional sections. Create several scanned variants only after HTML works.

For each patient/template pair:

- Generate the expected answer deterministically from the source facts.
- Include `needs_user_input` where a value is genuinely absent.
- Include `needs_review` for intentional conflicts or stale records.
- Generate paraphrased field labels and realistic irrelevant instruction text.
- Avoid presenting the answer key or field-to-fact mapping directly to the model on held-out cases.

### 11.3 Split carefully to prevent leakage

**Important:** Separate *patient identities AND template families* between training/validation/test when possible. The same FHIR record or near-identical form question must not appear with its gold answer in both training and test.

Proposed first pass:

- Train: 70% of synthetic patients and designated training templates.
- Validation: 15% of patients and variant templates.
- Test: 15% of completely held-out patients, with at least one **unseen layout**.

For a six-hour event, reserve at least ~100 evaluation form instances if time permits. Report actual sample sizes; never imply a benchmark is stronger than it is.

### 11.4 Fine-tuning examples

Input: form schema + only relevant passport facts and source references.  
Target: structured field decisions + grounded values + evidence IDs.

Use a consistent schema and high-quality, deterministic labels. Include examples where **abstention is correct**. Keep prompt size constrained by retrieving relevant facts rather than sending an entire FHIR record.

### 11.5 Training recipe

- Baseline model identifier: `Qwen/Qwen3.8-27B` (verify provider availability).
- Training method: SFT using LoRA/QLoRA where supported.
- Start with 1–2 epochs and a conservative learning rate; consult provider recommendations.
- Use early validation checks to avoid memorization and label imbalance.
- Save exact checkpoint ID, adapter settings, seed, optimizer configuration, and training dataset hash.
- Deploy trained checkpoint through the supported endpoint; verify output schema and inference behavior.
- If managed fine-tuning access is unavailable, use an approved accessible training workflow or switch to a supported smaller Qwen model; document the change.

**Do not describe the model as fine-tuned until a training job has actually finished.**

---

## 12. Controlled evaluation plan

### Comparison groups

| ID | Model | Harness | Question answered |
|---|---|---|---|
| A | Base Qwen | Standard structured mapping + deterministic execution | Original open-model performance |
| B | Fine-tuned Qwen | **Identical** mapping inputs + deterministic execution | Does SFT itself improve results? |
| C | Fine-tuned Qwen | Optimized retrieval, batching, validation, reusable tools | What does full-system optimization add? |
| D (optional) | Frontier model | Equivalent structured access/tools | How does the solution compare externally? |
| E (optional) | Frontier model | Free-form generated browser scripts | Different automation paradigm; report separately as non-equivalent tools |

**Critical fairness rule:** Do not compare model A without structured DOM information against model C with DOM information and then attribute all gains to fine-tuning. Distinguish **model improvement** from **harness improvement**.

### Metrics and calculations

1. **Field accuracy** = correct mapped field answers / all scored fields.
2. **Full-form success rate** = forms with all required fields correctly filled / all evaluated forms.
3. **Unsupported-answer rate** = fields containing fabricated or source-unsupported answers / filled fields.
4. **Missing-data recall** = correctly flagged unknown fields / all genuinely unknown fields.
5. **Evidence correctness** = answers with valid source references / answers requiring provenance.
6. **End-to-end latency** = elapsed time from form inspection to validated filled output; report median and P95.
7. **Model latency** = inference processing time independently of browser execution.
8. **Cost per form** = model input/output costs + other metered model/OCR services; separately report compute assumptions for local inference.
9. **Number of model calls** = total invocations per completed form.
10. **Operational failures** = timeouts, selector errors, invalid outputs, validation failures.

**Primary leaderboard metrics:** full-form success rate, unsupported-answer rate, P95 end-to-end latency, and marginal cost per successfully completed form.

### Reproducibility

- Freeze the test dataset and test-form templates before tuning.
- Fix model settings where possible (temperature, output length, prompts).
- Run multiple repetitions (e.g. 3) on the same held-out cases.
- Persist request/response IDs, timestamps, token counts, model versions, evaluation code version, and tool-call counts.
- Never tune prompts or labels directly against the final held-out test after seeing scores; use validation cases for iteration.
- Report uncertainty / small-sample limitations.

### Demo dashboard

Show four rows (A–D if available) and columns for accuracy, full-form completion, unsupported answers, median/P95 latency, calls/form, and estimated cost/form. Make actual measured values visible, with links to a few anonymized synthetic example runs.

---

## 13. UI and user journey

### Screen 1 — Synthetic patient passport

Display demographics, medications, allergies, conditions, and insurance. Mark every patient as synthetic. Each fact may expand to show source and last-updated status.

### Screen 2 — Blank medical intake form

Render a working HTML form with realistic fields and conditional sections. Include a selector for template and patient. Do not connect to any external hospital site during the demo.

### Screen 3 — Autofill preview

Show side-by-side:

- Original blank form.
- Suggested answers (with source record).
- Unanswered / contradictory items.
- Estimated confidence / review requirement (avoid representing confidence as calibrated unless measured).

Buttons: **Review**, **Apply**, **Reset**. The user must explicitly approve before any submission action.

### Screen 4 — Benchmark comparison

Run the fixed evaluation cases through base and fine-tuned variants. Display metrics, a correctness diff, and execution trace. Use accurate labels: **measured**, **estimated**, or **not available**.

---

## 14. Backend API contracts

Example server endpoints (names are suggestions):

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/passports` | GET | List accessible synthetic demo patients |
| `/api/passports/:id` | GET | Return selected passport and source-backed facts |
| `/api/forms/templates` | GET | List available templates |
| `/api/forms/inspect` | POST | Convert form DOM/schema/PDF into normalized fields |
| `/api/forms/map` | POST | Request fill plan from selected model variant |
| `/api/forms/validate` | POST | Check plan against evidence and field schema |
| `/api/forms/apply` | POST | Apply approved plan; no external submission |
| `/api/eval/run` | POST | Launch authorized, rate-limited benchmark batch |
| `/api/eval/results` | GET | Fetch stored model comparison metrics |

All endpoints that handle passport content must enforce authorization server-side. Add limits on payload size, file types, timeouts, and model costs. For this prototype, map and apply can be synchronous while long benchmarks use a job worker.

---

## 15. Suggested repository layout

```text
frontier-forms/
├── README.md
├── .env.local.example
├── .gitignore
├── apps/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── lib/
│       │   ├── supabase/
│       │   ├── forms/
│       │   └── models/
│       └── tests/
├── packages/
│   ├── form-schema/
│   └── fill-tools/
├── scripts/
│   ├── generate_synthea.md
│   ├── import_fhir.py
│   ├── create_forms.py
│   ├── build_gold_labels.py
│   ├── prepare_sft_jsonl.py
│   ├── run_eval.py
│   └── summarize_eval.py
├── training/
│   ├── config.example.yaml
│   └── README.md
├── supabase/
│   └── migrations/
├── data/
│   ├── templates/
│   └── synthetic-samples/
└── docs/
    ├── architecture.md
    └── benchmark-methodology.md
```

Never commit private `.env.local`, raw actual medical information, or service tokens.

---

## 16. Implementation order — hackathon execution

### Phase 0 — Verify resources (first)

- Confirm `Qwen/Qwen3.8-27B` inference and training access in the available account.
- Confirm Supabase connectivity with server-side environment variables.
- Identify team members responsible for dataset, training, form automation, and demo.
- Make one Synthea FHIR record parse successfully.

### Phase 1 — Baseline before training

- Implement canonical form schema and reusable HTML fill operations.
- Create two working HTML forms.
- Import 10–20 synthetic demo patients.
- Implement base Qwen field mapper with structured output.
- Run an initial **validation** benchmark and save results.

### Phase 2 — Generate and train

- Generate a larger synthetic cohort and labeled examples.
- Split by patient/template; freeze held-out test.
- Produce training JSONL.
- Launch LoRA SFT on supported infrastructure.
- If capacity prevents training, keep the baseline/harness demo functional and report the blocker honestly.

### Phase 3 — Evaluate fairly

- Run base Qwen and tuned Qwen with identical harness.
- Apply optimized retrieval/tool harness separately.
- Compute field correctness, abstention, form success, P95 latency, and cost.
- Investigate failures without contaminating final test.

### Phase 4 — Presentation

- Demonstrate a real blank intake form filling from synthetic passport data.
- Show an unknown or conflicting field being left for user review.
- Display before-and-after benchmark charts with real measurements.
- Explain why predefined tools reduce code generation and tool latency.
- State future ambition: private on-device passport, smaller local model, and standards-based EHR import.

### Phase 5 — Only if time remains

- Add scanned form input.
- Add more template variation.
- Add frontier comparator under an explicitly defined fair harness.
- Add alternate smaller local model.

---

## 17. Risks, safeguards, and honest claims

| Risk | Mitigation |
|---|---|
| The model invents an allergy, medication, or medical fact | Evidence-backed generation; schema validation; no fill without verified source |
| "No known allergy" is confused with "allergy status unknown" | Distinct structured statuses; never treat absence of record as a negative answer |
| Older medications are presented as current | Interpret explicit status, time periods, and provenance; ask user on ambiguity |
| OCR misreads scanned fields | Prefer DOM/AcroForm; validate OCR separately and require review |
| Unauthorized exposure of health data | Synthetic-only demo; server-side secrets; RLS; private Storage; owner validation |
| Supposed fine-tuning gains are actually tool gains | A/B same harness first; separate ablations |
| Small synthetic benchmark overstates real-world reliability | Hold out templates/patients; report limitations; avoid clinical accuracy claims |
| Credentials leak to browser or repository | `.env.local`, `.gitignore`, restricted keys, secret scanning |
| Generated browser code executes unsafe instructions | Predefined tool vocabulary only; no arbitrary execution; disable external submission |
| Epic integration is overstated | Describe as FHIR-aligned future architecture, not certified or integrated |
| 27B model cannot fit on Pi | Cloud Qwen experiment now; separate compact model path later |

### Important healthcare boundary

This prototype automates **data entry**, not clinical decision-making. It does not provide diagnosis or clinical recommendations. A user should verify medication, allergy, condition, and insurance details before any form is submitted. Use synthetic information throughout the hackathon.

---

## 18. Final demo script (draft; fill in observed results)

> **The problem:** Everyone keeps filling out the same forms. Healthcare intake forms are especially frustrating because they ask for information that already exists in our records.
>
> **Our solution:** Frontier Forms builds a personal data passport from standardized records. A specialized Qwen model maps that information into any supported intake form; reusable scripts fill the fields without writing fresh automation code each time.
>
> **Our experiment:** We trained an open model on synthetic medical form-mapping tasks generated from Synthea records. We tested the original and fine-tuned versions against identical held-out patients and forms.
>
> **Our results:** [Insert measured change in complete-form success], [unsupported-answer rate], [median and P95 latency], and [cost per completed form]. We also measured the incremental impact of our optimized form executor.
>
> **Why it matters:** Users regain time and control over their information. In the future, a smaller local model could bring this experience to phones and other devices without sending the complete passport to a hosted inference provider.

Do not replace the bracketed results with invented numbers.

---

## 19. Open decisions

1. Is the first benchmark strictly HTML forms, with scanned forms as stretch? **Recommended: yes.**
2. Is the target dataset medical intake fields only? **Recommended: yes, to maximize specialization.**
3. Is the main experimental model Qwen3.8-27B? **Yes if training/inference quota is confirmed.**
4. Do we optimize accuracy or cost as the headline? **Recommendation: complete-form success with unsupported-answer guardrail, then latency and cost.**
5. Will the demo use a local model? **Not with 27B; local inference is future scope or an optional separate smaller-model demo.**
6. Is Supabase storage only a prototype backend, or the long-term "on-device" passport? **Prototype backend now; encrypted/local-first architecture later.**

---

## 20. Reference links

- Synthea: https://synthea.mitre.org/about
- Synthea generator source: https://github.com/synthetichealth/synthea
- Epic interoperability technical specifications: https://open.epic.com/TechnicalSpecifications
- Supabase database connection guidance: https://supabase.com/docs/guides/database/connecting-to-postgres
- Supabase private Storage buckets: https://supabase.com/docs/guides/storage/buckets/fundamentals
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- Microsoft Foundry fine-tuning supported models (verify account availability): https://github.com/microsoft-foundry/fine-tuning/blob/main/interactive_training/docs/supported_models.md

---

**End of specification.**
