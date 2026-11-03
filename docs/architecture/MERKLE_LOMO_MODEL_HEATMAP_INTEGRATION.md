# Frontier Forms — unified Merkle × LOMO × model impact contract

Status: IMPLEMENTED documentation integration; cross-lane replay NOT_TESTED. Parent main commit: c137b5893d2b1c952a1b089208c12bb24fdaaf26. No model gain claimed by this document.

## Existing views (retain as predecessors)
- experiments/form_error_factorial/heatmap.html — 16 synthetic fault-injection module combinations, 10/30/100 patients.
- dashboard/training_progress.html — model identities, weight-hash availability, paired training observations.
- dashboard/training_heatmap.html — longitudinal evidence status and predecessor references.
- evidence/forms_detectors/run_v1/heatmap.html — synthetic detector error-class recall.
These views measure distinct populations/estimands and MUST NOT be merged into a single numeric improvement without case-level paired joins.

## Canonical join grain
One row per (run_id, synthetic_patient_leaf_sha256, form_template_sha256, field_key, model_id, model_weights_sha256_or_null, module_mask, comparator_mask, evaluation_version). Store cohort_merkle_root, passport_transform_sha256, plan_sha256, server_echo_sha256, oracle_sha256, outcome_sha256, pdf_sha256_or_null, predecessor_receipt_sha256, timestamps, case_split and synthetic-only rights attestation. Null is not a string hash. Roots must be recomputed from canonical bytes and declared leaf ordering; never synthesize missing roots.

## Admission rules
1. Verify source patient leaf → frozen cohort root → template → FHIR/passport → prediction → HTTP echo → independently scored oracle → outcome → PDF preview (when present).
2. Separate rule-based deterministic modules (weights NOT_APPLICABLE) from neural checkpoints (exact-byte weights hash REQUIRED for attribution).
3. For each LOMO removal, hold patient, template, oracle, model weights, decoding parameters and split fixed. Record discordant paired counts b/c, exact two-sided McNemar, patient-cluster bootstrap CI, effect size and denominator.
4. Distinguish detector injected-error recall from full-form clinical field correctness; never compare these as the same endpoint.
5. Heatmap status enum: PROPOSED, IMPLEMENTED, EXECUTED, OBSERVED, SUPPORTED, PASS, FAILED, NEGATIVE, NULL, DEFERRED, NOT_TESTED, UNKNOWN, NOT_COMPUTED. PASS for provenance does not imply model gain.
6. Drill-down on each cell must show model/weight hash, changed module, source leaf, root, oracle rule, wrong fields, PDF digest, receipt, reviewer, timestamp, and exact command.
7. Colors: green verified PASS; red FAILED; orange NEGATIVE; amber unresolved/unknown; gray NOT_TESTED/DEFERRED; blue observed without promotion. Keep text labels accessible.
8. Public outputs: synthetic-only permitted JSON; do not add PNG/PDF/HTML/JSONL/weights or real PHI. Respect immutable legacy exceptions without treating them as permission for new publication.

## Existing observations — not a new replay
Earlier evidence check reported B0 18/54 versus added modules 30/54 full-form success, 12 improved and 0 worsened, McNemar p=0.000488; discovery-grade only. Independent B0 sample reported 18/90 field mismatches, particularly allergies, units, and disorder versus social finding. New prospective LOMO and weight-specific effects NOT_TESTED.

## Next implementation gate
Implement JSON-only normalized join export and a locally generated dashboard reading that export. Run current-main test suite and exact-byte root verification, then independent review. No auto-merge. Do not contaminate Vita DAISY or Cloudmer.
