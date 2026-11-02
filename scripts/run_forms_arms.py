#!/usr/bin/env python3
"""Run incremental and LOMO module arms against frozen B0 and build the evidence graph.

Arms: B0, B0+each single module, the cumulative chain, the full candidate,
and full minus each module (LOMO). Every graph edge joins two arms that
differ in exactly one module, so its paired statistics attribute the change
to that one leaf. Multi-leaf differences are never used for attribution.

Golden-path rule (declared before this script was first run):
  A module is GOLDEN when, on the test split, BOTH its single-leaf addition
  to B0 AND its LOMO removal from the full candidate move required-field form
  success in its favour with exact McNemar p < 0.05 and a bootstrap 95% CI
  that excludes 0. Direction-only agreement is DIRECTIONAL. Anything else is
  NOT_SUPPORTED, or HARMFUL when both edges go against the module.

    PYTHONPATH=src python3 scripts/run_forms_arms.py --out evidence/forms_arms/run_v1
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from frontier_forms.forms.arms import MODULES, make_arm  # noqa: E402
from frontier_forms.forms.cohort import cohort_root, load_cohort, merkle_root, sha256_bytes, sha256_file  # noqa: E402
from frontier_forms.forms.harness import jsonl, output_root, run_arm, summarize  # noqa: E402
from frontier_forms.forms.server import FormState, serve  # noqa: E402
from frontier_forms.forms.templates import load_templates  # noqa: E402
from frontier_forms.statistics import admit  # noqa: E402

SHORT = {m: m.split("_")[0] for m in MODULES}


def arm_sets():
    full = frozenset(MODULES)
    sets = {frozenset()}
    sets |= {frozenset([m]) for m in MODULES}
    sets |= {frozenset(MODULES[:i]) for i in range(1, len(MODULES) + 1)}
    sets |= {full - {m} for m in MODULES}
    return sorted(sets, key=lambda s: (len(s), sorted(s)))


def paired(parent_rows, child_rows, split=None):
    base = {r["case_digest_sha256"]: r for r in parent_rows}
    recs = []
    for r in child_rows:
        if split and r["split"] != split:
            continue
        b = base[r["case_digest_sha256"]]
        recs.append({"case_digest_sha256": r["case_digest_sha256"], "task": r["template_key"],
                     "baseline_correct": b["required_fields_correct"],
                     "challenger_correct": r["required_fields_correct"]})
    return admit(recs, phase="discovery", reps=10000, seed=20261102)


def verdict(add_edge, lomo_edge):
    """add_edge: B0 -> B0+m (gain = +delta). lomo_edge: full-m -> full (gain = +delta)."""
    a, l = add_edge["test"], lomo_edge["test"]
    sig = lambda e: e["p_mcnemar_exact_two_sided"] < 0.05 and e["ci_delta_bootstrap_stratified_95"][0] > 0
    if sig(a) and sig(l):
        return "GOLDEN"
    if a["delta"] > 0 and l["delta"] > 0:
        return "DIRECTIONAL"
    if a["delta"] < 0 and l["delta"] < 0:
        return "HARMFUL"
    return "NOT_SUPPORTED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default=str(ROOT / "data/forms_cohort_v1/bundles"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    members, bundles = load_cohort(Path(args.cohort), limit=100)
    templates = load_templates()
    httpd = serve(FormState(members, bundles, templates))
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    results = {}
    try:
        for mods in arm_sets():
            name, fn = make_arm(mods)
            rows = run_arm(base, members, bundles, templates, fn, name)
            results[mods] = (name, rows)
    finally:
        httpd.shutdown()
        httpd.server_close()

    out = Path(args.out)
    (out / "predictions").mkdir(parents=True, exist_ok=True)
    nodes = []
    for mods, (name, rows) in results.items():
        data = jsonl(rows)
        (out / "predictions" / f"{name}.jsonl").write_bytes(data)
        nodes.append({"arm": name, "modules": sorted(mods), "output_root": output_root(rows),
                      "predictions_sha256": sha256_bytes(data),
                      "metrics": {k: v for k, v in summarize(rows).items() if k in ("overall", "by_split")}})

    edges = []
    for p, c in itertools.permutations(results, 2):
        if p < c and len(c - p) == 1:
            leaf = next(iter(c - p))
            edges.append({"parent": results[p][0], "child": results[c][0], "leaf": leaf,
                          "kind": "addition_to_B0" if not p else ("lomo_restore" if len(c) == len(MODULES) else "chain"),
                          "overall": paired(results[p][1], results[c][1]),
                          "test": paired(results[p][1], results[c][1], split="test")})
    edges.sort(key=lambda e: (e["kind"], e["leaf"], e["parent"]))

    full = frozenset(MODULES)
    leaves = {}
    for m in MODULES:
        add = next(e for e in edges if e["kind"] == "addition_to_B0" and e["leaf"] == m)
        lomo = next(e for e in edges if e["kind"] == "lomo_restore" and e["leaf"] == m)
        leaves[m] = {"verdict": verdict(add, lomo),
                     "add_test_delta": add["test"]["delta"], "add_test_p": add["test"]["p_mcnemar_exact_two_sided"],
                     "add_test_ci": add["test"]["ci_delta_bootstrap_stratified_95"],
                     "lomo_test_delta": lomo["test"]["delta"], "lomo_test_p": lomo["test"]["p_mcnemar_exact_two_sided"],
                     "lomo_test_ci": lomo["test"]["ci_delta_bootstrap_stratified_95"]}

    b0_freeze = json.loads((ROOT / "evidence/forms_b0/B0_FREEZE_V1.json").read_text())
    root = merkle_root(sorted(n["output_root"] for n in nodes))
    graph = {
        "graph_id": "FF-FORMS-FCG-ARMS-V1",
        "lane": "frontier-forms",
        "dataset_root": cohort_root(members),
        "b0_freeze": {"id": b0_freeze["freeze_id"], "b0_sha256": b0_freeze["arm"]["sha256"],
                      "oracle_sha256": b0_freeze["oracle"]["sha256"]},
        "arms_code_sha256": sha256_file(ROOT / "src/frontier_forms/forms/arms.py"),
        "graph_root": root,
        "endpoint": "required_fields_correct per form; paired by case_digest_sha256",
        "golden_path_rule": __doc__.split("Golden-path rule")[1].split("    PYTHONPATH")[0].strip(),
        "leaves": leaves,
        "golden_path": [m for m in MODULES if leaves[m]["verdict"] == "GOLDEN"],
        "full_candidate": results[full][0],
        "nodes": nodes,
        "edges": edges,
        "claim_ceiling": "Deterministic rule modules on synthetic data against a code oracle. Modules were designed after viewing B0 errors (all splits); results are discovery-phase and require replication on a new cohort/template set before any promotion.",
    }
    (out / "FCG_ARMS_V1.json").write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n")
    print("graph_root", root)
    for n in nodes:
        o = n["metrics"]["overall"]
        t = n["metrics"]["by_split"]["test"]
        print(f"{n['arm']:<16} all={o['full_form_success_required']:.3f} test={t['full_form_success_required']:.3f} field={o['field_accuracy']:.3f}")
    for m, v in leaves.items():
        print(m, json.dumps(v))


if __name__ == "__main__":
    main()
