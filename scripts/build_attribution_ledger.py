#!/usr/bin/env python3
"""Build the frontier-forms attribution ledger from committed evidence.

Every row keeps three quantities apart:
  model_weights  exact model/checkpoint/adapter on each side (with hashes), or the rule/tool version
  mechanism      which FCG mechanism is enabled on each side
  outcome        the measured paired difference (metric, split, n, delta, CI, exact McNemar p)

Attribution is SINGLE_MECHANISM when only one mechanism differs and the
weights are identical; SINGLE_MODEL_CHANGE when only the weights differ;
otherwise CONFOUNDED. Rows are regenerated from evidence files, never hand-edited.

    PYTHONPATH=src python3 scripts/build_attribution_ledger.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/ATTRIBUTION_LEDGER_FORMS.jsonl"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).relative_to(ROOT))


def outcome(stats, metric, split):
    return {"metric": metric, "split": split, "n": stats["n"], "delta": round(stats["delta"], 4),
            "ci95": [round(x, 4) for x in stats["ci_delta_bootstrap_stratified_95"]],
            "mcnemar_p": stats["p_mcnemar_exact_two_sided"], "table": stats["table"]}


def classify(w_changed, mech_changed):
    if w_changed and mech_changed:
        return "CONFOUNDED"
    if w_changed:
        return "SINGLE_MODEL_CHANGE"
    if len(mech_changed) == 1:
        return "SINGLE_MECHANISM"
    return "CONFOUNDED" if mech_changed else "NO_CHANGE"


def main():
    rows = []
    freeze = json.loads((ROOT / "evidence/forms_b0/B0_FREEZE_V1.json").read_text())
    rules = {"kind": "deterministic rules (no learned weights)", "b0_sha256": freeze["arm"]["sha256"],
             "arms_sha256": sha(ROOT / "src/frontier_forms/forms/arms.py")}

    # 1. module arms (incremental + LOMO)
    fcg = ROOT / "evidence/forms_arms/run_v1/FCG_ARMS_V1.json"
    g = json.loads(fcg.read_text())
    mods = {n["arm"]: set(n["modules"]) for n in g["nodes"]}
    for e in g["edges"]:
        changed = sorted(mods[e["child"]] ^ mods[e["parent"]])
        for split in ("test", "overall"):
            rows.append({"family": "module_arms", "parent_arm": e["parent"], "child_arm": e["child"],
                         "model_weights": {"parent": rules, "child": rules, "changed": False},
                         "mechanism": {"changed": changed, "parent_enabled": sorted(mods[e["parent"]]),
                                       "child_enabled": sorted(mods[e["child"]]), "edge_kind": e["kind"]},
                         "outcome": outcome(e[split], "required_fields_correct per form", split),
                         "attribution": classify(False, changed),
                         "evidence": {"path": rel(fcg), "sha256": sha(fcg)}})

    # 2. detectors (all single-leaf edges)
    det = ROOT / "evidence/forms_detectors/run_v1/DETECTOR_RESULTS_V1.json"
    d = json.loads(det.read_text())
    lean = json.loads((ROOT / "evidence/forms_detectors/run_v1/LEAN4_RECEIPT.json").read_text())
    for e in d["edges"]:
        rows.append({"family": "detectors", "parent_arm": e["parent"], "child_arm": e["child"],
                     "model_weights": {"parent": {"kind": "no model"}, "child": {"kind": "no model",
                                       "lean": lean["tool"] if e["leaf"].startswith("M2") else None}, "changed": False},
                     "mechanism": {"changed": [e["leaf"]], "edge_kind": e["kind"]},
                     "outcome": {"metric": "injected-error instance recall", "split": "all", "n": e["recall_table"]["n"],
                                 "delta": e["recall_gain"], "ci95": e["recall_gain_ci95"], "mcnemar_p": e["recall_gain_mcnemar_p"],
                                 "table": e["recall_table"], "fp_cost": e["fp_cost"], "fp_cost_mcnemar_p": e["fp_cost_mcnemar_p"]},
                     "attribution": "SINGLE_MECHANISM",
                     "evidence": {"path": rel(det), "sha256": sha(det)}})

    # 3. Apple front end vs B0 (same rules; perception front end differs)
    ap = ROOT / "evidence/forms_apple/run_v1"
    if (ap / "receipt.json").exists():
        rec = json.loads((ap / "receipt.json").read_text())
        apple = {"kind": "Apple Vision VNRecognizeTextRequest (on-device, CPU) + PDFKit",
                 "macos": rec["host"]["macos"], "tool_source_sha256": rec["tool_source_sha256"]}
        for tag, mech in (("A1", ["front_end:dom->apple_ocr_pdfkit"]),
                          ("A2", ["front_end:dom->apple_ocr_pdfkit", "ocr_readback_of_filled_pdf"])):
            s = json.loads((ap / f"summary_{tag}.json").read_text())
            for split, key in (("overall", "overall"), ("test", "test_split")):
                rows.append({"family": "apple_front_end", "parent_arm": "B0-v1", "child_arm": s["arm"],
                             "model_weights": {"parent": rules, "child": {**rules, "perception": apple}, "changed": True},
                             "mechanism": {"changed": mech},
                             "outcome": outcome(s["paired_vs_B0"][key], "required_fields_correct per form", split),
                             "attribution": "CONFOUNDED" if len(mech) > 1 else "SINGLE_MODEL_CHANGE",
                             "evidence": {"path": rel(ap / f"summary_{tag}.json"), "sha256": sha(ap / f"summary_{tag}.json")}})

    # 4. learned models vs B0 (and SFT vs zero-shot when both exist)
    md = ROOT / "evidence/forms_model"
    arms = {}
    for p in sorted(md.glob("*/receipt.json")) if md.exists() else []:
        rec = json.loads(p.read_text())
        s = json.loads((p.parent / "summary.json").read_text())
        ident = {k: rec.get(k) for k in ("base_model", "base_revision", "adapter_path", "adapter_sha256")}
        arms[rec["arm"]] = (ident, p.parent)
        for split, key in (("validation+test", "overall"), ("test", "test_split")):
            if key in s["paired_vs_B0"]:
                rows.append({"family": "learned_model", "parent_arm": "B0-v1", "child_arm": rec["arm"],
                             "model_weights": {"parent": rules, "child": ident, "changed": True},
                             "mechanism": {"changed": ["mapper:rules->model"]},
                             "outcome": outcome(s["paired_vs_B0"][key], "required_fields_correct per form", split),
                             "attribution": "CONFOUNDED",
                             "note": "rules -> model replaces the whole mapper; read as an arm comparison, not a single mechanism",
                             "evidence": {"path": rel(p.parent / "summary.json"), "sha256": sha(p.parent / "summary.json")}})

    # SFT adapter vs zero-shot base: same base weights + prompt, only the adapter differs
    m0 = next((k for k in arms if k.startswith("M0")), None)
    m1 = next((k for k in arms if k.startswith("M1")), None)
    if m0 and m1:
        import sys
        sys.path.insert(0, str(ROOT / "src"))
        from frontier_forms.forms.statistics_bridge import paired_vs_b0
        load = lambda d: [json.loads(x) for x in (d / "predictions.jsonl").read_text().splitlines()]
        res = paired_vs_b0(load(arms[m0][1]), load(arms[m1][1]))
        for split, key in (("validation+test", "overall"), ("test", "test_split")):
            rows.append({"family": "learned_model", "parent_arm": m0, "child_arm": m1,
                         "model_weights": {"parent": arms[m0][0], "child": arms[m1][0], "changed": True},
                         "mechanism": {"changed": []},
                         "outcome": outcome(res[key], "required_fields_correct per form", split),
                         "attribution": "SINGLE_MODEL_CHANGE",
                         "evidence": {"path": rel(arms[m1][1] / "predictions.jsonl"), "sha256": sha(arms[m1][1] / "predictions.jsonl")}})

    OUT.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    counts = {}
    for r in rows:
        counts[r["attribution"]] = counts.get(r["attribution"], 0) + 1
    print(len(rows), counts)


if __name__ == "__main__":
    main()
