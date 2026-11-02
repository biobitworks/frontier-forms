# Frontier Forms B0: frozen local form-filling baseline

**State:** FROZEN_PENDING_PI_REVIEW (2026-11-02). Lane: frontier-forms only. No data, results or checkpoints from other programs are used here.

## What is frozen

| Item | Where | Pin |
|---|---|---|
| Synthetic cohort, 100 living patients | `data/forms_cohort_v1/` | subset root `ee202dd8…08df`, raw root `03a6909f…c033` |
| Generator | Synthea v3.4.0, seed 20261102, reference date 2026-11-01 | jar SHA-256 `38678aab…2432` |
| Form templates (3 families) | `src/frontier_forms/forms/templates/` | SHA-256 per file in `B0_FREEZE_V1.json` |
| B0 arm | `src/frontier_forms/forms/b0.py` | SHA-256 in `B0_FREEZE_V1.json` |
| Gold oracle | `src/frontier_forms/forms/oracle.py` | SHA-256 in `B0_FREEZE_V1.json` |
| Teammate passport builder | `scripts/import_fhir.py` (PR #4), loaded unchanged | SHA-256 in `B0_FREEZE_V1.json` |
| B0 run v1 | `run_v1/predictions.jsonl`, `summary.json`, `receipt.json` | replay is byte-identical |

`tests/test_forms_b0.py` fails if any pinned file changes, so a new arm or oracle must be a new file plus a new freeze, never an edit.

## How it runs

```
PYTHONPATH=src python3 scripts/serve_forms.py --port 8765        # loopback form server + read-only FHIR R4
PYTHONPATH=src python3 scripts/run_forms_b0.py --cohort data/forms_cohort_v1/bundles --out /tmp/b0
python3 -m unittest tests.test_forms_b0 -v
```

The server binds to 127.0.0.1 only. `/fhir/R4` serves `metadata`, `Patient/<id>` and `?patient=` searches for the resources Epic's R4 API also exposes. All writes return 405. Forms never expose the canonical answer key. B0 fetches the HTML form and the teammate passport over HTTP, posts a structured fill plan (spec 10.2), and the harness checks the server echo.

## B0 run v1 results (synthetic data, code oracle)

| Slice | Forms | Field accuracy | Full-form success (required) | Unsupported-answer rate | Missing-data recall |
|---|---|---|---|---|---|
| All | 218 | 0.856 | 0.463 | 0.087 | 0.087 |
| train | 126 | 0.873 | 0.508 | 0.083 | 0.000 |
| validation | 38 | 0.871 | 0.500 | 0.084 | 0.000 |
| test | 54 | 0.807 | 0.333 | 0.100 | 0.257 |
| registration | 100 | 1.000 | 1.000 | 0.000 | n/a |
| medication/allergy | 100 | 0.711 | 0.010 | 0.189 | 0.000 |
| urgent care (held-out layout, test only) | 18 | 0.706 | 0.000 | 0.111 | 0.500 |

Where B0 fails: it writes "None" for allergies when the record has no AllergyIntolerance (the oracle requires asking the patient), it lists social findings as medical conditions, and it puts kilograms into a pounds field. Evidence correctness is NOT_COMPUTED because B0 emits no evidence ids.

## Planned arms (not yet run)

Incremental: B0 → B1 +source binding (evidence fact ids) → B2 +FCO/FCG custody → B3 +validation (units, abstention, schema) → B4 full candidate.
LOMO: B4 minus one mechanism per arm, same cases, same server, same oracle.
Comparison arm: Apple Vision OCR + macOS Preview form fill on the rendered form (runs on the Mac; separate receipt).
Paired statistics use `src/frontier_forms/statistics.py` (exact McNemar, patient-stratified bootstrap) with case digests from `predictions.jsonl`.

## Open review items

See `open_review_items` in `B0_FREEZE_V1.json`. The two gold-rule choices (disorders only, and no allergy record meaning ask) need PI sign-off before any comparison is admitted. The teammate Supabase count is still unverified and needs a rotated read-only credential.

**Claim ceiling:** these numbers describe a deterministic rule filler on synthetic data against a code oracle. They are not clinical accuracy and not model performance.
