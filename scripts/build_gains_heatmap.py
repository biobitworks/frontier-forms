#!/usr/bin/env python3
"""Colour-coded gains heatmap: every intervention vs its own baseline, per outcome metric.

Writes docs/figures/gains_heatmap.{json,csv,html}. Render the PNG with
  node scripts/render_status_figures.js gains
Cell colour: green = gain, red = loss, grey = null (p >= 0.05 or |delta| < 0.005),
blank = not measured. Lighter shade = no p-value (pilot or descriptive).
Every value is copied from a merged evidence file named in the row's source.
Deltas are always "better minus baseline" in the metric's own direction, so for
false flags a negative raw change is shown as a positive gain.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"

METRICS = [
    ("field", "Field accuracy"),
    ("form", "Full-form success"),
    ("caught", "Errors caught (recall)"),
    ("false", "False flags / admissions (lower is better)"),
    ("speed", "Time saved"),
]
LOWER_BETTER = {"false"}

# group, row label, grade, baseline label, source, {metric: (raw delta, p or None)}
# grade: A admitted, D discovery, N null/negative, P pilot, U untested
ROWS = [
    ("Form filling, 54 held-out test forms", "B0 + L1 evidence abstain", "N", "B0 rules", "evidence/forms_arms/run_v1/FCG_ARMS_V1.json (#10)",
     {"field": (0.0519, None), "form": (0.0, 1.0)}),
    ("Form filling, 54 held-out test forms", "B0 + L2 unit validation", "N", "B0 rules", "FCG_ARMS_V1.json (#10)",
     {"field": (0.0333, None), "form": (0.0, 1.0)}),
    ("Form filling, 54 held-out test forms", "B0 + L3 clinical filter", "N", "B0 rules", "FCG_ARMS_V1.json (#10)",
     {"field": (0.0556, None), "form": (0.0, 1.0)}),
    ("Form filling, 54 held-out test forms", "B0 + L1 + L3", "D", "B0 rules", "FCG_ARMS_V1.json (#10, #17, #48)",
     {"field": (0.0889, None), "form": (0.2222, 0.00049)}),
    ("Form filling, 54 held-out test forms", "B0 + L1 + L2 + L3 (full harness)", "D", "B0 rules", "FCG_ARMS_V1.json (#10, #17)",
     {"field": (0.1222, None), "form": (0.2222, 0.00049)}),
    ("Form filling, 218 forms", "Apple Vision OCR read-back of filled PDF (A2)", "N", "B0 rules", "evidence/forms_apple/README.md (#10)",
     {"field": (-0.054, None), "form": (-0.009, 0.5)}),
    ("Trained components, 46 SYNFORM2 test images (prereg)", "Learned OCR post-correction (A1)", "D", "page OCR + rules (A0)", "evidence/redteam/trained_gain/trained_gain_summary.json (#51)",
     {"field": (round(13 / 322, 4), None), "form": (round(8 / 46, 4), 0.0234)}),
    ("Trained components, 46 SYNFORM2 test images (prereg)", "Trained YOLOv8n detector crops (A2)", "N", "A0", "trained_gain_summary.json (#51)",
     {"field": (round(-7 / 322, 4), None), "form": (round(-5 / 46, 4), 0.534)}),
    ("Trained components, 46 SYNFORM2 test images (prereg)", "Detector crops + learned correction (A3)", "N", "A0", "trained_gain_summary.json (#51)",
     {"field": (round(5 / 322, 4), None), "form": (round(1 / 46, 4), 1.0)}),
    ("Local Qwen vs deterministic parser, 322 fields", "qwen2.5:1.5b mapper", "N", "geometric parser", "evidence/redteam/lanes/MAP_* (#23)",
     {"field": (round((209 - 283) / 322, 4), None)}),
    ("Local Qwen vs deterministic parser, 322 fields", "qwen3:1.7b mapper", "N", "geometric parser", "evidence/redteam/lanes/MAP_* (#23)",
     {"field": (round((109 - 283) / 322, 4), None)}),
    ("Injected-error detectors, 702 preregistered errors", "M1 Merkle breakpoint", "A", "no detector", "evidence/forms_detectors/run_v1/DETECTOR_RESULTS_V1.json (#10)",
     {"caught": (0.1624, 9.6e-35), "false": (0.0, 1.0)}),
    ("Injected-error detectors, 702 preregistered errors", "M2 Lean 4 constraints", "A", "no detector", "DETECTOR_RESULTS_V1.json (#10)",
     {"caught": (0.2678, 5.1e-57), "false": (0.0005, None)}),
    ("Injected-error detectors, 702 preregistered errors", "M3 source binding", "A", "no detector", "DETECTOR_RESULTS_V1.json (#10)",
     {"caught": (0.9886, 2.4e-209), "false": (0.0407, None)}),
    ("Injected-error detectors, 702 preregistered errors", "M1 + M2 + M3", "A", "no detector", "DETECTOR_RESULTS_V1.json (#10)",
     {"caught": (0.9886, None), "false": (0.0407, None)}),
    ("Injected-error detectors, 702 preregistered errors", "Remove M3 from full set (LOMO)", "A", "M1 + M2 + M3", "DETECTOR_RESULTS_V1.json (#10)",
     {"caught": (-0.5627, 2.5e-119), "false": (-0.0407, None)}),
    ("Admission gates, 945 field cells (SYNFORM2-ERR)", "Identity gate", "D", "no gate", "evidence/redteam/gate_factorial.json (#20, #21)",
     {"caught": (0.129, None), "false": (-0.016, None)}),
    ("Admission gates, 945 field cells (SYNFORM2-ERR)", "Rules gate (Lean-checked)", "D", "no gate", "gate_factorial.json (#20, #21)",
     {"caught": (0.379, None), "false": (-0.043, None)}),
    ("Admission gates, 945 field cells (SYNFORM2-ERR)", "Consistency gate (Apple OCR vs qwen2.5vl)", "D", "no gate", "gate_factorial.json (#20, #21)",
     {"caught": (0.185, None), "false": (-0.031, None)}),
    ("Admission gates, 945 field cells (SYNFORM2-ERR)", "Per-field commitment gate", "D", "no gate", "gate_factorial.json (#20, #21); descriptive cell rates (the Holm test there covers image-level success)",
     {"caught": (0.870, None), "false": (-0.109, None)}),
    ("Box detection vs deterministic contour control", "Logistic box validator", "N", "contour control", "evidence/forms_box_validator/run_v3 (#14)",
     {"caught": (0.0, 1.0), "false": (0.0, None)}),
    ("Box detection vs deterministic contour control", "Random Forest box validator (63 patients)", "N", "contour control", "evidence/local_box_validator/v2_medium.json (#15)",
     {"caught": (-0.0519, None)}),
    ("FCG context in the prompt (LongevityBench, not forms)", "Full FCG, L0 model, discovery 38", "N", "no context", "redteam/REDTEAM_REPORT.md (#11)",
     {"field": (round(3 / 38, 4), 0.55)}),
    ("FCG context in the prompt (LongevityBench, not forms)", "Full FCG, L0 model, held-out 39", "N", "no context", "redteam/REDTEAM_REPORT.md (#11)",
     {"field": (0.0, 1.0)}),
    ("FCG context in the prompt (LongevityBench, not forms)", "Full FCG, Insilico 0.6B, held-out 39", "N", "no context", "redteam/REDTEAM_REPORT.md (#11)",
     {"field": (round(-3 / 39, 4), None)}),
    ("Hosted-model bench: same model, our tools vs Pi browser-tools (pilot)", "DeepSeek V4.1 Flash", "P", "Pi browser-tools", "bench/charts/LIVE_RESULTS.md",
     {"field": (0.0, None), "speed": (round(1 - 16.8 / 92.0, 4), None)}),
    ("Hosted-model bench: same model, our tools vs Pi browser-tools (pilot)", "GLM 5.3", "P", "Pi browser-tools", "bench/charts/LIVE_RESULTS.md",
     {"field": (round((115 - 118) / 121, 4), None), "speed": (round(1 - 9.2 / 70.0, 4), None)}),
    ("Hosted-model bench: same model, our tools vs Pi browser-tools (pilot)", "Qwen Max", "P", "Pi browser-tools", "bench/charts/LIVE_RESULTS.md",
     {"field": (round((121 - 116) / 121, 4), None), "speed": (round(1 - 15.0 / 81.8, 4), None)}),
    ("Hosted-model bench: same model, our tools vs Pi browser-tools (pilot)", "GPT-OSS 120B", "P", "Pi browser-tools", "bench/charts/LIVE_RESULTS.md",
     {"field": (round((114 - 19) / 121, 4), None), "speed": (round(1 - 5.8 / 8.8, 4), None)}),
    ("Not yet measured", "Trained form-filling LLM (Qwen2.5-0.5B SFT, M1)", "U", "B0 rules", "T08", {}),
    ("Not yet measured", "V2 YOLOv8n detector + OCR value check", "U", "contour control", "T09", {}),
]

GRADE = {"A": "Admitted", "D": "Admitted (PI), discovery provenance", "N": "Null / negative", "P": "Pilot", "U": "Untested"}
# Byron (PI) admitted all discovery-grade results on 2026-11-02. They keep a provenance caveat:
# designed or analysed after seeing the data, and not yet replicated on a fresh cohort.
PROVENANCE = {"D": "Admitted by the PI on 2026-11-02. Discovery provenance: designed after seeing the data; not replicated on a fresh cohort."}

# Novel = a Frontier Forms mechanism; Standard = off-the-shelf training, OCR, VLM, LLM or detector.
KIND = {
    "B0 + L1 evidence abstain": "Novel", "B0 + L2 unit validation": "Novel", "B0 + L3 clinical filter": "Novel",
    "B0 + L1 + L3": "Novel", "B0 + L1 + L2 + L3 (full harness)": "Novel",
    "Apple Vision OCR read-back of filled PDF (A2)": "Standard",
    "Learned OCR post-correction (A1)": "Novel",
    "Trained YOLOv8n detector crops (A2)": "Standard",
    "Detector crops + learned correction (A3)": "Mixed",
    "qwen2.5:1.5b mapper": "Standard", "qwen3:1.7b mapper": "Standard",
    "M1 Merkle breakpoint": "Novel", "M2 Lean 4 constraints": "Novel", "M3 source binding": "Novel",
    "M1 + M2 + M3": "Novel", "Remove M3 from full set (LOMO)": "Novel",
    "Identity gate": "Novel", "Rules gate (Lean-checked)": "Novel",
    "Consistency gate (Apple OCR vs qwen2.5vl)": "Novel", "Per-field commitment gate": "Novel",
    "Logistic box validator": "Standard", "Random Forest box validator (63 patients)": "Standard",
    "Full FCG, L0 model, discovery 38": "Novel", "Full FCG, L0 model, held-out 39": "Novel",
    "Full FCG, Insilico 0.6B, held-out 39": "Novel",
    "DeepSeek V4.1 Flash": "Novel", "GLM 5.3": "Novel", "Qwen Max": "Novel", "GPT-OSS 120B": "Novel",
    "Trained form-filling LLM (Qwen2.5-0.5B SFT, M1)": "Standard",
    "V2 YOLOv8n detector + OCR value check": "Standard",
}


def classify(metric, raw, p):
    gain = -raw if metric in LOWER_BETTER else raw
    if abs(gain) < 0.005 or (p is not None and p >= 0.05):
        return gain, "null"
    return gain, ("gain" if gain > 0 else "loss")


def summary(cells):
    out = {}
    for k in ("Novel", "Standard", "Mixed"):
        cs = [c for c in cells if c["kind"] == k]
        out[k] = {c: sum(1 for x in cs if x["class"] == c) for c in ("gain", "loss", "null")}
    return out


def main():
    cells = []
    for group, label, grade, base, src, vals in ROWS:
        for key, name in METRICS:
            if key not in vals:
                continue
            raw, p = vals[key]
            gain, cls = classify(key, raw, p)
            cells.append({"group": group, "intervention": label, "grade": GRADE[grade], "baseline": base, "metric": name,
                          "raw_delta": raw, "gain_delta": round(gain, 4), "p": p, "class": cls,
                          "p_note": "none (pilot or descriptive)" if p is None else "", "kind": KIND[label],
                          "provenance": PROVENANCE.get(grade, ""), "source": src})
    data = {"schema": "frontier_forms.gains_heatmap.v1", "as_of_utc": "2026-11-03T00:15:00Z",
            "rule": "green = gain, red = loss, grey = null (p >= 0.05 or |delta| < 0.005); lighter = no p-value; blank = not measured",
            "metrics": [n for _, n in METRICS], "lower_better": [n for k, n in METRICS if k in LOWER_BETTER],
            "rows": [{"group": g, "intervention": l, "grade": GRADE[gr], "kind": KIND[l], "provenance": PROVENANCE.get(gr, ""),
                      "baseline": b, "source": s} for g, l, gr, b, s, _ in ROWS],
            "kinds": {"Novel": "Frontier Forms mechanism (FCG harness, evidence graph, source binding, Merkle, Lean admission, LOMO, learned OCR correction, tool layer)",
                      "Standard": "Off-the-shelf training or model (LoRA SFT, OCR, VLM, small LLM, box detector or classifier)",
                      "Mixed": "Standard component combined with a novel one"},
            "gain_by_kind": summary(cells),
            "cells": cells}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gains_heatmap.json").write_text(json.dumps(data, indent=1) + "\n")
    with open(OUT / "gains_heatmap.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cells[0].keys()))
        w.writeheader()
        w.writerows(cells)
    tpl = (ROOT / "scripts" / "gains_heatmap_template.html").read_text()
    (OUT / "gains_heatmap.html").write_text(tpl.replace("/*__DATA__*/null", json.dumps(data)))
    print("cells", len(cells), "rows", len(ROWS), data["gain_by_kind"])


if __name__ == "__main__":
    main()
