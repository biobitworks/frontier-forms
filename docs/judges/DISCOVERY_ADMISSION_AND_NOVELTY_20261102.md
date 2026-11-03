# Frontier Forms — discovery admission and novelty versus standard training

**Status: ADMITTED_TO_DISCOVERY_LEDGER_ONLY; SCIENTIFIC_PROMOTION=HOLD.** This is a retrospective evidence index, not an experimental replay, new benchmark or amendment to the frozen competition submission. Parent main at branch creation: c20996956fb18c9761b5d57792f667b32d243547. Preserve all predecessor failures and negative results.

## What was novel/integrated versus standard practice
| Component | Standard technique / inherited dependency | Frontier Forms implementation / integration | Claim ceiling |
|---|---|---|---|
| Synthetic patient cohort | MITRE Synthea synthetic data; FHIR; ordinary schema and HTTP tests | Patient×form case binding, passport/source leaf, form-key contract, local echo, oracle decisions and provenance lineage | Engineering integration, not invented synthetic data |
| OCR and vision | Apple Vision, local Qwen, YOLOv8n; conventional OCR/field-box detection | Compare clean and annotated renders, isolate box-overlay OCR interference; trace field-level errors | Experiment-specific observation, not a new OCR architecture |
| FCO/FCG validation | Deterministic rules, abstention, unit conversion, clinical categorization | Context-sensitive L1 evidence-abstention plus L3 clinical filter with per-leaf LOMO, exact paired receipts | Discovery-positive on synthetic cases; not unbiased clinical gain |
| Model training | Qwen LoRA fine-tuning, RandomForest training, standard supervised optimization | Frozen checkpoints and Merkle-linked per-epoch/source/prediction receipts, LOMO/model identity separation | Provenance engineering; no Qwen LoRA gain established |
| Evaluation | McNemar, bootstrap, Holm correction, ablation | Match patient×form keys and hashes, preserve failed/tied arms, source-root/weights/prediction lineage, fail-closed admission | Evidence-control integration, not novel statistical mathematics |
| Admission methodology | Vita DAISY freeze–challenge–replicate–admit pattern | Independent Frontier Forms FCAR gate, program separation and admission HOLD | Method transfer only; DAISY weights/metrics/roots not imported |

## Discovery records admitted for reporting, NOT promoted
1. **FCO LOMO**: B0+L3 18/54 vs B0+L1+L3 30/54 required-field full-form successes across 18 synthetic patients; delta +12/54=+22.22 percentage points. Exact McNemar p=0.00048828125, Holm-adjusted p=0.005859375, patient-cluster 95% CI [0.0741,0.3704]. No neural weight change. Original failures informed rule design, so NOT_PROMOTED; prospective independent replication NOT_TESTED. Source: dashboard/training_progress_latest.json and PR #48.
2. **OCR correction**: PR #58 reports 14/46 to 22/46 fully correct seven-field synthetic images; +8/46=+17.39 percentage points; McNemar p=0.0078125; Holm p=0.0234375. Source-reported image-stratified CI, not patient-cluster CI. DISCOVERY_ONLY; independent prospective replicate NOT_TESTED. This is a trained OCR-correction lane, not evidence of Qwen LoRA or DAISY transfer.
3. **B0 replay**: previous monitoring reported 1,867/2,180 correct fields (85.64%), 100 synthetic patients, 218 forms, zero server echo failures and exact matching frozen hashes. Treat as previously reported execution, not newly reexecuted by this PR.
4. **Rotating sample**: previous monitoring reported 73/90 correct fields, 3/9 full-form successes; 8 unsupported allergy assertions, 6 disorder/condition misclassifications, 3 lb conversion errors. The monitoring receipt is not newly reverified by this PR; do not promote to golden path.
5. **Negative / regressions**: standalone L1/L2/L3 edges and other FCO LOMO ties; GLM hosted-model pilot quality 118/121 to 115/121 correct (negative despite latency improvement); clean Apple OCR 58/70 versus boxed-overlay OCR 0/70 (PR #51). Preserve these as negative/tradeoff observations with original conditions, not as blanket generalizations.
6. **Integrity failure**: prior monitor reported three judge-demo annotation file SHA mismatches; PR #55 reportedly identified 10/62 manifest entries for repair. Actual current PR merge and full revalidation must be checked separately; do not mark PASS based on this document.
7. **LoRA checkpoint**: prior monitor reported epoch 0 only, no new adapter; NO_NEW_CHECKPOINT. New snapshot and training gain NOT_COMPUTED.
8. **PDF**: previous preview was one-page image-only, not proof of filled PDF autofill. Exact SHA must be traced to original bytes and source receipt, not reasserted as newly verified.
9. **Supabase**: reported rows are not observed live rows; remain NOT_OBSERVED.

## Attribution and novelty safeguards
- Third-party frameworks, pretrained models, Synthea and standard statistical methods are credited as prior art/dependencies. The novelty claim is the *specific integrated implementation, lineage and controlled synthetic experiments*, not invention of their components.
- Claude-authored PRs (#50/#51/#49 and others) and ChatGPT-authored PRs (#46/#48/#53/#56) must be attributed by their actual PR/commit metadata; do not assign all team work to one assistant.
- Pre-event work and November 2 work must be separated by commit timestamp and the actual frozen submitted SHA. No retrospective post-cutoff change is part of the judged build.
- Model gains require named model/weights and paired held-out answers. A changed Merkle root, reduced loss, improved detector F1, or cross-sectional training-size sensitivity does not establish full-form gain.
- No production EHR writes, PHI, weights or foreign DAISY/Cloudmer data are included in this ledger.

## Promotion gate
Discovery admission is an inventory action. Scientific admission requires independently frozen unseen patient/template holdout, predeclared oracle and arms, identical-case evaluation, verified model/source/checkpoint hashes, exact paired McNemar, 10,000 patient-cluster bootstrap, family-wise correction, independent replication and PI approval. Current status: HOLD / NOT_TESTED, not PASS.

## Review links
- PR #48 https://github.com/biobitworks/frontier-forms/pull/48
- PR #49 https://github.com/biobitworks/frontier-forms/pull/49
- PR #50 https://github.com/biobitworks/frontier-forms/pull/50
- PR #51 https://github.com/biobitworks/frontier-forms/pull/51
- PR #55 https://github.com/biobitworks/frontier-forms/pull/55
- PR #58 https://github.com/biobitworks/frontier-forms/pull/58
