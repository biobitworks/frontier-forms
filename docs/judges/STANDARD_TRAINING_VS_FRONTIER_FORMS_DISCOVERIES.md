# Frontier Forms — standard methods versus our contribution

**Interpretation:** *Project-specific* is a defensible statement about the implementation and tested combination in this repository. It is **not** an assertion of invention, freedom-to-operate, patentability, or global scientific novelty. No prior-art search, outside independent replication, actual Epic EHR writeback, or independent PI promotion is claimed.

This is the actionable [source-backed admission ledger](../../evidence/admission/FF_DISCOVERY_AND_NOVELTY_V1.json). Each entry distinguishes an **observation**, a **synthetic benchmark asset**, a **conditional discovery**, a **null/negative control**, and **formal scientific admission**. The validation program is separate from Vita DAISY/Cloudmer and retains no model/data/weight transfers.

## Side-by-side: established tools versus our integrated work

| Layer | Standard training / known method | What we implemented or measured here | Claim ceiling / owner |
|---|---|---|---|
| Source data | MITRE Synthea FHIR generation, train/validation/test partition, fake patients | Versioned 100-patient Synthea cohort (63/19/18), separate SYNFORM2 111-case and SYNFORM2-ERR 23-case image/fault sets | **ADMITTED_SYNTHETIC_TEST_ASSET**, not real patient/Epic data; Claude PR #10 / red-team #21 |
| Baseline | Fixed rules and zero-shot instruction following | Same cohort and FHIR local-form harness, B0 18/54 complete test forms; untrained Qwen2.5-0.5B M0 **0/92 complete**, 381/920 correct fields | **OBSERVED**, Qwen did worse; Claude PR #62 |
| Learned model training | LoRA/SFT, Qwen inference, YOLOv8n object detection, OCR, learned correction tables | Local runs with frozen model identities and 30-epoch YOLO full/no-scan, plus A1 fitted OCR normalization | Training itself is **not novel**; no admitted LLM fine-tuning gain |
| Deterministic provenance and correction | Ordinary source validation, type checks, abstention, formal constraints | Per-field FCO/FCG evidence gate L1+L2+L3 and source-bound corrections, deterministic LOMO arms: **18/54 → 30/54** complete forms (22.22 pp) | **PROJECT-SPECIFIC INTEGRATION; DISCOVERY_ONLY**, Claude PR #10, independent audit PR #64; neural weights unchanged |
| Learned OCR correction | Standard fitted postprocessing, **not** Qwen neural weight updates | Train-split-fitted A1 post-correction **14/46 → 22/46** complete seven-field test renders; Holm p=0.0234375, independent whole-case bootstrap CI [+4.35,+32.61] pp | **OBSERVED DISCOVERY**, *operational label* PROMOTE_DISCOVERY, formal external scientific admission **HOLD**, Claude PR #51/#63, ChatGPT verifier PR #64 |
| Trained detector controls | YOLO, learned logistic/RandomForest bbox detection | A2 crops **9/46** and A3 crops+correction **15/46**, both NULL versus 14/46 baseline; trained logistic 540/540 boxes tied deterministic contour at 540/540; D1 13.06% recall, D2 95.56% recall / 65.65% precision | **NULL/NEGATIVE/EXPLORATORY**, not admitted, PR #14/#16/#64 |
| Evidence architecture | Standard Merkle hashing, Lean constraints, paired tests, ablation/LOMO, audit logs | Joined source identities, model digests, per-epoch GAIN/LOSS/NEUTRAL, fail-closed custody, patient-case paired tests, hold decisions, independent repair successor | **PROJECT-SPECIFIC EVIDENCE ARCHITECTURE**, not a new hashing/formal-math algorithm, Claude PR #21 + ChatGPT #18/#64 |
| Model and tool speed | Ordinary matched tool/no-tool benchmarking | Teammate hosted pilot: 48 runs, 24 matched pairs, 23 faster tool arms **and 3 quality regressions** | **SEPARATE REPORTED HOSTED PILOT**, no independent scientific promotion; not imported into local training |
| EHR deployment | SMART/FHIR and Epic APIs | Synthetic HTML/CSS forms and local read-only FHIR server, PDF and OCR sample readbacks | **IMPLEMENTED/PARTIAL**, real Epic OAuth, schema parity and production writeback **NOT_TESTED** |

### What was distinctive *within the project*

The **integration** is source-bound form correction and abstention, local model/vision comparisons, and every outcome (including failed and tied models) connected to per-source cryptographic identities and formal admission decisions. It is specifically the *joint testable architecture* we can describe as our contribution—not a claim that Synthea, Merkle trees, Lean, LoRA, Qwen, YOLO, OCR postprocessing, or ablation testing were invented here.

**Do not conflate three types of promotion:** Git PR **merged** (engineering state); an A1 **PROMOTE_DISCOVERY** label (positive controlled synthetic result, replication pending); formal **ADMIT_SCIENTIFIC** (still **HOLD_NO_INDEPENDENT_PI_ADMISSION**). A discovery's p-value and confidence interval do not resolve source selection, prospective replication, unseen template generalization or clinical risk.

## Admitted now / explicitly excluded

- **ADMIT to the local synthetic evidence registry:** the exact Synthea and SYNFORM2 source manifests, their independent/test split boundaries and recorded benchmarks. Data admission means *usable for this synthetic evaluation*, not IRB/human-study approval.
- **RETAIN as observed discovery evidence:** deterministic FCO/FCG improvement and train-fitted A1 OCR correction, with model attribution and test exposure caveats. A1 was a learned correction table, not fine-tuned Qwen.
- **RETAIN negative and null:** M0 zero-shot Qwen, D1, logistic/Random Forest no gains, A2/A3, OCR overlay failure, hosted-model quality regressions. They remain real evidence despite not being promotable.
- **DEFER** any independent scientific/global novelty/clinical superiority claim, M1 fine-tuning improvement, real Epic writeback, and new-template replication. No silent FAIL→PASS relabeling.

## Independent promotion criteria

To change scientific HOLD, precommit an **independent** patient cohort and **unseen** form family/template, version oracle and all models/weights, test B0, FCO, zero-shot model, trained model and A1 in one fixed protocol, with patient-cluster confidence intervals and appropriate multiple-testing adjustment. Verify source-to-DOM-to-PDF OCR position and null rates. Obtain explicit scientific/PI review before changing the gate. Do not infer causality from hashes or Merkle inclusion.

Sources: [admission ledger](../../evidence/admission/FF_DISCOVERY_AND_NOVELTY_V1.json), [formal FCAR status](../../evidence/admission/FF_FCAR_GATE_ASSESSMENT_V1.json), [independent OCR evidence](OCR_CORRECTION_SUCCESSOR_V2.json), [M0 negative baseline](../../evidence/forms_model/M0-zeroshot/summary.json), [data provenance](../../data/forms_cohort_v1/GENERATION.json), [synthetic test outcomes](../../evidence/redteam/trained_gain/trained_gain_summary.json), and [separate teammate hosted evidence](../../evidence/governance/OUTCOMES_AND_PROMOTIONS_20261102_V2.json).
