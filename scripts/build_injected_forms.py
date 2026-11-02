#!/usr/bin/env python3
"""Build the prebuilt error-injected forms and write the preregistration.

    PYTHONPATH=src python3 scripts/build_injected_forms.py
Writes data/forms_injected_v1/{forms.jsonl,truth.jsonl,PREREG.json}.
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frontier_forms.forms import inject  # noqa: E402
from frontier_forms.forms.cohort import cohort_root, load_cohort, sha256_bytes, sha256_file  # noqa: E402
from frontier_forms.forms.templates import load_templates  # noqa: E402

OUT = ROOT / "data/forms_injected_v1"
members, bundles = load_cohort(ROOT / "data/forms_cohort_v1/bundles")
forms, truth = inject.build(members, bundles, load_templates())
OUT.mkdir(parents=True, exist_ok=True)
fb, tb = inject.jsonl(forms), inject.jsonl(truth)
(OUT / "forms.jsonl").write_bytes(fb)
(OUT / "truth.jsonl").write_bytes(tb)
per_form = collections.Counter(collections.Counter(t["form_id"] for t in truth).get(f["form_id"], 0) for f in forms)
prereg = {
    "prereg_id": "FF-DETECTOR-PREREG-V1",
    "date": "2026-11-02",
    "lane": "frontier-forms",
    "written_before": "any detector code exists in the repo; detectors are committed in a later commit",
    "injection": {"version": inject.INJECTION_VERSION, "seed": inject.SEED,
                  "variants_per_case": inject.VARIANTS_PER_CASE, "n_errors_weights": inject.N_ERRORS_WEIGHTS,
                  "error_types": inject.ERROR_TYPES, "code_sha256": sha256_file(ROOT / "src/frontier_forms/forms/inject.py")},
    "dataset": {"cohort_root": cohort_root(members), "forms_sha256": sha256_bytes(fb), "truth_sha256": sha256_bytes(tb),
                "n_forms": len(forms), "n_error_instances": len(truth),
                "errors_per_form": dict(sorted(per_form.items())),
                "error_type_counts": dict(sorted(collections.Counter(t["error_type"] for t in truth).items()))},
    "mechanisms": {
        "M1_merkle_breakpoint": "Recompute every field leaf sha256(form_id|field_key|value) and the form Merkle root; a field is flagged when its leaf differs from the sealed leaf (the breakpoint). Sees only the form and its seal.",
        "M2_lean4_constraints": "Lean 4 (v4.15.0) program lean/FormChecks.lean evaluates declared per-field constraints (identity text fields required and well formed; ISO date not after 2026-11-01; phone NNN-NNN-NNNN; 5-digit ZIP; 2-letter state; select value in options; height_cm 30-250, weight_kg 0.5-350, weight_lb 1-800; blood pressure S/D integers with 40<=D<S<=300). Counts only if lean compiles the file, including its proof examples.",
        "M3_fco_source_binding": "Recompute each field from the teammate passport served by the local server, using the full candidate mapping (B0+L1+L2+L3); flag when the form value disagrees (lists as sets, numbers within 0.05, blanks compared)."},
    "combinations": "all 8 subsets of {M1,M2,M3}; the empty set detects nothing",
    "endpoints": {
        "primary": "error-instance recall: an instance is detected when any of its fields is flagged",
        "secondary": ["per-error-type recall", "false-positive rate on fields not touched by injection",
                      "form-level sensitivity and specificity (form has >=1 error)",
                      "field-level AUROC of the count of mechanisms flagging (full set)"]},
    "statistics": {
        "single_leaf_edges": "S -> S+{m} for every S not containing m; LOMO = {M1,M2,M3}-{m} -> full",
        "test": "exact two-sided McNemar on paired error instances; paired bootstrap 10000 reps, seed 20261102, stratified by error type",
        "alpha": 0.05,
        "attribution": "a gain is attributed to mechanism m only on single-leaf edges; multi-leaf differences are reported as CONFOUNDED",
        "fp_cost": "the same paired test is applied to clean fields to report the false-positive cost of each edge"},
    "claim_ceiling": "Synthetic injected errors on synthetic patients. Detection rates describe these declared error types only."
}
(OUT / "PREREG.json").write_text(json.dumps(prereg, indent=2, sort_keys=True) + "\n")
print(json.dumps(prereg["dataset"], indent=1))
