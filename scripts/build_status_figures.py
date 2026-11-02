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



# ---------------------------------------------------------------- ledger
# Every claim we tested, admitted or not. verdict: admitted, discovery, negative, null, failed, partial, not_tested
LEDGER = [
    ("FCG harness L1+L3 on forms", "0.333 -> 0.556 (30/54), 12/0 discordant, p=0.00049, Holm p=0.0059, cluster CI [0.07, 0.37]", "discovery", "#10 #17 #18 #48"),
    ("Single module L1, L2 or L3 added to B0", "0 change in form success on test (p=1.0 each)", "null", "#10"),
    ("L2 unit validation in LOMO", "removing L2 changes nothing (delta 0)", "null", "#10"),
    ("M3 source binding (injected errors)", "recall 0.989; LOMO removing M3 loses 0.563, p=2.5e-119; costs 4% false flags", "admitted", "#10"),
    ("M1 Merkle breakpoint, M2 Lean 4", "single gains 0.16 / 0.27, but 0 unique contribution once M3 is present", "null", "#10"),
    ("Per-field commitment gate (SYNFORM2-ERR)", "detection 0.13 -> 1.00, 0 false admissions; coverage falls 0.985 -> 0.876", "discovery", "#20 #21"),
    ("Fault-injection factorial, 16 arms", "full modules repair 100% by construction; not a model gain", "discovery", "#12"),
    ("Frontier Forms tools vs Pi browser-tools (hosted models)", "DeepSeek V4.1 Flash 92.0 -> 16.8 s median, fields 119/121 both; 4 models, small pilot, no held-out", "partial", "bench (#56 lane)"),
    ("Same, GPT-OSS 120B", "fields 12/58 -> 58/58 on 2 matched cases", "partial", "bench"),
    ("Same, GLM 5.3", "fields 102/105 -> 101/105 (one field worse) while 7x faster", "partial", "bench"),
    ("Qwen text mappers vs deterministic parser", "qwen2.5:1.5b 209/322, qwen3:1.7b 109/322 vs parser 283/322", "negative", "#23"),
    ("Trained logistic box validator", "540/540 = contour control 540/540; gain 0, p=1", "negative", "#14"),
    ("Random Forest box-validator factorial", "F1 0.973-0.979 vs control 1.000 at 10/30/63 patients", "negative", "#15"),
    ("D1 tiny segmentation detector", "recall 0.131, precision 0.099, F1 0.113", "failed", "#16"),
    ("D2 candidate classifier", "recall 0.956, precision 0.656, 180 false boxes; same layouts only", "partial", "#16"),
    ("Apple A2 OCR read-back of filled PDFs", "field acc 0.856 -> 0.802; dropdowns vanish, long lists cut; p=0.5", "negative", "#10"),
    ("OCR on boxed overlay images", "Apple OCR 58/70 clean vs 0/70 with boxes drawn", "negative", "#51"),
    ("Prompt injection, qwen3 with retrieved context", "attacker succeeds on 6/17 to 9/24 eligible cases", "failed", "#11"),
    ("Prompt injection, qwen2.5vl on form images", "followed the injected note 0/18", "partial", "#29 (open)"),
    ("Prompt injection, Tesseract", "copies the injected note as text in 19/57 images", "failed", "#19"),
    ("FCG context in the prompt (LongevityBench)", "L0 25 -> 28/38 discovery (p=0.55); held-out 25/39 vs 25/39", "null", "#11"),
    ("FCG context, Insilico Qwen3-0.6B (MPS)", "25 -> 24/38 and 22 -> 19/39", "negative", "#11"),
    ("Insilico P-L3c CPU rerun", "stopped by Byron at 139/693; CPU matches MPS 38/38; C1/C2 negative", "partial", "#13"),
    ("Liquid 1.2B vs Insilico 0.6B", "25/38 vs 27/38, p=0.6875", "null", "#1 #3"),
    ("Historic Insilico score on a second stack", "27/38 became 25/38", "failed", "#11"),
    ("qwen3:1.7b / qwen2.5vl on LongevityBench", "3/38 and similar: format failures", "negative", "#20"),
    ("Custody attacks (red team)", "7 weaknesses reproduced: duplicate-last-leaf collision, uncommitted parent pointers, no edge integrity, under-reporting impact view, duplicate-key parse, phantom-index proof, oracle leak via prompt hashes", "failed", "#11 #20"),
    ("Forged VERIFIED custody state", "accepted before the fix; now rejected", "admitted", "#8"),
    ("Review verifier read the working tree (F-02)", "fixed by pinning to historical commits", "admitted", "#20"),
    ("JSON-only gate, first scanner", "falsely returned PASS; fixed in 3c4c111", "failed", "#16"),
    ("Trained model M1 SFT", "one epoch-0 val loss 1.005, no adapter saved; no gain admitted", "not_tested", "#18 T08"),
    ("V2 YOLOv8n + OCR value validator", "pipeline merged, no result yet", "not_tested", "#19 T09"),
    ("Fresh replication cohort", "not run", "not_tested", "T01"),
    ("Named frontier-model baseline on the 54 test forms", "not run", "not_tested", "#56"),
]


