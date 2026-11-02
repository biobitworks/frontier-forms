#!/usr/bin/env python3
"""Independently rebuild the LongevityBench-mini split and FCO context for each case.

Reads ONLY the source parquet (sha-checked) and the public split manifest.
Rebuilds the 729-leaf FCO tree from the documented recipe so that each case can
carry its own leaf hash + inclusion proof as "FCG context" for the ablation arms.

Writes a PRIVATE cases file (contains prompts and gold) outside the repository.
Prints a public summary (counts, hashes) only.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merkle_independent as M  # noqa: E402

REV = "0b6bab2ac5de29b0ad4fcbf062022a6b1c742e9f"
SOURCE_SHA = "544e0bf2975b04cf1d2be6654b4baccbe04db3cf4f167d80c81e25a9fc3fe72c"
RECIPE_SHA = "53de0a80f8c80a93648d2f1c367bcc0aa7ca10c55321e4be4365b06e82db0c20"  # from LN-MINI manifest
ROOT_728 = "5f9a7e51f1ee03d70d34e99358fe14230efa396f7fd851df21f424e6843f61b1"
TASKS = ("LB-0307", "LB-0309", "LB-0314", "LB-0315")
VERSION = "fco.longevity.ingest.v1"


def sha_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", type=Path, required=True)
    ap.add_argument("--split-manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="private JSONL, must be outside the repo")
    a = ap.parse_args()
    import pyarrow.parquet as pq

    raw = a.parquet.read_bytes()
    src_sha = sha_hex(raw)
    if src_sha != SOURCE_SHA:
        print(json.dumps({"status": "FAIL_SOURCE_SHA", "observed": src_sha}))
        return 2
    rows = pq.read_table(a.parquet).to_pylist()
    split = json.loads(a.split_manifest.read_text())["task_partitions"]
    source = {"fco_kind": "SourceDatasetFCO", "schema": VERSION, "dataset": "insilicomedicine/longebench",
              "subset": "mini", "hf_revision": REV, "raw_sha256": src_sha, "row_count": len(rows),
              "source_path": "datasets/longebench/mini/eval-00000-of-00001.parquet",
              "license": "CC-BY-NC-4.0", "transform_script_sha256": RECIPE_SHA}
    sid = "fco:" + sha_hex(M.canonical(source))
    atoms = []
    for i, r in enumerate(rows):
        cid = "case:" + sha_hex(M.canonical({"source": src_sha, "row_index": i, "lb_id": r["lb_id"]}))[:24]
        ctx = {"dataset": src_sha, "row": i, "lb_id": r["lb_id"], "pool": r["pool"],
               "domain": r["domain"], "format": r["format"], "task": r["task"]}
        atoms.append({"fco_kind": "EvaluationInputFCO", "schema": VERSION, "case_id": cid, "context": ctx,
                      "messages": r["messages"][:-1], "source_fco": sid,
                      "gold_visibility": "PROHIBITED_IN_MODEL_INPUT"})
    lh = [M.leaf_hash(x) for x in [source] + atoms]
    root = M.root_from_leaf_hashes(lh).hex()

    key_to_part = {}
    for t, parts in split.items():
        for p, keys in parts.items():
            for k in keys:
                if k in key_to_part:
                    key_to_part[k] = ("DUPLICATE_KEY", t)
                else:
                    key_to_part[k] = (p, t)
    seen = collections.Counter()
    prompts_by_key = collections.defaultdict(set)
    out_rows = []
    for i, r in enumerate(rows):
        if r["lb_id"] not in TASKS:
            continue
        prompt = r["messages"][-2]["content"]
        gold = r["messages"][-1]["content"].strip()
        key = sha_hex(M.canonical([REV, r["lb_id"], prompt]))
        prompts_by_key[key].add(i)
        part = key_to_part.get(key, ("UNASSIGNED", r["lb_id"]))[0]
        seen[part] += 1
        if part not in ("discovery", "heldout"):
            continue
        opt_line = next((ln for ln in prompt.splitlines() if ln.strip().startswith("Options:")), "")
        options = sorted(set(re.findall(r"\b([A-E])\.", opt_line)))
        proof = M.inclusion_proof(lh, i + 1)
        assert M.verify_inclusion(lh[i + 1].hex(), proof, root)
        out_rows.append({
            "row_key_sha256": key, "partition": part, "task": r["lb_id"], "format": r["format"],
            "domain": r["domain"], "gold": gold, "options": options, "messages": r["messages"][:-1],
            "fco": {"case_id": atoms[i]["case_id"], "input_fco_id": "fco:" + sha_hex(M.canonical(atoms[i])),
                    "source_fco_id": sid, "leaf_index": i + 1, "leaf_hash": lh[i + 1].hex(),
                    "proof": proof, "snapshot_root": root,
                    "edge": {"src": sid, "rel": "DERIVED_INPUT_AT", "dst": "fco:" + sha_hex(M.canonical(atoms[i]))}},
        })
    out_rows.sort(key=lambda x: (x["partition"], x["task"], x["row_key_sha256"]))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x") as f:  # create-only: never overwrite a frozen case file
        for x in out_rows:
            f.write(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n")
    dup_prompts = sum(1 for v in prompts_by_key.values() if len(v) > 1)
    disc = [x["row_key_sha256"] for x in out_rows if x["partition"] == "discovery"]
    held = [x["row_key_sha256"] for x in out_rows if x["partition"] == "heldout"]
    print(json.dumps({
        "status": "PASS", "source_sha256": src_sha, "rows": len(rows),
        "rebuilt_root": root, "root_vs_pin": "PASS" if root == ROOT_728 else "FAIL",
        "partition_counts_rebuilt": dict(seen), "discovery": len(disc), "heldout": len(held),
        "discovery_heldout_overlap": len(set(disc) & set(held)),
        "duplicate_prompt_keys": dup_prompts,
        "options_parsed_all": all(len(x["options"]) >= 2 for x in out_rows),
        "gold_in_options_all": all(x["gold"] in x["options"] for x in out_rows),
        "discovery_case_set_sha256": sha_hex("\n".join(sorted(disc)).encode()),
        "heldout_case_set_sha256": sha_hex("\n".join(sorted(held)).encode()),
        "private_cases_sha256": sha_hex(a.out.read_bytes()),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
