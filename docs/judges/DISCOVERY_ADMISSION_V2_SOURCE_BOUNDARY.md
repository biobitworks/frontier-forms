# Discovery admission V2 — inherited methods versus implemented integration

**Machine-readable evidence:** evidence/governance/DISCOVERY_ADMISSION_V2_20261102.json

This is an append-only successor to PR #66's prose discovery inventory and PR #65's Claude-created gain heatmap (31 intervention rows, 52 measured cells). It freezes 89 source-linked records: FCO leaf contrasts, injected-error detector results, 60 YOLO epochs, three OCR trained/crop arms, Random Forest controls, local logistic model, failed custody case, and not-computed Qwen LoRA outcome.

## Admission is not promotion

- ADMITTED_TO_EVIDENCE_LEDGER: evidence readback and source path/SHA256 binding. Applies to success, failed, null, negative, neutral and not-computed records alike.
- DISCOVERY_POSITIVE: within-dataset measured improvement, subject to original exposure and replication limitations.
- SCIENTIFIC_PROMOTED: independent replication and FCAR/PI admission. Currently **zero**. FCAR status HOLD.
- NOVELTY: engineering composition and particular controlled implementation, **not independently demonstrated global invention or patent novelty**.

## What improved

**FCO L1 × L3:** on synthetic 18 patients × three forms, required-field full-form correctness improves 18/54 → 30/54, +22.22 percentage points. McNemar p=0.000488, Holm p=0.005859, patient-cluster bootstrap 95% CI +7.41 to +37.04 pp. Same neural weights. Existing test cases informed rule design; no independent prospective replication.

**Learned OCR correction:** synthetic 23 cases × clean/scan renders, 14/46 → 22/46 all-seven-field success, +17.39 pp. Exact paired p=0.0078125, Holm p=0.0234375, 23-case cluster CI +4.35 to +32.61 pp. This is a fitted OCR correction *table*, not new Qwen fine-tuning weights. Preregistration chronology and new-template replication remain unverified.

## Negatives, null and failure records are retained

YOLO crop A2/A3 arms were null in the trained OCR comparison. The trained logistic box detector tied the deterministic control at 540/540 fields (p=1, patient CI [0,0]). All three Random Forest fitted sizes had box F1 below the contour baseline. Drawing detection overlays before OCR reduced clean-figure accuracy from 58/70 to 0/70. YOLO full/no-scan 30-epoch chains preserve every loss and neutral transition. The initial 10-mismatch demo-manifest failure is preserved alongside its repaired 62/62 identity proof. No later PASS overwrites the failed predecessor.

## Standard techniques and integrated engineering

- **Standard:** MITRE Synthea/FHIR, Apple Vision, Qwen, YOLOv8n, LoRA, Random Forest, SHA256/Merkle, McNemar, bootstrap, Holm, routine supervised optimization.
- **Integrated:** patient × synthetic FHIR source × field/oracle binding; local cross-format/browser/PDF and OCR-field validation; per-leaf FCO/FCG LOMO; per-epoch checkpoint and model-weight provenance; append-only replayable evidence and admission; multiple controls and explicit regression/null records.
- **Vita DAISY:** methodological inspiration for freeze–challenge–replicate–admit; no cross-program data, trained weights, scores or roots. DAISY-specific performance gain NOT_COMPUTED.
- **Attribution:** Claude Code source training/demo/heatmap PRs versus ChatGPT independent check/ledger successors are distinguished. A shared GitHub login cannot assign unproven authorship.

## Chain of custody and deadline boundary

The 89-leaf canonical JSON event Merkle root is computed by scripts/build_discovery_admission_v2.py. It is not numerically comparable to a performance delta. The 82-event judge, three-arm OCR and synthetic asset roots are recorded only as predecessor identity references. Each input is bound to its exact file SHA256; independent verifier replays each input and compares complete output bytes.

The artifact explicitly disclaims proof of competition submission content. Its conservative "publication_after_event_cutoff" field is a **claim ceiling**, not an assertion that this particular file was created after 4:30 p.m. Pacific. Only a submitted frozen receipt with exact SHA establishes whether a change was eligible for judging.

To verify: run python3 scripts/build_discovery_admission_v2.py and python3 -m unittest tests.test_discovery_admission_v2 -v.

To admit new experiments, publish a new immutable successor after frozen inputs, model weight checks, paired patient answers and exact replication verification; do not alter this file.
