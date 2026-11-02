"""Pair an arm's case rows with frozen B0 rows and run the repo's admission statistics.

Primary endpoint (predeclared): per-form success on all required fields.
Pairs are matched by case_digest_sha256; any unmatched or duplicate case is an
error, never silently dropped. Statistics: exact two-sided McNemar and a
paired bootstrap stratified by template (src/frontier_forms/statistics.py),
plus a patient-cluster paired bootstrap (patients resampled, forms kept together).
"""
from __future__ import annotations

from frontier_forms.statistics import admit


def _pairs(b0_rows, arm_rows):
    base = {r["case_digest_sha256"]: r for r in b0_rows}
    if len(base) != len(b0_rows):
        raise ValueError("DUPLICATE_B0_CASE")
    out = []
    for r in arm_rows:
        b = base.get(r["case_digest_sha256"])
        if b is None:
            raise ValueError(f"UNPAIRED_CASE:{r['case_key']}")
        out.append({"case_digest_sha256": r["case_digest_sha256"], "task": r["template_key"],
                    "patient_id": r["patient_id"],
                    "split": r["split"],
                    "baseline_correct": b["required_fields_correct"],
                    "challenger_correct": r["required_fields_correct"]})
    if len(out) != len(base):
        raise ValueError("ARM_MISSING_CASES")
    return out


def patient_cluster_bootstrap(pairs, reps=10000, seed=20261102, alpha=0.05):
    """Paired bootstrap that resamples PATIENTS (all of a patient's forms move together).

    Forms from one patient share a passport, so they are not independent; this CI is
    the conservative companion to the template-stratified one.
    """
    import random
    by_p = {}
    for p in pairs:
        d = int(bool(p["challenger_correct"])) - int(bool(p["baseline_correct"]))
        by_p.setdefault(p["patient_id"], []).append(d)
    pids = sorted(by_p)
    sums = [sum(by_p[k]) for k in pids]
    counts = [len(by_p[k]) for k in pids]
    rng = random.Random(seed)
    deltas = []
    for _ in range(reps):
        idx = [rng.randrange(len(pids)) for _ in pids]
        deltas.append(sum(sums[i] for i in idx) / sum(counts[i] for i in idx))
    deltas.sort()
    lo, hi = deltas[int(alpha / 2 * reps)], deltas[int((1 - alpha / 2) * reps) - 1]
    return {"ci_delta_patient_cluster_95": [lo, hi], "patients": len(pids), "reps": reps, "seed": seed,
            "positive_gate": lo > 0}


def paired_vs_b0(b0_rows, arm_rows, reps=10000, seed=20261102):
    pairs = _pairs(b0_rows, arm_rows)
    res = {"endpoint": "required_fields_correct per form", "overall": admit(pairs, phase="discovery", reps=reps, seed=seed)}
    res["overall"]["patient_cluster_bootstrap"] = patient_cluster_bootstrap(pairs, reps=reps, seed=seed)
    test = [p for p in pairs if p["split"] == "test"]
    if test:
        res["test_split"] = admit(test, phase="discovery", reps=reps, seed=seed)
        res["test_split"]["patient_cluster_bootstrap"] = patient_cluster_bootstrap(test, reps=reps, seed=seed)
    return res
