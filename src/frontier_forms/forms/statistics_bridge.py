"""Pair an arm's case rows with frozen B0 rows and run the repo's admission statistics.

Primary endpoint (predeclared): per-form success on all required fields.
Pairs are matched by case_digest_sha256; any unmatched or duplicate case is an
error, never silently dropped. Statistics: exact two-sided McNemar and a
paired bootstrap stratified by template (src/frontier_forms/statistics.py).
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
                    "split": r["split"],
                    "baseline_correct": b["required_fields_correct"],
                    "challenger_correct": r["required_fields_correct"]})
    if len(out) != len(base):
        raise ValueError("ARM_MISSING_CASES")
    return out


def paired_vs_b0(b0_rows, arm_rows, reps=10000, seed=20261102):
    pairs = _pairs(b0_rows, arm_rows)
    res = {"endpoint": "required_fields_correct per form", "overall": admit(pairs, phase="discovery", reps=reps, seed=seed)}
    test = [p for p in pairs if p["split"] == "test"]
    if test:
        res["test_split"] = admit(test, phase="discovery", reps=reps, seed=seed)
    return res
