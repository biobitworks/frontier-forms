# Frontier Forms — on-device synthetic bounding-box validator

Independent additive experiment stacked on Claude PR #10 and synthetic LOMO PR #12. No Fireworks, NVIDIA cloud, Epic write APIs, real PHI, remote inference or Cloudmer/knots data.

## Data provenance and task

- MITRE Synthea: frozen 100 synthetic-patient FHIR R4 cohort; 63 train / 19 validation / 18 test.
- open.epic: technical FHIR mapping specification; it is not a second source of the MITRE patient ground truth.
- Browser-rendered synthetic form images: three template families, with DOM ground-truth field bounding boxes in the active teammate source checkout.
- Train two allowed form templates only, from actual Synthea synthetic demographics/contact facts. Evaluate 54 filled browser forms from the 18 excluded test patients, including the held-out urgent-care template.
- Detector task: locate field boxes. This is NOT field-value correctness, OCR transcription accuracy or clinical improvement.

## Models and ablations

Control CV_B0_contours is a deterministic OpenCV contour classifier. This is NOT the teammate B0 form-filling agent. The learned local challenger uses sklearn RandomForestClassifier with 24 trees, max_depth=10 and fixed seed 20261102, trained on raster contour candidate features. Three feature blocks geometry (x,y), shape (dimensions/aspect), pixels (darkness/borders) produce 2^3-1 = 7 trained arms plus deterministic control. Threshold chosen on validation patient images, never on test patient images. No YOLO or LLM weights are tuned here.

Samples: tiny 10 train patients, small 30, medium 63, always 19 validation / 18 test patients.

## Actual results (V2 source-trained)

| Training patients | Deterministic F1 | Full-feature learned F1 | Candidate AUROC |
|---:|---:|---:|---:|
| 10 | 1.0000 | 0.9792 | 1.000 |
| 30 | 1.0000 | 0.9792 | 1.000 |
| 63 | 1.0000 | 0.9734 | 1.000 |

NEGATIVE: no model improvement over deterministic contour detection on existing template geometry. AUROC only measures ranking of candidate boxes vs non-boxes, not clinical confidence. Some shape-only LOMO variants tie baseline F1=1.000. No claim of prospective generalization: test layouts already seen during prior development.

## Custody, predecessor and publication

V1 prototype trained on artificial ID-tied text; its root excluded full predicted box coordinates and is preserved as PARTIAL PROVENANCE. V2 successor trained on genuine synthetic Synthea FHIR name, DOB, contact and address strings and binds complete predicted box arrays to each per-arm Merkle leaf. Independent verifier checks exact source SHA-256, training code hash, weight-file SHA-256, output predictions and paired results before publishing.

Only code and public-safe synthetic-derived JSON projections under evidence/local_box_validator are pushed to GitHub. PNG/PDF image assets, local full case-level receipt and binary pickle checkpoints remain on the authorized Mac. Registry connects predecessor V1 and V2 by actual JSON file SHA-256.

## Reproduce in an authorized local checkout

Python 3.12 with opencv-python, scikit-learn, Pillow, numpy is required. Run train_eval.py using the local teammate form-render directory, frozen Synthea cohort manifest and local private output path; then run verify_receipts.py against the same artifacts. Public JSON cannot independently reconstruct private screenshots or weights without those local bytes.

## Unresolved

- Need prospective previously unseen form families, randomized rendering, independent blind labels before supported generalization claim.
- Need OCR-text and field-value evaluation with calibrated error-risk scores; box classifier AUROC is not clinical answer AUROC.
- True end-to-end YOLO box proposal or VLM fine-tuning is NOT_TESTED.
- No completed model training gain established for Insilico or Qwen in this box validator.