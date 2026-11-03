# Frontier Forms — all-outcome and promotion ledger

**Status:** integrated source inventory of pre-existing Frontier Forms synthetic observations; **no new model execution or scientific admission**. Initial V1 source commit: `5d8b784e950b89c0453d8a13ff91451e41764dfd`.

## Open the public-safe local/GitHub dashboard

```sh
python3 -m http.server 8787 --bind 127.0.0.1
# http://127.0.0.1:8787/dashboard/outcome_promotion_ledger.html
```

The dashboard displays all 24 source events plus 48 synthetic teammate-hosted benchmark runs (24 matched cases) without dropping negative, null or positive-discovery rows, includes a filterable judge workstream matrix, and indexes versioned committed JSON/JSONL source files by **file path and exact SHA-256** (not duplicate record contents). Each source record contains its unmodified source event ID, parent/child, status, paired statistics where available, model-weight digest if actual, and source event hash.

## Full scientific result accounting

| Historical evidence classification | Count | Admission interpretation |
|---|---:|---|
| DISCOVERY_POSITIVE_NOT_PROMOTED | 8 | Positive on source challenges but not independently replicated; **not admitted** |
| NEGATIVE_OR_TIE | 10 | Negative or no observed difference; preserved |
| NEGATIVE_NO_GAIN | 4 | Trained vision and other model comparators fail to improve baseline; preserved |
| OBSERVED_BASELINE_ONLY | 1 | Qwen SFT epoch-0 telemetry only; no trained adapter effect |
| NOT_COMPUTED | 1 | Vita DAISY methodology-only bridge; no transferred weights, results or root |

**Scientific admissions: zero.** This does not mean no engineering work was completed. Commits and PR merges are engineering integration—not proof of better clinical answers.

## Evidence boundaries and verification

- Parent source snapshot: `dashboard/training_progress_latest.json` → `evidence/training_progress/OBS-20261102T225623Z-a38f4704aa6e/`; existing snapshot Merkle root reused but **not reinvented**.
- B0: `evidence/forms_b0/B0_FREEZE_V1.json`, 100 distinct synthetic MITRE Synthea patients (as recorded), FROZEN_PENDING_PI_REVIEW.
- Gate: `evidence/admission/FF_FCAR_GATE_ASSESSMENT_V1.json`; exact scientific status **HOLD_NO_INDEPENDENT_PI_ADMISSION**. Replication `NOT_TESTED`.
- Vita DAISY is an abstract reference for freeze, challenge, replicate, admit; no Vita DAISY weights, measured gains, dataset or Merkle root are imported into Frontier Forms.
- `file_inventory_merkle_root` or `inventory_sha256_merkle_root` commits the indexed list of exact file-byte SHA-256 digests using the declared leaf/node recipes. **This does not establish causality, statistical significance, patient truth or approval.**
- open.epic provides interoperability specifications; MITRE Synthea provides synthetic source patient records. No production EHR data.
- Paths may refer to already-public historical PNG/PDF-derived JSON as hashed metadata, but the new PR does **not** upload new binary images, PDFs, model checkpoints or individual synthetic FHIR values.
- The index can become stale as teammates commit: preserve this as a predecessor and create `OUTCOMES_AND_PROMOTIONS_*_V2.json` using a fresh checkout. Do not overwrite V1.

## Reproduce this exact index

```sh
python3 scripts/build_outcome_ledger.py  # on frozen predecessor checkout only; immutable successors refuse overwrite
python3 -m unittest discover -s tests -p test_outcome_promotion_ledger.py -v
python3 scripts/check_synthetic_json_policy.py
python3 scripts/check_fcar_admission.py
```

The generator is strictly **read-only with respect to source evidence**; it writes only the new immutable JSON, and refuses to replace it with different bytes. No training, model inference, independent experiment or new statistical bootstrap is executed. The existing reported statistical values are transparently preserved as source records.

## Next scientific work

**PROPOSED, NOT EXECUTED:** preregister a fresh synthetic patient/form-layout cohort, freeze independent oracle and exact weights, run paired B0/full/LOMO with patient-cluster bootstrap and multiple-testing control, then seek independent PI admission. Preserve the existing negative/error cases and source roots as predecessors.

## V2 successor: all teammate-hosted pilot outcomes preserved

V1 is an immutable source-index predecessor from main 5d8b784. V2 is regenerated against main 21158fe and indexes 521 committed JSON/JSONL paths, 24 historical local scientific events plus 48 completed hosted-model benchmark runs and 24 within-model matched case contrasts. Some tooling arms improve speed while losing correct fields; these losses are retained as negative results. Hosted benchmark models and checkpoint revisions are separate from local Synthea and Vita DAISY; public model revision and weight identity are UNKNOWN. See evidence/governance/OUTCOMES_AND_PROMOTIONS_20261102_V2.json for all recorded synthetic aggregate run metrics, exact-byte hashes and predecessor link.

**Frozen-source CI contract:** Verification reads original file bytes from the recorded predecessor Git commit with git show, not mutable main files after unrelated teammate merges. The generator is intentionally one-time for each immutable output path; on new main use a successor filename and receipt.
