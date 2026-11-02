# All 218 filled forms: PDF read-back (JSON)

This is a re-run of the frozen Apple arm (`scripts/run_forms_apple_arm.py --samples 1000`, tool `tools/apple_forms/AppleForms.swift`, Vision pinned to the CPU). It ran on MacBookPro on 2026-11-02 and kept every filled PDF.

- `*.readback.json`: one file per patient-form (218 in total). Each holds the PDF field values, plus the Apple Vision OCR text, its confidence and its box for every widget.
- `FILLED_PDF_SHA256SUMS.txt`: the SHA-256 of each of the 218 filled PDFs. The PDFs stay on the MacBookPro (`/tmp/ffa/apple_all/samples/`), because main's JSON-only gate blocks new PDFs. Six sample PDFs are already committed under `../run_v1/samples/`.
- `summary_A1.json`, `summary_A2.json`: identical to run v1. The A1 and A2 predictions are byte-identical to `../run_v1/predictions_A*.jsonl` (A1 `bda50991…`, A2 `ea0ea42b…`). That makes this the third byte-identical replay.

All patients are synthetic (MITRE Synthea).
