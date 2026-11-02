# Figures and images: index for judges

Every figure and image in the repository, with what it shows, how to read it, the PR that produced it and its evidence grade. All patient data is synthetic (MITRE Synthea); all inference ran locally. Regenerate with `python3 scripts/build_status_figures.py && python3 scripts/label_figures.py`.

Evidence grades: **Evidence** = preregistered or independent run; **Discovery** = built after seeing the test data, needs replication; **Negative** = no gain over the control; **Illustration** = a single example, no statistics.

## Analytic figures

| # | Figure | How to read (axes, legend) | Source PR | Grade |
|---|---|---|---|---|
| 1 | [Accomplishment heatmap: workstream status and mechanisms versus outcomes](../../docs/figures/accomplishment_heatmap.html) | 1a: rows = workstreams, columns = evidence stages, cell = status (icon + label). 1b: rows = mechanism or combination, columns = outcome metric 0-1, darker blue = better (lower-better columns shaded by 1 - value), printed number = raw value. | This PR (status 2026-11-02); data from #10 #12 #14-#23 | Mixed; each row tagged |
| 2 | [Admission-gate factorial on SYNFORM2-ERR (16 mechanism combinations)](../../docs/architecture/gate_factorial_heatmap.html) | Rows = combination of identity / rules / commitment / consistency gates. Columns = planted-error detection, false-admission rate, coverage, selective accuracy (0-1). Blue sequential ramp, darker = larger value; values printed in every cell. | #20 #21 (red team) | Discovery (replication NOT_TESTED) |
| 3 | [Injected-error detector gain heatmap (654 forms, 702 preregistered errors)](../../evidence/forms_detectors/run_v1/heatmap.html) | Rows = detector combination (M1 Merkle breakpoint, M2 Lean 4 constraints, M3 source binding). Columns = recall per error type, then overall recall, false-positive rate on clean fields, form sensitivity and specificity. Greener = better; lower table lists single-leaf edges with bootstrap 95% CI and McNemar p (only these attribute a gain). | #10 | Evidence grade (preregistered, synthetic) |
| 4 | [Fault-injection factorial: 16 module combinations at three scales](../../experiments/form_error_factorial/heatmap.html) | Select a scale (10 / 30 / 100 patients). Rows = module combination, columns = overall accuracy, paired change vs the impaired baseline, then repair outcome per attack type. Legend: fully repaired / partially repaired / still failing / missing evidence. | #12 | Discovery (faults target known corrections by design) |
| 5 | [One synthetic form: model field answers over Apple Vision OCR boxes](../../experiments/form_error_factorial/vision_overlay.html) | Image = rendered synthetic PDF. Rectangles = Apple Vision text boxes (not Qwen). Box colour: green exact match, orange missing, red wrong. Pick the comparison arm (Apple OCR, qwen2.5vl image, qwen3 OCR-text) above the image. | #12 | Illustration only (n = 1 form) |
| 6 | [Training checkpoints versus FCO/FCG ablations (statistical timeline)](../../dashboard/training_progress.html) | Panel 1: x = epoch, y = validation cross-entropy loss (one real point so far). Panel 2: rows = single changed leaf, columns = delta in percentage points with 95% CI, McNemar p and Holm-adjusted p. Panel 3: training-set size versus held-out F1 (sample-size sweep, not a learning curve). | #18 | Mixed; no trained-model gain admitted |
| 7 | [Evidence-gate state over evidence versions](../../dashboard/training_heatmap.html) | Rows = gate, columns = evidence version (not equal time). Colour: green tested PASS, orange negative statistical result, amber reported/unknown, red failure, grey untested/proposed. Click a cell for its source record. | #7 | Provenance dashboard, no performance claim |
| 8 | [Admission-gate factorial on SYNFORM2-ERR (16 combinations x 4 outcome metrics) (static SVG)](../../docs/architecture/gate_factorial_heatmap.svg) | Same as figure 2, static. | #20 #21 | Discovery |
| 9 | [Accomplishment heatmap (static PNG)](accomplishment_heatmap.png) | Static render of figure 1. | This PR | Mixed |

## Image sets (inputs, not results)

These are the synthetic form renders the models read. They are stimuli, not charts, so each set is captioned once here and in its folder README.

| Folder | Title | Caption | Source PR |
|---|---|---|---|
| [`data/forms_vision_v1/`](../../data/forms_vision_v1) | Rendered synthetic form images with gold DOM boxes | 57 PNG renders (3 blank templates + 54 filled held-out test forms) of the three Frontier Forms templates, filled from MITRE Synthea patients. GOLD_BOXES.json holds the browser DOM box of every field. Input to V1 qwen2.5vl, T1 Tesseract and the box validators. | #10 #19 |
| [`data/forms_vision_inject_v1/`](../../data/forms_vision_inject_v1) | Paired clean / prompt-injected form images | 18 clean and 18 injected renders of the same forms; the injected copy carries an instruction-like note. Used by V1i (qwen2.5vl followed it 0/18). | #10 #29 |
| [`redteam/ehr/data/forms/`](../../redteam/ehr/data/forms) | SYNFORM2 synthetic forms with planted-error twins | Red-team form renders; *.inj.png is the planted-error or injected twin of the clean image. Input to the admission-gate factorial and the Qwen mapper lanes. | #11 #20 #23 |
| [`evidence/forms_apple/forms/`](../../evidence/forms_apple/forms) | Frozen blank PDF forms for the Apple arm | The three templates as fillable PDFs; PDFKit fills them as Preview would. | #10 |
| [`evidence/forms_apple/run_v1/samples/`](../../evidence/forms_apple/run_v1/samples) | Apple arm spot-check PDFs with OCR read-back | Two filled PDFs per template, each with its Vision OCR read-back JSON. Shows the two failure modes: dropdown values do not render, long medication lists are cut off. | #10 |
| [`experiments/form_error_factorial/sample_vision/`](../../experiments/form_error_factorial/sample_vision) | Single synthetic intake form for the vision overlay | One rendered synthetic intake form (PNG + PDF) with the raw model replies in model_field_answers.json; drawn in vision_overlay.html. | #12 |
| [`experiments/form_error_factorial/prebuilt_forms/`](../../experiments/form_error_factorial/prebuilt_forms) | Prebuilt synthetic HTML intake fixtures | 15 synthetic HTML intake forms used as fault-injection fixtures (MANIFEST.json lists hashes). | #12 |

## Not in the repo

Bounding-box overlay galleries (gold / qwen2.5vl / Tesseract) are on open PR #29, not on main. V2 detector renders, model weights and raw model prompts stay on the local Macs by policy.
