# Frontier Forms: what we did and what comes next

The project turns a medical intake form into a draft FHIR record and checks each field against its source. It uses only synthetic MITRE Synthea patients, so there is no PHI. Models run locally (Apple Vision, Ollama Qwen, local detectors), with no hosted inference and no live EHR writes. The statuses are PROPOSED, IMPLEMENTED, EXECUTED, OBSERVED, SUPPORTED, NEGATIVE, NULL, NOT_TESTED and BLOCKED. **No workstream has reached SUPPORTED**, because every positive result still needs replication.

This covers 34 PRs: 27 merged, 4 open and 3 closed unmerged. The full inventory is `docs/judges/pr_inventory.json`. Labelled figures with captions, including the accomplishment heat map, are in [FIGURES.md](FIGURES.md).

## Workstreams

| Workstream | Status | PRs |
|---|---|---|
| Custody / Merkle replay | OBSERVED | 3, 8, 11, 20, 21, 47 |
| LongevityBench model lanes | NEGATIVE | 1, 3, 11, 13, 20 |
| FCO/FCG context in prompt | NULL | 11, 13, 20 |
| Supabase schema/importer | EXECUTED locally; live NOT_TESTED | 4, 5, 17 |
| Synthea cohort freeze | OBSERVED | 10, 17 |
| Form rendering + loopback server | OBSERVED | 10, 12, 19, 22 |
| B0 + L1–L3 module arms | OBSERVED (discovery) | 10, 17, 18, 19 |
| Apple Vision OCR | OBSERVED | 10, 12, 20, 22, 23 |
| qwen2.5vl:3b extraction | OBSERVED | 12, 19, 23, 29 |
| Tesseract OCR | OBSERVED | 10, 11, 19 |
| Qwen text mappers | NEGATIVE | 12, 22, 23 |
| Qwen LoRA SFT before/after | EXECUTED; gain NOT_TESTED | 10, 17, 18 |
| Learned bbox validators | NEGATIVE | 14, 15, 16 |
| YOLOv8n detector + epoch ledger | OBSERVED; V2 NOT_TESTED | 19, 20, 21 |
| Commitment gate factorial | OBSERVED; replication NOT_TESTED | 20, 21 |
| Injected-error detectors | OBSERVED | 10, 12, 18 |
| Training dashboards | OBSERVED | 7, 18 |
| 100-patient acceptance runner | OBSERVED; PR open | 22 |
| Lean 4 proofs | EXECUTED (compiled) | 3, 11, 12, 20 |
| Paired statistics | EXECUTED | 3, 18, 19, 28 |
| Prompt injection | OBSERVED; filter NOT_TESTED | 10, 11, 29 |
| Security / JSON-only / CI | EXECUTED | 8, 16, 17, 27, 30, 43 |
| Fireworks | BLOCKED | 1, 12, 20, 26 |
| NVIDIA training | NOT_TESTED | 1, 3, 20 |
| Epic | NOT_TESTED | 1, 3, 22 |
| Snyk | BLOCKED | 1, 8, 20 |
| Governance (GSD/gsigmad, TASKS) | EXECUTED | 9, 42, 44, 46, 47 |
| Demo: form server, overlays, screenshots, PDFs | OBSERVED (this branch) | 7, 12, 18, this PR |

## Headline results

- **Frozen cohort:** 100 Synthea v3.4.0 patients split 63/19/18. Two generations were byte-identical (#10).
- **Baseline vs harness:** on the 54 held-out test forms, B0 reached 0.333 (18/54) full-form success. B0+L1+L2+L3 reached 0.556 (30/54), with p=0.00049 and a patient-cluster CI of [0.074, 0.370] (#17, #19). This is discovery grade only.
- **Commitment gate:** planted-error detection rose from 0.13 to 1.00 with 0 false admissions, Holm p < 0.0001 and CI [+0.61, +0.66] (#20).
- **Injected-error detectors:** across 654 forms with 702 errors, M3 source binding reached 0.989 recall. Without source data, M1+M2 reached 0.426 (#10).
- **qwen2.5vl:3b:**
  - 318/322 SYNFORM2 test fields (#23 ledger).
  - Box recall 0.821 and value read 0.736 on 57 images (#19).
  - Followed the injected note in 0 of 18 injected images (#29).
- **YOLOv8n:** test mAP50 0.912, with 315/322 fields detected (#20).
- **100-patient B0 acceptance:** 1,867/2,180 fields (85.6422%) and 0 server echo errors (#22).
- **Bounding boxes and OCR:** drawing boxes onto a form image dropped Apple OCR from 58/70 to 0/70 correct fields on the same 10 forms, so OCR must run on the clean render (`docs/demo/ocr_boxes_vs_clean.json`).
- **Custody:** all 728 inclusion proofs and the review roots were independently recomputed (#11, #20, #47).

## Negative and null results we kept

- **LongevityBench:** Liquid 25/38 vs Insilico 27/38, McNemar p=0.6875. NEGATIVE (#1, #3).
- **FCO/FCG context:** NULL on held-out (25/39 vs 25/39). Insilico with full FCG went 22→19/39, NEGATIVE (#11, #13).
- **qwen3:1.7b and qwen2.5vl:3b on LongevityBench:** 3/39 and 6/39, NEGATIVE (#20).
- **Qwen text mappers:** 209/322 and 109/322, against 283/322 for the deterministic parser (#23).
- **Logistic box validator:** tied the control at 540/540, with CI [0, 0] (#14).
- **Random Forest box validator:** −37.0 pp full-page vs the control (#15).
- **D1:** F1 0.11285, NEGATIVE.
- **D2:** F1 0.77828, exploratory only because it was tested on layouts it had already seen (#16).
- **LoRA SFT:** only an epoch-0 loss (1.0049872103490327) and no adapter, so the gain is NOT_TESTED (#18).
- **Publication policy:** 123 legacy non-JSON files are exempt but not compliant (#22, #30).
- **External services:** Snyk and Fireworks BLOCKED. NVIDIA, live Supabase and Epic NOT_TESTED.

## What remains (ordered)

1. **Fresh replication cohort (T01 #31).** Preregister and score it once.
2. **Trained-model result (T08 #38).** Restart SFT M1, then score M0, M1 and M2 on the 54 test forms.
3. **Custody fixes (#47).** Fix the duplicate-last-leaf, unbound-parent and dangling-edge findings, then regenerate `evidence/stats` through the gate.
4. **Oracle-rule sign-off (T02 #32).**
5. **Noisy and scanned renders (T03 #33).** Score the OCR and VLM arms clean vs degraded.
6. **V2 detector results (T09 #40).**
7. **Prompt-injection filter (T04 #34).**
8. **Acceptance runner (#22).** Rebase it and produce one unified field-level receipt.
9. **Publication policy (issue #24).** Migrate the legacy fixtures to JSON and confirm CI is green.
10. **Cost and latency per correct form (T05 #35).**
11. **Owner decisions.** Decide T07, T10 and #25, merge #29 and #47, and review #44.
