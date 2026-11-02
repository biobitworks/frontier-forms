# Local bbox vision validator — preregistered research contract (2026-11-02)

## Lanes and release boundary

- **V0**: deterministic source-bound B0/FCO + Lean4/Merkle (not a learned vision arm).
- **V1**: Apple Vision OCR boxes + PDFKit read-back (local inference, no training).
- **V2**: existing qwen2.5vl:3b form image model (pretrained local inference, not training).
- **V3**: this *new* PyTorch SmallUNet, optimized on synthetic blank-form DOM rectangles and tested against disjoint patient images. Trains and evaluates fully local.
- **V4**: V3 bounding boxes + V1 OCR value read-back + FCO source/value bindings. **NOT IMPLEMENTED**. Bounding-box correctness is not clinical correctness.
- **V5**: V4 with Lean/Merkle admission, then one-by-one LOMO and factorial combination. **NOT IMPLEMENTED**.

For V3, only blank forms are used to optimize weights; all synthetic patient-filled forms are held out. Six seed-hashed patients form validation; twelve form final test. That guards against pixel-level patient leakage but cannot demonstrate new-template generalization because all three form layouts are shared. The blank labels come from DOM geometry (not independent human annotation). Additional template-held-out cohorts and new fonts/layouts are required before admission. Never count synthetic oracle agreement as improvement on clinical records.

## Local training

```bash
python3 -m unittest tests.test_local_bbox_validator
python3 scripts/train_local_bbox_validator.py --data data/forms_vision_v1 --out runs/local_bbox_v1 --epochs 8 --steps-per-epoch 20
```

Dependencies: locally installed PyTorch, Pillow, NumPy, SciPy; no new model download, provider key, or endpoint. Training creates **local-only** `bbox_detector_state.pt` plus JSON lines with one bounding-box prediction per component and `TRAIN_RECEIPT.json` with exact weights, source and outputs SHA256. The program performs zero network operations. Results are **NOT_EXECUTED** until a real run and independent receipt verification.

## Publishing constraints

- **No Fireworks or other external inference/training API.** No cloud browser interaction with patient-like screenshots.
- GitHub is the only authorized data publication destination. Only verified **synthetic JSON** is public for Open Epic. MITRE Synthea generated synthetic JSON can be published in full after provenance/license, credential, and synthetic-only checks.
- Never publish image screenshots, PDF or HTML rendered patient forms, actual model weights, GPU device logs containing private paths, medical records, credentials, or unredacted personal data. The parent PRs currently contain PNG/PDF/HTML and require migration before merge.
- GitHub data artifacts should be JSON/JSONL only; code, tests and docs are not data. Do not conflate GitHub upload authorization with external inference authorization.
- `TRAIN_RECEIPT.json` contains host identifier by default; redact it and private paths before public release. Hashes establish identity, not correctness. Do not claim a Merkle root until independently computed from declared canonical bytes.

## Promotion gates

Report IoU50 recall/precision/F1, mean matched IoU, per-field matched/missed/extra counts, number of form layouts tested, synthetic patient overlap and latency. Compare V0, V1, V2, V3, V4, V5 on a **new** patient and template holdout with matched evaluation criteria. Preserve failures and abstentions, with exact model weights hash, image/annotation hash, decision source leaf and FCO linkage. No auto-merge without reviewed privacy and scientific gates.
