# Local synthetic bounding-box vision validator — V1

Executed on magicSTUDIObox, CPU-only, no external inference or uploads. The data is MITRE Synthea synthetic and the HTML-rendered form images originate from Claude's draft PR #10. This stacked lane uses the same exact source images, patient IDs, field labels and DOM rectangle annotations, without modifying them.

The learned detector is a **trained logistic-regression pixel/geometry classifier** (OpenCV contour proposals to pixel features to fitted coefficients). It is not YOLO, is not an OCR model, is not a language model, and does not validate clinical content. All learned parameters are published as JSON in run_v3/weights.json with their independently recomputable SHA-256 identity.

## Run design

- **Train:** Three blank forms, zero patient images. Labels: DOM field boxes from the existing GOLD_BOXES.json. Learns to classify candidate image rectangles.
- **Evaluate:** All 54 existing filled forms from 18 synthetic patients, 540 boxes. No patient image enters optimization. All three *layouts* occur in training; this is not new-layout generalization.
- **Control:** Same OpenCV contour proposals, with a predetermined geometric width/aspect-ratio filter and no learned weights. Any gain must be attributed to the classifier, not the candidate generator.
- **Outcome:** IoU ≥ 0.5 match to DOM field boxes; exact two-sided McNemar on paired per-box detection; 10,000 patient-cluster bootstrap replicates; false-positive proposals.
- **No backend write:** Images are read locally, results are synthetic JSON. This is a visual proposal validator for the web/PDF intake pipeline, not independent clinical or OCR validation.

## Reproduction

    python3 -m pip install -r requirements-local-vision.txt
    python3 scripts/train_local_box_validator.py --out /tmp/frontier-box-independent-run
    python3 -m unittest tests.test_local_box_validator -v

Comparison results and all per-box candidate scores are under run_v3. The source image SHA-256 list and held-out patient IDs hashed with SHA-256 are under input_manifest.json. Exact model weights and parameters are under weights.json. summary.json defines the model identity, Merkle root algorithm, paired statistics, validation ceiling and negative findings.

**Observed negative:** Both trained and heuristic detectors located 540/540 source-rendered fields with zero false positives. Accuracy delta 0, McNemar p=1, 95% patient bootstrap CI [0,0]. Do not claim improved model accuracy from a new root or new checkpoint. Train and evaluate on new form layout families before evaluating the learned model's usefulness.

## Next version proposal

Add a separately generated synthetic rendered-paper/PDF layout family absent from training, including scans, skew, compression, dropouts and character confusables. Compare local Qwen2.5VL 3B, Apple Vision/PDFKit and this CPU classifier using identical rendered images; keep OCR text quality separate from box localization. Connect evidence and model outputs at the case-field level, then run an image-level/field-level LOMO with matched patient IDs. No Fireworks.

## Append-only pre-publication correction
The predecessor exploratory run_v1 root was computed, but the staged Gitleaks scan found 18 generic-api-key false positives caused by a synthetic hashed identifier property name. The original bytes and exact root remain in a local private archive; V1_FALSE_POSITIVE_RECEIPT.json records its hash, original 18-count failure and successor. run_v2 changes **only the identifier property name** and replays the training. No scientific gain or checkpoint change is attributed to that formatting repair.

## Second staged-scan correction
Run_v2 still had 18 false positives. Inspecting the redacted match-field information identified the actual trigger as the synthetic long form template_key value, not the patient digest. V1_CLASSIFICATION_CORRECTION.json preserves that corrected finding rather than revising the old record. Run_v3 changes only the exported field label to form_family and records the V2 predecessor SHA. Existing scientific metrics, trained coefficients, source bytes, and the canonical prediction subset remain unchanged.
