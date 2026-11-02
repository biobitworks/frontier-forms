#!/usr/bin/env python3
"""Append-only: patient-cluster paired bootstrap CIs for every committed forms arm comparison.

The original FCG_ARMS_V1 / summary CIs resample cases stratified by template. Forms
from one patient are not independent, so this recomputes each edge's CI resampling
patients instead. Existing evidence files are not modified.

    PYTHONPATH=src python3 scripts/patient_cluster_bootstrap.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frontier_forms.forms.statistics_bridge import _pairs, patient_cluster_bootstrap  # noqa: E402
from frontier_forms.statistics import admit  # noqa: E402

OUT = ROOT / "evidence/PATIENT_CLUSTER_BOOTSTRAP_V1.json"


def load(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines()]


def main():
    preds = ROOT / "evidence/forms_arms/run_v1/predictions"
    arms = {p.stem: load(p) for p in sorted(preds.glob("*.jsonl"))}
    g = json.loads((ROOT / "evidence/forms_arms/run_v1/FCG_ARMS_V1.json").read_text())
    rows = []
    for e in g["edges"]:
        pa, ch = arms[e["parent"]], arms[e["child"]]
        for split in ("overall", "test"):
            sel = (lambda r: True) if split == "overall" else (lambda r: r["split"] == "test")
            pairs = _pairs([r for r in pa if sel(r)], [r for r in ch if sel(r)])
            strat = admit(pairs, phase="discovery")
            cl = patient_cluster_bootstrap(pairs)
            rows.append({"family": "module_arms", "parent": e["parent"], "child": e["child"], "leaf": e["leaf"], "split": split,
                         "n_forms": len(pairs), "delta": round(strat["delta"], 4),
                         "ci_template_stratified_95": [round(x, 4) for x in strat["ci_delta_bootstrap_stratified_95"]],
                         "ci_patient_cluster_95": [round(x, 4) for x in cl["ci_delta_patient_cluster_95"]],
                         "patients": cl["patients"], "mcnemar_p": strat["p_mcnemar_exact_two_sided"],
                         "positive_under_both": strat["ci_delta_bootstrap_stratified_95"][0] > 0 and cl["positive_gate"]})
    b0 = load(ROOT / "evidence/forms_b0/run_v1/predictions.jsonl")
    for d in sorted((ROOT / "evidence/forms_model").glob("*/predictions.jsonl")) if (ROOT / "evidence/forms_model").exists() else []:
        ch = load(d)
        keep = {r["split"] for r in ch}
        for split in ("overall", "test"):
            sel = (lambda r: r["split"] in keep) if split == "overall" else (lambda r: r["split"] == "test")
            pairs = _pairs([r for r in b0 if sel(r)], [r for r in ch if sel(r)])
            strat = admit(pairs, phase="discovery")
            cl = patient_cluster_bootstrap(pairs)
            rows.append({"family": "learned_model", "parent": "B0-v1", "child": d.parent.name, "split": split,
                         "n_forms": len(pairs), "delta": round(strat["delta"], 4),
                         "ci_template_stratified_95": [round(x, 4) for x in strat["ci_delta_bootstrap_stratified_95"]],
                         "ci_patient_cluster_95": [round(x, 4) for x in cl["ci_delta_patient_cluster_95"]],
                         "patients": cl["patients"], "mcnemar_p": strat["p_mcnemar_exact_two_sided"],
                         "positive_under_both": strat["ci_delta_bootstrap_stratified_95"][0] > 0 and cl["positive_gate"]})
    src = {"FCG_ARMS_V1": hashlib.sha256((ROOT / "evidence/forms_arms/run_v1/FCG_ARMS_V1.json").read_bytes()).hexdigest()}
    OUT.write_text(json.dumps({"method": "paired bootstrap resampling patients with replacement (all forms of a patient move together); "
                                         "10000 reps, seed 20261102, percentile 95% CI", "sources_sha256": src, "rows": rows},
                              indent=1, sort_keys=True) + "\n")
    for r in rows:
        print(r["parent"], "->", r["child"], r["split"], r["delta"], r["ci_template_stratified_95"], r["ci_patient_cluster_95"], r["positive_under_both"])


if __name__ == "__main__":
    main()