def bench():
    return {
        "title": "Teammate bench: same hosted model, Pi browser-tools vs Frontier Forms tools (pilot)",
        "source": "bench/charts/LIVE_RESULTS.md and live_metrics.json at main@e422def (teammate lane, Fireworks-hosted models)",
        "columns": ["Fields correct, Pi", "Fields correct, our tools", "Time saved (1 - tools/Pi median)", "Cost saved (1 - tools/Pi mean)"],
        "lower_better": [False, False, False, False],
        "rows": [
            {"label": "DeepSeek V4.1 Flash [6/6 matched]", "values": [round(119/121,4), round(119/121,4), round(1-16.8/92.0,4), round(1-0.0054/0.0269,4)], "grade": "partial"},
            {"label": "GLM 5.3 [5/6 matched]", "values": [round(102/105,4), round(101/105,4), round(1-9.6/68.6,4), round(1-0.0160/0.1156,4)], "grade": "partial"},
            {"label": "Qwen Max [2/6 matched]", "values": [round(32/33,4), 1.0, round(1-16.9/79.1,4), round(1-0.0360/0.1918,4)], "grade": "partial"},
            {"label": "GPT-OSS 120B [2/6 matched]", "values": [round(12/58,4), 1.0, round(1-4.2/7.2,4), round(1-0.0018/0.0022,4)], "grade": "partial"},
        ],
        "note": "3 forms x 2 synthetic patients x 2 arms per model, temperature 0, one run per case, concurrency raised mid-run. No held-out set, no repetitions, no CI. Live numbers may change as runs finish.",
    }


GRADES = {
    "evidence": "Evidence grade: preregistered or independent run, synthetic data",
    "discovery": "Discovery grade: designed after seeing the test data; needs replication",
    "baseline": "Baseline / control",
    "negative": "Negative: no gain over control",
    "exploratory": "Exploratory: designed after a failure, same layouts",
    "running": "Running / not yet scored",
    "todo": "Not run",
    "partial": "Pilot or partial: small n, no held-out set or no statistics",
}
VERDICTS = {
    "admitted": "Admitted / promoted (evidence or a verified fix)",
    "discovery": "Positive, discovery grade (not promoted)",
    "partial": "Partial or pilot",
    "null": "Null: no detectable difference",
    "negative": "Negative: worse than or equal to control",
    "failed": "Failed or attack succeeded",
    "not_tested": "Not tested yet",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = {
        "schema": "frontier_forms.accomplishment_heatmap.v1",
        "as_of_utc": "2026-11-02T23:55:00Z",
        "main_commit": "e422def",
        "claim_ceiling": "Synthetic MITRE Synthea data only; research lanes use local inference, the teammate bench lane (panel F) uses Fireworks-hosted models; no clinical claim. Re-plots committed results; nothing new was run.",
        "stages": STAGES,
        "workstreams": [{"name": n, "prs": p, "states": s, "note": note} for n, p, s, note in WORK],
        "panels": [forms_arms(), detectors(), gates(), vision(), models(), bench()],
        "ledger": [{"claim": c, "result": r, "verdict": v, "source": s} for c, r, v, s in LEDGER],
        "verdicts": VERDICTS,
        "grades": GRADES,
    }
    (OUT / "accomplishment_heatmap.json").write_text(json.dumps(data, indent=1) + "\n")
    tpl = (ROOT / "scripts" / "status_heatmap_template.html").read_text()
    (OUT / "accomplishment_heatmap.html").write_text(tpl.replace("/*__DATA__*/null", json.dumps(data)))
    print("wrote", OUT / "accomplishment_heatmap.json", OUT / "accomplishment_heatmap.html")


if __name__ == "__main__":
    main()
