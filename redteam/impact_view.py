#!/usr/bin/env python3
"""FCG impact view over the append-only custody chain.

For each successor: earliest changed leaf (by leaf order), added/removed/modified
paths, and the downstream dependents reachable through DECLARED FCG edges.
Also simulates arm 10 (changed source version with predecessor retained):
a new LongevityBench revision changes leaf 1 of the 15-leaf project tree; the
predecessor bundle is untouched and a successor root is computed in memory only.
"""
from __future__ import annotations

import copy
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merkle_independent as M  # noqa: E402


def load(d: Path):
    m = json.loads((d / "manifest.json").read_text())
    rows = [json.loads(x) for x in (d / "leaves.jsonl").read_text().splitlines() if x.strip()]
    return m, rows


def diff(a, b):
    pa = {r["path"]: r.get("sha256") for r in a}
    pb = {r["path"]: r.get("sha256") for r in b}
    order = [r["path"] for r in b]
    added = [p for p in order if p not in pa]
    removed = [p for p in pa if p not in pb]
    modified = [p for p in order if p in pa and pa[p] != pb[p]]
    earliest = next((i for i, (x, y) in enumerate(zip([r["path"] for r in a], order)) if x != y or pa.get(y) != pb[y]), None)
    if earliest is None and len(a) != len(b):
        earliest = min(len(a), len(b))
    return {"earliest_changed_index": earliest, "earliest_changed_path": order[earliest] if earliest is not None and earliest < len(order) else None,
            "added": added, "removed": removed, "modified": modified}


def downstream(edges, start):
    g = defaultdict(list)
    for e in edges:
        g[e["source"]].append((e["relation"], e["target"]))
    seen, q, out = {start}, deque([start]), []
    while q:
        n = q.popleft()
        for rel, t in g[n]:
            out.append({"from": n, "relation": rel, "to": t})
            if t not in seen:
                seen.add(t)
                q.append(t)
    return out


def main() -> int:
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    _, pred = load(repo / "evidence/freeze/predecessor")
    edges = pred[-1]["edges"]
    chain = []
    rs = {}
    for d in sorted((repo / "evidence/freeze/review_successor").glob("REVIEW-*")):
        m, rows = load(d)
        rs[m["root"]] = (m, rows)
    # order by parent links starting from the 15-leaf predecessor root
    cur_root, cur_rows = "9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a", pred
    while True:
        nxt = next(((r, v) for r, v in rs.items() if v[0].get("parent_project_root") == cur_root), None)
        if not nxt:
            break
        root, (m, rows) = nxt
        d = diff(cur_rows, rows)
        chain.append({"parent": cur_root, "child": root, "parent_leaves": len(cur_rows), "child_leaves": len(rows),
                      "comparable": "NO_DIFFERENT_LEAF_SCHEMA" if cur_rows is pred else "YES",
                      **({k: (len(v) if isinstance(v, list) else v) for k, v in d.items()} if cur_rows is not pred else {}),
                      **({"modified_paths": d["modified"], "added_paths": d["added"], "removed_paths": d["removed"]} if cur_rows is not pred else {})})
        cur_root, cur_rows = root, rows
    # arm 10: simulated source revision change, predecessor retained
    succ = copy.deepcopy(pred)
    succ[1]["sha256"] = "SIMULATED_NEW_REVISION_" + "0" * 41
    succ_root = M.root_of_records(succ)
    leaf_paths = {r["path"] for r in pred}
    declared_dependents = downstream(edges, succ[1]["path"])
    undeclared = [p for p in ["eval/lb_mini_discovery_lfm2-1.2b-longevity-q4km_latest.jsonl",
                              "eval/insilico_qwen3_06b_discovery_attempt3.jsonl",
                              "eval/paired_discovery_mcnemar_bootstrap.json",
                              "eval/longebench_split_manifest.json"] if p in leaf_paths
                  and p not in {x["to"] for x in declared_dependents}]
    out = {
        "schema": "claude.redteam.fcg_impact_view.v1",
        "chain": chain,
        "arm10_changed_source_version": {
            "predecessor_root_retained": M.root_of_records(pred),
            "simulated_successor_root": succ_root,
            "successor_root_status": "SIMULATED_IN_MEMORY_NOT_A_FREEZE",
            "earliest_changed_leaf": {"index": 1, "path": succ[1]["path"]},
            "declared_downstream_via_fcg_edges": declared_dependents,
            "outputs_that_depend_on_source_but_have_no_declared_edge": undeclared,
            "finding": "impact view under-reports: discovery outputs, split manifest and statistics consume the parquet "
                       "but FCG_EDGES declares only parquet->snapshot manifest; a source revision would not be "
                       "propagated to them by graph traversal",
        },
        "dangling_edge_targets": sorted({e["target"] for e in edges if e["target"] not in leaf_paths}),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
