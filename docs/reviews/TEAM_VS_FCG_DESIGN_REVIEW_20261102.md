# Frontier Forms — comparative design review and proposed integration gates

**Review ID:** FF-DESIGN-COMPARE-20261102-001  
**Review branch parent:** `main@bba71d8578c30822a8bb546aa06097cd62d0c2ff` (PR #4 merge)  
**Our evidence lane:** [PR #3](https://github.com/biobitworks/frontier-forms/pull/3) @ `da953450d33a721682191f77589c275e0b49731c`  
**Earlier precursor:** [PR #1](https://github.com/biobitworks/frontier-forms/pull/1) @ `46340989d56eaa0b35bb21e52dd2dbdd8e777bae` (draft)  
**Teammate implementation:** [PR #4](https://github.com/biobitworks/frontier-forms/pull/4), merged, last HEAD `08169f932d9ae097c8879936caa3b89e29da6c51`  
**Review scope:** comparison and proposals; **no production schema, importer, user data, or held-out results modified**.

## Recommendation

**Retain PR #4 as the application and ingestion baseline. Integrate PR #3 as a separate append-only evidence and experimental-validation plane.** Do not replace the team's Supabase-backed form system merely to add FCO/FCG/Merkle. Link both with explicit identity, repeatable snapshots, versioned evidence, and public-safe GitHub JSON outbox receipts. Merging PR #3 unchanged is **HOLD** until its two unresolved inline review findings and conflict are resolved.

## Comparison matrix

| Concern | Team implementation (merged PR #4) | Our research/evidence design (open PR #3) | Proposed bridge / admission |
|---|---|---|---|
| End-user experience | Passport, intake form and deterministic automation blueprint | Synthetic image/OCR/FHIR research workflow and notebook contract | Team owns product UI; our harness independently scores same synthetic form tasks |
| Clinical source | Synthea FHIR R4 sample imported to PostgreSQL (helper states 100 living patients) | Historical Synthea CSV and LongBench-related roots, plus proposed Supabase upstream intake | Treat these as **different source versions**; never transfer a CSV-source root to the FHIR database |
| Source identity | `synthea-sample-data-fhir-latest` label, file path and FHIR resource ID; no imported archive digest persisted in schema | SHA-256 source descriptors, original/successor manifests and Merkle verifiers | Source archive SHA-256, per-resource SHA-256, source-version ID, collection/snapshot ID and destination readback |
| Record identity | Random uuid4 IDs for `source_records` and `passport_facts`, deletion/reinsertion on importer rerun | Stable occurrence IDs, append-only successors and typed FCG lineage | Introduce stable source-occurrence identity + versioned immutable custody records; keep operational mutable tables as projections |
| SQL / RLS | Nine SQL tables, RLS enabled in migration; teammate claims deployed rows | No verified live PostgreSQL connection/consistent snapshot in PR #3 | Independently query read-only schema, RLS grants, counts, snapshot, rights and secret rotation |
| Gold oracle | `evaluation_cases.gold_answers` available in proposed schema | Paired discovery flags and label-leakage guardrails; no real EHR holdout scored | New isolated locked synthetic-form gold oracle; train/dev/test disjoint by patient and template family |
| Statistics | Baseline versus tuned Qwen proposed | 38-case prior discovery: 25/38 vs 27/38, exact McNemar p=.6875; paired bootstrap contains zero; **negative** | Paired test on same frozen EHR forms, patient-cluster bootstrap and predeclared guardrails |
| Fireworks/NVIDIA | Provider and tuning plans | Protocols and cost/formula fixtures, live inference NOT_TESTED | Verify actual model/provider endpoint and capture raw response/latency/token/cost receipts |
| Evidence integrity | FHIR relational provenance, no Merkle/FCG commitment | Verified review manifest roots from public Git checkout; underlying private source bytes unavailable here | Canonical byte encoding and actual source-byte readback before signing a new root |
| GitHub writeback | Teammate owns JSON writeback | Versioned public-safe evidence export and receipt protocol | Transactional export outbox → teammate PR → committed-byte hash readback → verified acknowledgement |
| Review / CI | PR #4 merged without observed PR commit workflow runs | PR #3 latest GitHub Actions workflow succeeded and local offline tests PASS | Post-merge importer, migration, privacy and source-integrity gates required |

## Independent review observations (2026-11-02)

### P0 — Stable record identity and append-only provenance are not yet supported

At `scripts/import_fhir.py`, `PassportBuilder.add_source()` and `add_fact()` allocate `uuid.uuid4()`. `import_bundle()` executes `DELETE FROM public.passport_facts` followed by `DELETE FROM public.source_records` and inserts fresh records. Even on byte-identical clinical input, persistent row identifiers change on rerun, so a stored fact ID cannot itself act as a stable FCO/custody identifier. FKs with `ON DELETE CASCADE` and `ON DELETE SET NULL` also cannot preserve the old lineage.

**Executed, read-only proof:** Loaded the actual PR #4 module code with dependency stubs, instantiated two `PassportBuilder` objects using the same in-memory synthetic Patient and AllergyIntolerance bundle, and executed `build_facts()` twice. Result: `IDENTICAL_SOURCE_INPUT=True`, `VALUE_EQUALS=True`, `SOURCE_RECORD_UUID_EQUAL=False`, `FACT_UUID_EQUAL=False`. **Observed identity variance**, not a claim of clinical-value divergence. No database changes were performed.

**Proposed successor:** Do not modify/overwrite the team's operational IDs. Add `source_artifact_versions`, `source_occurrences`, `custody_events`, `snapshot_manifests`, and `export_outbox` in an isolated schema/migration. Key source occurrences using source-file digest + FHIR resourceType/resource ID + source occurrence index and version; hash exact canonical bytes. Retain full immutable historical versions; a changed source produces a successor event. Use constraints, RLS and independent readback. Reject false equivalence between row PK and content hash.

### P0 — Ordinal synthetic IDs can silently reassign patients

`select_bundles()` sorts names and chooses first `--limit 100` living patients; `main()` generates `SYN-{n:05d}` based on current position. A changed source bundle inventory or deceased status can shift all subsequent positions, causing an existing synthetic ID to refer to a different FHIR patient on reimport.

**Proposed successor:** Bind the synthetic ID to the stable original FHIR Patient.id (or frozen mapping manifest), not import order; verify unchanged patient ID-to-bundle mappings and reject remapping unless a new cohort/version is explicitly admitted. Lock cohort selection with an input manifest digest.

### P0 — PR #3 source-root attribution export may accept altered input

Open unresolved [PR #3 review thread](https://github.com/biobitworks/frontier-forms/pull/3) on `scripts/export_private_stats.py:31-32`: the exporter matches case keys/counts and gold values but does **not** recompute the two private source-file byte digests against the frozen descriptors before labeling its output with `frozen_source_root=9e4d4d...`. The reviewer reports a fabricated-source counterexample.

**Proposed successor:** Fail closed on full-byte SHA-256 mismatch for both model-input/result files and the locked split manifest before any public export; add a negative fixture that preserves case keys but alters correctness data; record the precise predecessor descriptor and source version. Do not mark the old review thread resolved until a successor test actually passes.

### P1 — PR #3 notebook reruns overwrite frozen receipts

`scripts/execute_notebooks.py` hard-codes output under `evidence/notebook_runs_v4`. Running the same notebook rewrites timestamped outputs. Its earlier `v3` version had an unresolved inline review warning; the current `v4` still uses a fixed output directory. This can invalidate committed leaf hashes and preserve neither original execution nor successor if re-run in place.

**Proposed successor:** Allocate unique append-only receipt directories per execution, preserve old bytes, and publish a manifest/parent link for each run. CI must not overwrite committed receipts.

### P1 — Current SQL represents a working MVP, not a frozen canonical dataset

The merged `supabase/migrations/20261102000000_initial_schema.sql` creates nine operational tables and enables RLS. It does not implement immutable dataset version/snapshot columns, hash identity, source-row Merkle leaves, dual custody receipts, exclusive writer roles or transactionally verified GitHub export outbox. No row-count or table-privilege verification was performed as part of this review. The teammate's `SUPABASE_Data_Helper_Script.md` **reports** that the migration was applied, 100 living patients and 8,252 source and fact rows imported; those numbers are **reported, not independently queried**.

**Proposed successor:** With fresh rotated credentials and least-privilege read-only role, verify schema/migration status and counts, FK/PK integrity, RLS behavior, source content digests and one repeatable-read snapshot. Preserve SQL migration history separately from actual applied state. No source root can be declared until source bytes and database snapshot data are actually collected and independently hashed.

### P1 — Integration / review state

PR #1 remains a draft baseline; PR #3 remains open with latest head `da953450...`; PR #4 is merged to `main` at `bba71d8578c30822a8bb546aa06097cd62d0c2ff`. `git merge-tree` found an **added-in-both .gitignore** conflict between PR #3 and merged PR #4. Merge policy must preserve PR #4's app ignores and PR #3's privacy/artifact exclusions, not choose one without inspecting patterns.

PR #3 current CI workflow `independent-evidence-check` completed successfully. A separate review checkout executed `scripts/verify_predecessor.py`, `scripts/verify_review_export.py`, `scripts/validate_pair_export.py` and `python3 -m unittest discover -s tests -v`; **16 tests PASS**. Manifest roots (15 leaves; 65, 66, 79 current-review leaves) were recomputed from available Git evidence. The 13 original source-file bytes were **not available in this review checkout**, thus original dataset-byte verification was **NOT_TESTED**, not PASS. Signed MMR, clinical holdout, live Fireworks and NVIDIA are NOT_TESTED.

## Proposed minimal integration sequence

1. **Freeze version and source rights.** Designate a new MITRE FHIR R4 sample cohort as a separate root from PR #3's Synthea CSV/LongBench-related predecessor. Pin archive bytes, selection mapping, template version, licenses and export permissions.
2. **Preserve teammate's runtime.** Keep nine existing Supabase tables. Add append-only custody/provenance tables and grants with a new migration; use non-destructive projections for operational reads.
3. **Repair identity.** Demonstrate stable patient, source occurrence, transform and gold-oracle identities across two clean reimports; prove that changed files cause successor events, not silent overwrites.
4. **Run reproducible scripts.** Canonical JSON roundtrip and two clean-process repeats produce identical output digest under identical source/transform/environment. Store independent origin and destination receipts.
5. **Lock science.** Freeze patient/template-held-out split and gold-oracle digests before comparing Qwen base vs Qwen tuned. Record raw responses and within-model variance. Compare Fireworks JEV and NVIDIA only under task-compatible separate arms.
6. **Evaluate improvement.** Paired exact McNemar on full-form binary correctness, patient-cluster bootstrap for paired effects, predeclared minimum meaningful improvement and unsupported-answer guardrails. Preserve negative results.
7. **Writeback independently.** Approved, public-safe JSON exported to append-only Supabase outbox, then separate teammate GitHub PR/commit, independent committed-byte SHA-256 readback and acknowledgement. No direct commits of patient source bundles, hidden oracle, private credentials or unapproved artifacts.
8. **Admit or hold.** CI, schema/RLS tests, rights, split isolation, independent hash checks and unresolved review findings all PASS before any promotion.

## FCG state tracking proposal

For each run, bind:
`source_bundle_sha256 → source_occurrence_sha256 → transform_code_sha256 → canonical_json_sha256 → dataset_freeze_id → form_template_version → blinded_oracle_ref → model_checkpoint_id + provider → raw_response_sha256 → evaluated_result_sha256 → paired_effect/CI → challenge_receipt → decision → successor_fco`.

Required fields: `event_id, predecessor_event_id, source_sha256, code_commit, input_sha256, output_sha256, model_id, harness_version, evidence_uri, verification_state, decision_state, leaf_index, leaf_sha256, merkle_construction, merkle_root, verifier_id`. Store `NOT_COMPUTED` for missing roots. Preserve red/amber/green/gray views separately from exact reason categories. Hashes prove byte identity; root inclusion alone does not imply causal improvement.

## Current decision

**TEAM BASELINE: RETAIN.**  
**OUR SCIENCE/EVIDENCE LANE: ACCEPT CONCEPT, HOLD MERGE UNTIL REVIEW FINDINGS REMEDIATED.**  
**SUPABASE MIGRATION/COUNTS: REPORTED, NOT INDEPENDENTLY OBSERVED.**  
**DETERMINISTIC IDENTITY: OBSERVED FAIL IN BOUNDED SYNTHETIC REPLAY.**  
**STATISTICAL SUPERIORITY: NEGATIVE (historical discovery only).**  
**NEW EHR INFERENCE, TRAINING, MERKLE SOURCE ROOT, SIGNATURE, MMR, FINAL EXPORT: NOT_TESTED / NOT_COMPUTED.**

### TURN_BREAKPOINT

`ID=FF-DESIGN-COMPARE-20261102-001 | PARENT=main@bba71d8 + PR1@46340989 + PR3@da953450 + PR4@08169f93 | VERIFIED_NEW=PR statuses, branch contents, merge-tree conflict, importer identity challenge | EXECUTED=remote clone/fetch, public Git-derived verifiers, 16 unit tests, importer synthetic identity replay | OBSERVED=reported Supabase rows only; source/value UUIDs vary with identical input; historical discovery negative | DECISIONS=retain team build and propose additive FCG layer | PROPOSED=append-only schema, stable identity, freeze+oracle+evaluation+outbox gates | NOT_TESTED=DB readback, production import, Fireworks/NVIDIA, held-out EHR performance | FAILURES=import identity stability; two unresolved PR3 review findings | UNRESOLVED=source bytes, credential rotation, schema state, .gitignore conflict | NEXT_ACTION=separate owner-review and successors; no automatic merge`.
