#!/usr/bin/env python3
"""Build the 2026-11-02 accomplishment heatmap for judges.

Reads merged evidence on main where a machine-readable source exists and uses
the stated value from the merged PR/README otherwise (each row names its source).
Writes, under docs/figures/:
  accomplishment_heatmap.json  - every plotted number with its source and grade
  accomplishment_heatmap.html  - self-contained page (no fetch, opens from file://)

Render the PNG with:  node scripts/render_status_figures.js
No model is run here; this only re-plots committed results.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"


def load(rel):
    return json.loads((ROOT / rel).read_text())


# ---------------------------------------------------------------- panel A
# Workstream x stage status. States: done, discovery, negative, running, todo, na
STAGES = ["Data frozen", "Implemented", "Executed", "Paired stats", "Replicated / new cohort"]
WORK = [
    ("Synthea cohort, form server, oracle", "#10", ["done", "done", "done", "na", "todo"],
     "100 patients, splits 63/19/18, byte-reproducible. Two oracle rules still need PI sign-off (T02)."),
    ("B0 baseline (frozen rule filler)", "#10 #17", ["done", "done", "done", "na", "todo"],
     "33.3% full-form success (18/54) on the held-out test split."),
    ("FCG harness L1-L3 + LOMO", "#10 #17 #18 #19", ["done", "done", "done", "discovery", "todo"],
     "0.333 -> 0.556 (12/0 discordant, p=0.00049). Discovery grade: modules written after B0 errors were seen (T01)."),
    ("Injected-error detectors M1-M3", "#10", ["done", "done", "done", "done", "todo"],
     "Preregistered: 654 forms, 702 injected errors. M3 source binding recall 0.99; LOMO: removing M3 loses 0.563 recall (p=2.5e-119), while M1 and M2 add nothing once M3 is present."),
    ("Admission-gate factorial (SYNFORM2-ERR)", "#20 #21", ["done", "done", "done", "discovery", "todo"],
     "Per-field commitment leaf: detection 0.13 -> 1.00, 0 false admissions. Replication NOT_TESTED."),
    ("Fault-injection factorial, 16 arms", "#12", ["done", "done", "done", "discovery", "todo"],
     "Seeded faults with known corrections; 100% repair is by design, not a model gain."),
    ("OCR arms: Tesseract, Apple Vision/PDFKit", "#10 #11 #19", ["done", "done", "done", "negative", "todo"],
     "Tesseract labels 0.967 / values 0.787. Apple A2 read-back loses dropdowns and long lists (p=0.5)."),
    ("VLM qwen2.5vl:3b boxes + injection", "#19 (#29 open)", ["done", "done", "done", "discovery", "todo"],
     "Box recall 0.821, value read 0.736, 24 s/page. Injection followed 0/18 (V1i on open PR #29)."),
    ("Trained box validators (#14 #15 #16)", "#14 #15 #16", ["done", "done", "done", "negative", "todo"],
     "No gain over deterministic contour control. D2 recall 0.956 / precision 0.656 is exploratory; no new-layout test."),
    ("V2 YOLOv8n detector + OCR value check", "#19", ["done", "done", "running", "todo", "todo"],
     "Pipeline merged; run in progress on MacBookPro (T09)."),
    ("Qwen text mappers on OCR lines", "#23", ["done", "done", "done", "negative", "todo"],
     "Both Qwen mappers below the deterministic parser on identical input (209 and 109 vs 283 of 322 fields)."),
    ("Post-training arm M0 / M1 SFT / M2", "T08", ["done", "done", "running", "todo", "todo"],
     "Qwen2.5-0.5B LoRA: one epoch-0 val loss (1.005), no adapter saved. Restart on MacBookPro."),
    ("Custody: Merkle, Lean 4, red-team replay", "#3 #8 #11 #13 #20", ["done", "done", "done", "done", "na"],
     "All roots recomputed independently; 7 custody weaknesses reproduced as tests; forged-custody fix (#8)."),
    ("CI, gitleaks, JSON-only publication gate", "#17 #27 #30 #39 #43", ["na", "done", "done", "na", "na"],
     "Full-history gitleaks; 123 legacy files pinned by exact blob; new images under data/evidence/experiments rejected."),
    ("Prompt-injection filter", "T04", ["done", "todo", "todo", "todo", "todo"],
     "Measured (V1i, Tesseract reads the note in 19/57) but no filter exists."),
    ("Noisy / scanned renders", "T03", ["todo", "todo", "todo", "todo", "todo"],
     "All arms read clean browser renders."),
    ("Cost / latency per correct form", "T05", ["na", "todo", "discovery", "todo", "todo"],
     "Per-page latency recorded for some arms; no seconds-per-correct-form metric."),
    ("Fresh replication cohort", "T01", ["todo", "todo", "todo", "todo", "todo"],
     "Needs a preregistered new Synthea seed scored once with frozen arms."),
]

# ---------------------------------------------------------------- panel B
def forms_arms():
    d = load("evidence/forms_arms/run_v1/FCG_ARMS_V1.json")
    rows = []
    for n in d["nodes"]:
        t = n["metrics"]["by_split"]["test"]
        rows.append({
            "label": n["arm"],
            "values": [t["full_form_success_required"], t["field_accuracy"],
                       t["unsupported_answer_rate"], t["missing_data_recall"]],
            "grade": "baseline" if n["arm"] == "B0" else "discovery",
        })
    return {
        "title": "Form filling: B0 plus harness modules (54 held-out test forms)",
        "source": "evidence/forms_arms/run_v1/FCG_ARMS_V1.json (PR #10)",
        "columns": ["Full-form success", "Field accuracy", "Unsupported answers (lower better)", "Missing-data recall"],
        "lower_better": [False, False, True, False],
        "rows": rows,
        "note": "L1 evidence abstain, L2 unit validation, L3 clinical filter. Only L1+L3 together move form success (+0.222, p=0.00049). Discovery grade.",
    }


def detectors():
    d = load("evidence/forms_detectors/run_v1/DETECTOR_RESULTS_V1.json")
    rows = []
    order = ["none", "M1", "M2", "M3", "M1+M2", "M1+M3", "M2+M3", "M1+M2+M3"]
    for k in order:
        c = d["combinations"].get(k)
        if c is None:
            continue
        rows.append({"label": k, "values": [c["recall"], c["fp_rate_clean_fields"], c["form_sensitivity"], c["form_specificity"]],
                     "grade": "baseline" if k == "none" else "evidence"})
    return {
        "title": "Injected-error detectors (preregistered: 654 forms, 702 errors)",
        "source": "evidence/forms_detectors/run_v1/DETECTOR_RESULTS_V1.json (PR #10)",
        "columns": ["Error recall", "False-flag rate, clean fields (lower better)", "Form sensitivity", "Form specificity"],
        "lower_better": [False, True, False, False],
        "rows": rows,
        "note": "M1 Merkle breakpoint, M2 Lean 4 constraints, M3 source binding. Single-leaf edges are attributable; combinations are joint.",
    }


def gates():
    d = load("evidence/redteam/gate_factorial.json")["configurations"]
    order = ["none", "identity", "rules", "consistency", "commitment", "identity+rules",
             "rules+consistency", "rules+commitment", "identity+rules+commitment+consistency"]
    rows = []
    for k in order:
        c = d[k]
        rows.append({"label": k, "values": [c["planted_detection_rate"], c["false_admission_rate_of_all"], c["coverage"], c["selective_accuracy"]],
                     "grade": "baseline" if k == "none" else "discovery"})
    return {
        "title": "Admission-gate factorial (SYNFORM2-ERR: 135 images, 945 field cells)",
        "source": "evidence/redteam/gate_factorial.json (PRs #20/#21); all 16 rows in docs/architecture/gate_factorial_heatmap.html",
        "columns": ["Planted-error detection", "False admissions (lower better)", "Coverage", "Selective accuracy"],
        "lower_better": [False, True, False, False],
        "rows": rows,
        "note": "Extractor qwen2.5vl:3b; challenger Apple Vision OCR. Commitment = salted per-field hash in the FCG leaf. Replication NOT_TESTED.",
    }


def vision():
    v1 = load("evidence/forms_vision/V1-qwen2.5vl-3b/summary.json")
    t1 = load("evidence/forms_vision/T1-tesseract-redteam/summary.json")
    return {
        "title": "Reading the form image (evaluation set differs by row; compare within a set only)",
        "source": "evidence/forms_vision/*/summary.json (PR #19); box validators from PRs #14 #15 #16",
        "columns": ["Value read exactly", "Box recall @IoU 0.5", "Box precision"],
        "lower_better": [False, False, False],
        "rows": [
            {"label": "Tesseract 5.5.3 (T1) [57 renders]", "values": [t1["value_read_match_nonblank"], None, None], "grade": "evidence"},
            {"label": "qwen2.5vl:3b (V1) [57 renders]", "values": [v1["value_read_match_nonblank"], v1["box_recall_iou50"],
                                                       round(v1["fields"] * v1["box_recall_iou50"] / (v1["fields"] * v1["box_recall_iou50"] + v1["false_boxes"]), 4)],
             "grade": "evidence"},
            {"label": "Contour control (deterministic) [54 test forms, 540 boxes]", "values": [None, 1.0, 1.0], "grade": "baseline"},
            {"label": "Logistic box validator (#14) [54 test forms, 540 boxes]", "values": [None, 1.0, 1.0], "grade": "negative"},
            {"label": "D1 tiny segmenter (#16) [36 test images, 360 boxes]", "values": [None, 0.1306, 0.0994], "grade": "negative"},
            {"label": "D2 candidate classifier (#16) [36 test images, 360 boxes]", "values": [None, 0.9556, 0.6565], "grade": "exploratory"},
            {"label": "V2 YOLOv8n + OCR check (#19)", "values": [None, None, None], "grade": "running"},
        ],
        "note": "Rows are grouped by evaluation set: T1 and V1 on the same 57 renders (570 fields); the contour control and #14 on the same 54 filled test forms (540 boxes); D1 and D2 on 36 patient-disjoint test images (360 boxes), with no contour control on that set. Box precision for V1 = matched boxes / (matched + 213 false boxes). #14 and the contour control tie at 540/540 (gain 0). #15 RF F1 0.973 vs control 1.000.",
    }


def models():
    return {
        "title": "Local models vs deterministic code on identical input",
        "source": "evidence/redteam/lanes/MAP_*_synform2_test_META.json (PR #23); evidence/baseline/BASELINE_V1.json (PR #17)",
        "columns": ["Fields correct (SYNFORM2 test, 322)", "Full-form success (54 test forms)"],
        "lower_better": [False, False],
        "rows": [
            {"label": "Geometric parser (deterministic)", "values": [round(283 / 322, 4), None], "grade": "baseline"},
            {"label": "qwen2.5:1.5b mapper", "values": [round(209 / 322, 4), None], "grade": "negative"},
            {"label": "qwen3:1.7b mapper", "values": [round(109 / 322, 4), None], "grade": "negative"},
            {"label": "B0-v1 (frozen rules)", "values": [None, 0.3333], "grade": "baseline"},
            {"label": "M0 Qwen2.5-0.5B base", "values": [None, None], "grade": "running"},
            {"label": "M1 Qwen2.5-0.5B SFT", "values": [None, None], "grade": "todo"},
            {"label": "M1 + harness", "values": [None, None], "grade": "todo"},
        ],
        "note": "Empty cells are NOT RUN, never zero. The post-training arm is the main missing result (T08).",
    }


GRADES = {
    "evidence": "Evidence grade: preregistered or independent run, synthetic data",
    "discovery": "Discovery grade: designed after seeing the test data; needs replication",
    "baseline": "Baseline / control",
    "negative": "Negative: no gain over control",
    "exploratory": "Exploratory: designed after a failure, same layouts",
    "running": "Running / not yet scored",
    "todo": "Not run",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = {
        "schema": "frontier_forms.accomplishment_heatmap.v1",
        "as_of_utc": "2026-11-02T23:45:00Z",
        "main_commit": "908b6aa",
        "claim_ceiling": "Synthetic MITRE Synthea data only; local inference only; no clinical claim. Re-plots committed results; nothing new was run.",
        "stages": STAGES,
        "workstreams": [{"name": n, "prs": p, "states": s, "note": note} for n, p, s, note in WORK],
        "panels": [forms_arms(), detectors(), gates(), vision(), models()],
        "grades": GRADES,
    }
    (OUT / "accomplishment_heatmap.json").write_text(json.dumps(data, indent=1) + "\n")
    tpl = (ROOT / "scripts" / "status_heatmap_template.html").read_text()
    (OUT / "accomplishment_heatmap.html").write_text(tpl.replace("/*__DATA__*/null", json.dumps(data)))
    print("wrote", OUT / "accomplishment_heatmap.json", OUT / "accomplishment_heatmap.html")


if __name__ == "__main__":
    main()
