# Frontier Forms local acceptance gate V1 — 2026-11-02

## Purpose

One observable workflow: **MITRE Synthea synthetic FHIR R4 bundle -> local
read-only FHIR/passport facade -> B0 or local Qwen field mapper -> versioned
HTML/CSS preview -> browser-printed PDF -> Apple Vision OCR bounding-box
readback -> inspectable JSON receipt**. The components are evaluated separately
before promotion. No real patient data, cloud-hosted inference, or Epic writes.

**Open Epic distinction:** open.epic publishes FHIR R4/SMART and Questionnaire
technical specifications, not the three synthetic HTML templates in this repo.
Actual Epic questionnaire/field UI fidelity and OAuth are NOT_TESTED.
See https://open.epic.com/TechnicalSpecifications and
https://open.epic.com/Interface/FHIR for specs only.

## Reproduce on an authorized local Mac

1. Use the frozen `data/forms_cohort_v1` bundles, exactly 100 unique patients
   with 63/19/18 train/validation/test split, and `src/frontier_forms/forms/templates`.
2. Start an optional manual local test server:
   `PYTHONPATH=src python3 scripts/serve_forms.py --port 8765`.
   Existing frozen form: `/forms/<template_key>`. New *successor*
   CSS-styled preview: `/preview/forms/<template_key>`.
   Neither endpoint exposes `canonical_key` or gold answers.
3. Full deterministic mapping against the loopback server (100 patients;
   218 eligible forms): `python3 scripts/run_acceptance_loopback.py --arm b0 --limit 100 --render-limit 0 --out runs/acceptance_b0_all100_fields`.
4. HTML/CSS/PDF browser spot check:
   `python3 scripts/run_acceptance_loopback.py --arm b0 --limit 1 --render-limit 1 --out runs/acceptance_smoke_v2`.
5. Actual local Qwen field answers and one PDF:
   `python3 scripts/run_acceptance_loopback.py --arm qwen --model qwen2.5:0.5b --limit 1 --render-limit 1 --out runs/acceptance_qwen_one`.
6. Optional native PDF OCR:
   `swiftc -O experiments/form_error_factorial/apple_vision_boxes.swift -o /tmp/ff_accept_apple_vision`;
   pass `--vision-tool /tmp/ff_accept_apple_vision` with `--render-limit N`.
7. Independent gate:
   `python3 scripts/check_synthetic_json_policy.py` must return PASS
   **before a release merge**. Currently FAIL due inherited public artifacts.

Dependencies for actual rendering: local Python Playwright, Chrome/Chromium,
PyMuPDF. The code uses the local installed Chrome on macOS. Qwen runs
through loopback Ollama only; no remote model endpoint exists in the runner.

## Latest OBSERVED evidence

Structured source-bound aggregate receipt:
`evidence/acceptance/ACCEPTANCE_PROGRESS_20261102.json`.

- B0: 100 synthetic patients, 218 form cases, 1,867/2,180 fields correct;
  zero server-echo failures, **but no PDF rendered in the full-cohort B0 pass**.
- Qwen2.5:0.5b: 1 patient / 2 forms / 12/20 fields correct. Model digest and
  output byte hashes are recorded; not generalizable.
- CSS successor: one B0 PDF rendered and text read-back passed for the filled
  values checked. Separate older PDF samples produced three local
  Apple Vision JSON receipts with real line boxes; this is not an end-to-end
  100-patient vision validation.
- Main-branch JSON-only publication gate: FAIL, 123 tracked violations,
  including 104 prohibited pixel/PDF items, 15 HTML fixtures, 4 JSONL files.
- Clinical truth beyond the synthetic oracle, unseen Epic UI forms, new-layout
  vision generalization, D2 bbox model integration, FCO source admission,
  Lean/Merkle end-to-end causality and model training gain remain NOT_TESTED.

## Non-negotiable acceptance / promotion

Compare B0, unchanged Qwen, LoRA Qwen (only if saved adapter independently
verified), Apple Vision OCR, trained bbox D2, and their valid combinations on
the **same frozen patient-disjoint, template-held-out synthetic inputs**.
Declare model digest/weight hash, local runtime, input JSON SHA256, output
JSON SHA256, original form field, answer, decision, explicit source-leaf
binding, DOM field box, PDF read-back box, and outcome for each field.

A submitted JSON echo is not a correctly rendered PDF. PDF selectable text
is not OCR. OCR text present anywhere on the page is not proof that it was
placed in the correct field box. A file SHA256 establishes identity only:
a Merkle root must be computed from declared canonical leaves and independently
verified; do not invent or infer it from content hashes.

All screenshots, PDFs, raw model prompts, logs and model weights stay local.
Publish only verified synthetic JSON datasets and JSON receipts to GitHub.
Do not use Fireworks or any external provider for inference or training.
Do not merge until the publication gate and reviewed full-pipeline gates PASS.
