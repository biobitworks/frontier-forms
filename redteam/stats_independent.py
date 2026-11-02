#!/usr/bin/env python3
"""Independent paired statistics (no predecessor code): exact McNemar, stratified
paired bootstrap, Holm correction, one-vs-rest classification rates."""
from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Sequence


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact binomial test on discordant counts b (base-only) and c (challenger-only)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def contingency(base: Sequence[bool], chal: Sequence[bool]) -> dict:
    assert len(base) == len(chal)
    t = {"both_correct": 0, "base_only": 0, "chal_only": 0, "both_wrong": 0}
    for x, y in zip(base, chal):
        t["both_correct" if x and y else "base_only" if x else "chal_only" if y else "both_wrong"] += 1
    return t


def stratified_bootstrap(base: Sequence[bool], chal: Sequence[bool], strata: Sequence[str],
                         reps: int = 10000, seed: int = 20261102) -> dict:
    groups = defaultdict(list)
    for i, s in enumerate(strata):
        groups[s].append(i)
    rng = random.Random(seed)
    n = len(base)
    diffs = []
    keys = sorted(groups)
    for _ in range(reps):
        d = 0
        for k in keys:
            idx = groups[k]
            for _j in range(len(idx)):
                i = idx[rng.randrange(len(idx))]
                d += int(chal[i]) - int(base[i])
        diffs.append(d / n)
    diffs.sort()
    lo = diffs[int(0.025 * reps)]
    hi = diffs[int(0.975 * reps) - 1]
    return {"reps": reps, "seed": seed, "method": "paired, resample within task strata, percentile",
            "ci95": [lo, hi], "mean": sum(diffs) / reps}


def holm(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for rank, (k, p) in enumerate(items):
        adj = min(1.0, (m - rank) * p)
        running = max(running, adj)
        out[k] = running
    return out


def one_vs_rest(gold: Sequence[str], pred: Sequence[str | None]) -> dict:
    labels = sorted(set(gold))
    per = {}
    for L in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == L and p == L)
        fp = sum(1 for g, p in zip(gold, pred) if g != L and p == L)
        fn = sum(1 for g, p in zip(gold, pred) if g == L and p != L)
        tn = sum(1 for g, p in zip(gold, pred) if g != L and p != L)

        def r(a, b):
            return a / b if b else None
        prec, rec = r(tp, tp + fp), r(tp, tp + fn)
        f1 = (2 * prec * rec / (prec + rec)) if prec and rec else (0.0 if prec is not None and rec is not None else None)
        per[L] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": prec, "recall": rec, "f1": f1,
                  "fpr": r(fp, fp + tn), "fnr": r(fn, fn + tp), "fdr": r(fp, fp + tp)}

    def macro(key):
        v = [x[key] for x in per.values() if x[key] is not None]
        return sum(v) / len(v) if v else None
    return {"per_label": per, "macro": {k: macro(k) for k in ("precision", "recall", "f1", "fpr", "fnr", "fdr")},
            "zero_denominator_labels": sorted(L for L, x in per.items() if x["precision"] is None)}
