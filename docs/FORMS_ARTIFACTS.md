# Frontier Forms: where everything lives

Every patient here is synthetic: MITRE Synthea v3.4.0, a frozen 100-patient cohort. There is no real PHI. Byron approved publishing these synthetic JSON, PNG, PDF and HTML files. Model weights and credentials are never committed.

## Form server and forms
| What | Path |
|---|---|
| Loopback form server (HTML forms, read-only FHIR R4 facade; writes return 405) | `src/frontier_forms/forms/server.py`; run it with `PYTHONPATH=src python3 scripts/serve_forms.py --port 8765` |
| Form templates (3 families; urgent care is the held-out layout) | `src/frontier_forms/forms/templates/*.json`, rendered by `templates.py` |
| Frozen B0 filler, oracle and scorer | `src/frontier_forms/forms/b0.py`, `oracle.py`, `harness.py` |
| Frozen cohort (FHIR JSON subset bundles, manifest, splits) | `data/forms_cohort_v1/` |
| Prebuilt forms with injected errors (654 forms, 702 errors, preregistered) | `data/forms_injected_v1/` |
| Fault-factorial HTML fixtures (PR #12) | `experiments/form_error_factorial/prebuilt_forms/` |

## PDFs
| What | Path |
|---|---|
| Blank AcroForm PDFs (made by PDFKit) | `evidence/forms_apple/forms/*.pdf` |
| Filled PDFs plus Apple Vision OCR read-back, sample of 6 | `evidence/forms_apple/run_v1/samples/` |
| All 218 filled PDFs, one per patient-form, with read-back JSON | `evidence/forms_apple/run_v1_all_pdfs/` (added in a follow-up PR when the MacBookPro re-run finishes) |
| Single fixture PDF with Apple Vision boxes (PR #12) | `experiments/form_error_factorial/sample_vision/` |

## Screenshots
| What | Path |
|---|---|
| 57 rendered forms: 3 blank, plus 54 B0-filled test-split forms | `data/forms_vision_v1/*.png` |
| 36 paired clean and injected images for prompt-injection tests | `data/forms_vision_inject_v1/*.png` |
| Renderer (Playwright; layout randomization and forged-text options) | `tools/render/render_forms.js` |

## Bounding-box versions
| What | Path |
|---|---|
| Gold boxes (DOM input rectangles and the written values) | `data/forms_vision_v1/GOLD_BOXES.json`, `data/forms_vision_inject_v1/GOLD_BOXES.json` |
| **Overlay images**: gold in green, qwen2.5vl box and value in red, Tesseract lines in blue, with an HTML gallery | `evidence/forms_vision/overlays_v1/index.html` (57), `evidence/forms_vision/overlays_inject_v1/index.html` (36) |
| qwen2.5vl:3b predicted boxes and raw answers | `evidence/forms_vision/V1-qwen2.5vl-3b/answers.jsonl`, `V1i-qwen2.5vl-3b-injection/` |
| Tesseract line boxes (red-team runner) and scoring | `evidence/forms_vision/T1-tesseract-redteam/` |
| Trained box validators from other lanes (#14, #15, #16) | `evidence/forms_box_validator/`, `evidence/local_box_validator/`, `evidence/forms_bbox/` |
| V2 trained YOLOv8n detector: per-field pixel and normalized boxes, validator verdicts | `evidence/forms_detector/V2-yolov8n/` (follow-up PR once training finishes) |
| Browser overlay of the fixture with Apple Vision boxes (PR #12) | `experiments/form_error_factorial/vision_overlay.html` |

Regenerate the overlays with `python3 scripts/render_bbox_overlays.py` (its usage is in the header).
