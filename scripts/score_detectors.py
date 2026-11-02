#!/usr/bin/env python3
"""Score M1/M2/M3 and every combination on the prebuilt error-injected forms.

    lean --run lean/FormChecks.lean data/forms_injected_v1/forms.jsonl > evidence/forms_detectors/run_v1/lean_flags.jsonl
    PYTHONPATH=src python3 scripts/score_detectors.py --lean-flags evidence/forms_detectors/run_v1/lean_flags.jsonl \
        --out evidence/forms_detectors/run_v1

Follows data/forms_injected_v1/PREREG.json. One declared deviation: the
false-positive-cost bootstrap on clean fields uses 1000 reps instead of 10000
(about 6000 paired fields per edge); the McNemar test there is exact as declared.
"""
import argparse
import html
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from frontier_forms.forms.cohort import load_cohort, sha256_bytes, sha256_file  # noqa: E402
from frontier_forms.forms.detectors import MECHANISMS, load_lean_flags, m1_merkle, m3_source_binding  # noqa: E402
from frontier_forms.forms.harness import _http  # noqa: E402
from frontier_forms.forms.server import FormState, serve  # noqa: E402
from frontier_forms.forms.templates import load_templates  # noqa: E402
from frontier_forms.statistics import admit  # noqa: E402

SHORT = {"M1_merkle_breakpoint": "M1 Merkle", "M2_lean4_constraints": "M2 Lean4", "M3_fco_source_binding": "M3 FCO"}
DATA = ROOT / "data/forms_injected_v1"


def combos():
    return [frozenset(c) for r in range(len(MECHANISMS) + 1) for c in itertools.combinations(MECHANISMS, r)]


def cname(s):
    return "none" if not s else "+".join(SHORT[m].split()[0] for m in MECHANISMS if m in s)


