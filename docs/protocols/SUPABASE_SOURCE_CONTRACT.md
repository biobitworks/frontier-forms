# Supabase source-intake and versioned freeze protocol

## Current epistemic state (2026-11-02)

The user reports a **dataset is being built on Supabase**. Its project reference, schema, tenancy, row count, database transaction snapshot, sensitivity, license and linkage to Synthea/Frontier Forms are **UNKNOWN**. No live connection or SQL query has been executed for this lane. It is therefore an upstream candidate, not an observed frozen dataset. No source-data Merkle root can be computed from a project description.

**Source designation**: SUPABASE-LIVE-UPSTREAM-UNIDENTIFIED.  
**Status**: REPORTED / IN_PROGRESS.  
**Data export**: NOT_AUTHORIZED (pending rights and privacy verification).  
**Current FCG edge**: PROPOSED_SOURCE_FOR → Frontier Forms EHR intake (NOT_TESTED).
**Predecessor**: original 15-leaf root 9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a. Existing 66-leaf public review successor root 513cb1f8e83d0eae653c94000552fa6680b37827bcc8100af35fed3fc7d0f730; neither must be overwritten.

## Prerequisites: observe before committing

Confirm project reference without sharing service_role keys; read-only access, database schema and version; origin of all underlying records and licenses; source-to-Synthea mapping if one exists; whether any PHI/PII is present; exact public-export classification; table RLS policies and permissions; and whether a synthetic-only isolated staging schema exists.

Do not publish database URLs with credentials or snapshot rows. A connected Supabase app can list/inspect the project after authorization. Discovery itself is a separate observation receipt, never a row-count claim without an actual query.

## Atomic freeze recipe

1. Record source project ID (nonsecret), schema names, migration history/version, PostgreSQL server version, timestamp UTC and table allowlist.
2. For each freeze, obtain a **single consistent database snapshot**. Use a read-only REPEATABLE READ transaction, or a properly configured consistent pg_dump with a recorded snapshot/reference and transaction controls. Avoid paging live tables across independent transactions. Record visibility/locking limitations.
3. Export only approved synthetic rows from explicitly allowlisted tables to a private, access-controlled area. Capture stable table/PK identity, explicit null representation, normalized numeric/UTC timestamp handling, Unicode/JSON encoding, and logical source version. Review logical schema drift, row totals, duplicate PKs, missing fields, FK violations and rejected occurrences.
4. Canonicalize a documented schema descriptor and per-occurrence records; compute byte hashes of the exact export bytes and deterministic row FCOs. Compute binary Merkle root from **actually materialized leaves and declared order**, record inclusion proofs. Store original archive identity separately; hashes do not establish clinical truth.
5. Create snapshot FCO with source transaction/LSN or repeatable-read snapshot metadata, transform code/version, source and output digests, occurrence count, rights and claim ceiling. Append typed FCG edges from source → row occurrence → transformed form → label → answer → evaluation. If latest records mutate, create a new successor snapshot and a SUPERSEDES edge; never change predecessor.
6. For longitudinal monitoring, compare consecutive frozen snapshots using stable row identities and timestamp/version evidence. Track additions, modifications, deletions, unresolved conflicts and downstream invalidation. A data changed event does **not** itself prove why it changed.
7. Gate model training and evaluation from exact snapshots only. Split by patient/entity identity and form-template family to prevent leakage; never train on frozen final holdout. Maintain label availability and blinded oracle separate from model inputs.
8. After independent FCO/FCG root replay, source hash validation, semantic mapping/rights review, test notebook and security checks, authorize a frozen SNAPSHOT. Never claim a live table itself is immutable.

## Controlled metrics

At each snapshot/breakpoint record row count, missingness, duplicates, PK/FK integrity, schema drift, valid clinical code coverage, label completeness, classification base rates, field extraction exact match, precision/recall/F1, FPR/FDR/FNR when class-definitions permit, AUROC only with continuous scores, McNemar only for same cases, stratified paired bootstrap with seeded resamples, abstention, source-span evidence, and model token/cost receipts. The source data gate is **independent** of Fireworks/Snyk/Lean/GSigmaD execution.

A broken upstream leaf blocks downstream claims at that leaf and all dependent FCG descendants, without deleting old outputs. Register a SUCCESSOR only after the replacement bytes and proofs are actually recomputed. Do not invent canonical roots, signed events or MMR peaks.

## Follow-on integration

Supabase is the **source of synthetic patient/form data only if separately verified**; MITRE Synthea is a potential input generator, not synonymous with the Supabase tables; Epic remains an interface specification; Fireworks is the serverless model evaluation provider; NVIDIA Megatron is a training framework. Nothing here asserts that the Supabase dataset contains OCR-labeled scans, is a clinical dataset, or is owned by Frontier Forms.