def auroc(pos, neg):
    """Mann-Whitney AUROC with ties counted 1/2."""
    if not pos or not neg:
        return None
    counts = defaultdict(lambda: [0, 0])
    for s in pos:
        counts[s][0] += 1
    for s in neg:
        counts[s][1] += 1
    wins, below = 0.0, 0
    for s in sorted(counts):
        p, n = counts[s]
        wins += p * below + 0.5 * p * n
        below += n
    return wins / (len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lean-flags", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    prereg = json.loads((DATA / "PREREG.json").read_text())
    fb, tb = (DATA / "forms.jsonl").read_bytes(), (DATA / "truth.jsonl").read_bytes()
    assert sha256_bytes(fb) == prereg["dataset"]["forms_sha256"], "FORMS_CHANGED_SINCE_PREREG"
    assert sha256_bytes(tb) == prereg["dataset"]["truth_sha256"], "TRUTH_CHANGED_SINCE_PREREG"
    forms = [json.loads(x) for x in fb.splitlines()]
    truth = [json.loads(x) for x in tb.splitlines()]
    lean = load_lean_flags(args.lean_flags)
    assert set(lean) == {f["form_id"] for f in forms}, "LEAN_OUTPUT_INCOMPLETE"

    members, bundles = load_cohort(ROOT / "data/forms_cohort_v1/bundles")
    httpd = serve(FormState(members, bundles, load_templates()))
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    flags = {}
    try:
        passports = {}
        for f in forms:
            pid = f["patient_id"]
            if pid not in passports:
                passports[pid] = _http(base, f"/api/passport/{pid}")
            flags[f["form_id"]] = {
                "M1_merkle_breakpoint": m1_merkle(f)["flags"],
                "M2_lean4_constraints": set(lean[f["form_id"]]),
                "M3_fco_source_binding": m3_source_binding(f, passports[pid]),
            }
    finally:
        httpd.shutdown()
        httpd.server_close()

    err_fields = defaultdict(set)
    for t in truth:
        err_fields[t["form_id"]].update(t["fields"])
    clean = [(f["form_id"], k, f["patient_id"]) for f in forms for k in sorted(f["fields"]) if k not in err_fields[f["form_id"]]]
    all_fields = [(f["form_id"], k) for f in forms for k in sorted(f["fields"])]
    types = sorted({t["error_type"] for t in truth})

    def flagged(s, fid, k):
        return any(k in flags[fid][m] for m in s)

    def detected(s, t):
        return any(flagged(s, t["form_id"], k) for k in t["fields"])

    table = {}
    for s in combos():
        det = [detected(s, t) for t in truth]
        by_type = {ty: round(sum(d for d, t in zip(det, truth) if t["error_type"] == ty) /
                             sum(t["error_type"] == ty for t in truth), 4) for ty in types}
        fp = sum(flagged(s, fid, k) for fid, k, _ in clean)
        form_has_err = {f["form_id"]: bool(err_fields[f["form_id"]]) for f in forms}
        form_flag = {f["form_id"]: any(flagged(s, f["form_id"], k) for k in f["fields"]) for f in forms}
        tp_f = sum(form_flag[x] and form_has_err[x] for x in form_flag)
        tn_f = sum((not form_flag[x]) and (not form_has_err[x]) for x in form_flag)
        tp_fields = sum(flagged(s, fid, k) for fid, k in all_fields if k in err_fields[fid])
        table[cname(s)] = {
            "mechanisms": sorted(s), "recall": round(sum(det) / len(det), 4), "recall_by_type": by_type,
            "detected": sum(det), "instances": len(det),
            "fp_rate_clean_fields": round(fp / len(clean), 4), "fp_fields": fp, "clean_fields": len(clean),
            "field_precision": round(tp_fields / (tp_fields + fp), 4) if tp_fields + fp else None,
            "form_sensitivity": round(tp_f / sum(form_has_err.values()), 4),
            "form_specificity": round(tn_f / (len(forms) - sum(form_has_err.values())), 4),
        }

    full = frozenset(MECHANISMS)
    score = {(fid, k): sum(k in flags[fid][m] for m in MECHANISMS) for fid, k in all_fields}
    pos = [score[(fid, k)] for fid, k in all_fields if k in err_fields[fid]]
    neg = [score[(fid, k)] for fid, k in all_fields if k not in err_fields[fid]]
    auc = auroc(pos, neg)

    edges = []
    for s in combos():
        for m in MECHANISMS:
            if m in s:
                continue
            c = s | {m}
            inst = [{"case_digest_sha256": t["instance_id"], "task": t["error_type"],
                     "baseline_correct": detected(s, t), "challenger_correct": detected(c, t)} for t in truth]
            fpp = [{"case_digest_sha256": f"{fid}:{k}", "task": "clean",
                    "baseline_correct": not flagged(s, fid, k), "challenger_correct": not flagged(c, fid, k)}
                   for fid, k, _ in clean]
            gain = admit(inst, reps=10000, seed=20261102)
            cost = admit(fpp, reps=1000, seed=20261102)
            attributable = gain["p_mcnemar_exact_two_sided"] < 0.05 and gain["ci_delta_bootstrap_stratified_95"][0] > 0
            edges.append({"parent": cname(s), "child": cname(c), "leaf": m,
                          "kind": "lomo_restore" if c == full else ("single_from_none" if not s else "addition"),
                          "recall_gain": round(gain["delta"], 4), "recall_gain_ci95": gain["ci_delta_bootstrap_stratified_95"],
                          "recall_gain_mcnemar_p": gain["p_mcnemar_exact_two_sided"], "recall_table": gain["table"],
                          "fp_cost": round(-cost["delta"], 4), "fp_cost_mcnemar_p": cost["p_mcnemar_exact_two_sided"],
                          "fp_cost_ci95": [round(-x, 4) for x in cost["ci_delta_bootstrap_stratified_95"][::-1]],
                          "verdict": "ATTRIBUTABLE_GAIN" if attributable else ("NO_GAIN" if gain["delta"] == 0 else "NOT_SIGNIFICANT")})
    lomo = {e["leaf"]: e for e in edges if e["kind"] == "lomo_restore"}
    single = {e["leaf"]: e for e in edges if e["kind"] == "single_from_none"}

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lean_bytes = Path(args.lean_flags).read_bytes()
    result = {
        "run_id": "FF-DETECTOR-RUN-V1", "prereg_sha256": sha256_file(DATA / "PREREG.json"),
        "forms_sha256": prereg["dataset"]["forms_sha256"], "truth_sha256": prereg["dataset"]["truth_sha256"],
        "lean_flags_sha256": sha256_bytes(lean_bytes),
        "code_sha256": {p: sha256_file(ROOT / p) for p in ("src/frontier_forms/forms/detectors.py", "lean/FormChecks.lean",
                                                            "scripts/score_detectors.py", "src/frontier_forms/forms/arms.py")},
        "combinations": table, "field_auroc_full_count_score": round(auc, 4) if auc is not None else None,
        "edges": edges,
        "per_mechanism": {m: {"single_gain": single[m]["recall_gain"], "single_p": single[m]["recall_gain_mcnemar_p"],
                              "lomo_gain": lomo[m]["recall_gain"], "lomo_p": lomo[m]["recall_gain_mcnemar_p"],
                              "lomo_ci95": lomo[m]["recall_gain_ci95"], "lomo_fp_cost": lomo[m]["fp_cost"],
                              "unique_contribution": lomo[m]["verdict"]} for m in MECHANISMS},
        "deviation": "FP-cost bootstrap uses 1000 reps (prereg said same test as gain: 10000).",
        "attribution_rule": "Gains are attributed only on single-leaf edges. A combination's recall over 'none' is the joint gain and is CONFOUNDED with respect to its members.",
    }
    (out / "DETECTOR_RESULTS_V1.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (out / "heatmap.html").write_text(render(result, types))
    for k, v in table.items():
        print(f"{k:<10} recall={v['recall']:.3f} fp={v['fp_rate_clean_fields']:.3f} sens={v['form_sensitivity']:.3f} spec={v['form_specificity']:.3f}",
              " ".join(f"{t[:2]}={v['recall_by_type'][t]:.2f}" for t in types))
    print("AUROC", result["field_auroc_full_count_score"])
    for m, v in result["per_mechanism"].items():
        print(m, v)


def render(r, types):
    e = html.escape

    def cell(v, invert=False):
        x = v if not invert else 1 - v
        hue = int(120 * x)
        return f'<td style="background:hsl({hue},65%,{88 - 30 * abs(x - 0.5)}%)">{v:.2f}</td>'
    head = "".join(f"<th>{e(t.split('_', 1)[1])}</th>" for t in types)
    rows = []
    for name, v in r["combinations"].items():
        rows.append(f"<tr><th>{e(name)}</th>" + "".join(cell(v["recall_by_type"][t]) for t in types)
                    + cell(v["recall"]) + cell(v["fp_rate_clean_fields"], invert=True)
                    + cell(v["form_sensitivity"]) + cell(v["form_specificity"]) + "</tr>")
    erows = []
    for ed in r["edges"]:
        erows.append(f"<tr><td>{e(ed['parent'])} → {e(ed['child'])}</td><td>{e(ed['kind'])}</td>"
                     f"<td>{ed['recall_gain']:+.3f}</td><td>[{ed['recall_gain_ci95'][0]:+.3f}, {ed['recall_gain_ci95'][1]:+.3f}]</td>"
                     f"<td>{ed['recall_gain_mcnemar_p']:.2g}</td><td>{ed['fp_cost']:+.3f}</td><td>{e(ed['verdict'])}</td></tr>")
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Detector gain heatmap</title><style>
body{{font:14px system-ui,sans-serif;margin:16px;background:#fff;color:#111}} table{{border-collapse:collapse;margin:12px 0}}
td,th{{border:1px solid #ccc;padding:4px 8px;text-align:center}} th{{background:#f4f4f4}} .wrap{{overflow-x:auto}}
</style></head><body>
<h1>Frontier Forms: detector gain heatmap (run v1)</h1>
<p>654 prebuilt synthetic forms, 702 injected errors (preregistered). Cells: recall per error type; FP = false-positive rate on clean fields (greener is lower). Field AUROC (count of mechanisms flagging, full set): {r['field_auroc_full_count_score']}.</p>
<div class="wrap"><table><tr><th>Combination</th>{head}<th>Recall</th><th>FP rate</th><th>Form sens.</th><th>Form spec.</th></tr>{''.join(rows)}</table></div>
<h2>Single-leaf edges (only these attribute a gain)</h2>
<div class="wrap"><table><tr><th>Edge</th><th>Kind</th><th>Recall gain</th><th>Bootstrap 95% CI</th><th>McNemar p</th><th>FP cost</th><th>Verdict</th></tr>{''.join(erows)}</table></div>
<p>{e(r['attribution_rule'])} {e(r['deviation'])}</p></body></html>
"""


if __name__ == "__main__":
    main()
