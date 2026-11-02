#!/usr/bin/env python3
"""Claude red-team: independent recomputation of every historical FCO/FCG root.

Uses only redteam/merkle_independent.py (no predecessor verifier code).
Expected roots come from the external brief, not from the manifests, so a
manifest that self-declares a forged root is caught.

Usage:
  python redteam/verify_roots.py --repo . [--evidence /path/to/fireworks-antigence-eval-20261102]
         [--receipt out.json]
Without --evidence, source-byte checks are recorded NOT_TESTED (never PASS).
The receipt never contains absolute local paths, case text or gold answers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merkle_independent as M  # noqa: E402

PINNED = {
    "LN_MINI_728": "5f9a7e51f1ee03d70d34e99358fe14230efa396f7fd851df21f424e6843f61b1",
    "PREDECESSOR_15": "9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a",
    "REVIEW_66": "513cb1f8e83d0eae653c94000552fa6680b37827bcc8100af35fed3fc7d0f730",
    "REVIEW_79": "2f1cfafda7de0153fc932c52f36ce49d7ea25307b218ba392bae80b8d72c95a2",
}
SNAPSHOT = "LN-MINI-ec719d04c3707ca1cb"


def sha_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def file_sha(p: Path) -> tuple[str, int]:
    d = hashlib.sha256()
    n = 0
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 23)
            if not b:
                break
            d.update(b)
            n += len(b)
    return d.hexdigest(), n


def jsonl(text: str) -> list:
    return [json.loads(x) for x in text.splitlines() if x.strip()]


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE).stdout


def check_predecessor(repo: Path, evidence: Path | None) -> dict:
    b = repo / "evidence/freeze/predecessor"
    man = json.loads((b / "manifest.json").read_text())
    leaves = jsonl((b / "leaves.jsonl").read_text())
    root = M.root_of_records(leaves)
    paths = [x["path"] for x in leaves]
    ctx, edges = leaves[0], leaves[-1]
    out = {
        "pinned_root": PINNED["PREDECESSOR_15"],
        "recomputed_root": root,
        "root_vs_pin": "PASS" if root == PINNED["PREDECESSOR_15"] else "FAIL",
        "root_vs_manifest": "PASS" if root == man["root"] else "FAIL",
        "leaf_count": len(leaves),
        "leaf_order_vs_manifest": "PASS" if paths == man["leaf_order"] else "FAIL",
        "context_digest": "PASS" if sha_hex(M.canonical(ctx["context"])) == ctx["sha256"] else "FAIL",
        "edges_digest": "PASS" if sha_hex(M.canonical(edges["edges"])) == edges["sha256"] else "FAIL",
        "parent_root_in_context_matches_728_pin": "PASS"
        if ctx["context"].get("parent", {}).get("root") == PINNED["LN_MINI_728"] else "FAIL",
        "odd_leaf_count_duplicate_ambiguity": "PRESENT" if len(leaves) % 2 else "ABSENT",
    }
    # FCG edge referential integrity: every endpoint should be a committed leaf.
    dangling = []
    for e in edges["edges"]:
        for end in ("source", "target"):
            if e[end] not in paths:
                dangling.append({"relation": e["relation"], "end": end, "value": e[end], "status": e["status"]})
    out["fcg_edges"] = len(edges["edges"])
    out["fcg_dangling_endpoints"] = dangling
    files = []
    for x in leaves[1:-1]:
        rec = {"path": x["path"], "expected_sha256": x["sha256"]}
        if evidence is None:
            rec["status"] = "NOT_TESTED_SOURCE_UNAVAILABLE"
        else:
            p = evidence / x["path"]
            if not p.is_file():
                rec["status"] = "MISSING"
            else:
                got, size = file_sha(p)
                rec["observed_sha256"] = got
                rec["status"] = "PASS" if (got == x["sha256"] and size == x["size_bytes"]) else "FAIL"
        files.append(rec)
    out["source_files"] = files
    st = {f["status"] for f in files}
    out["source_bytes"] = "PASS" if st == {"PASS"} else ("NOT_TESTED" if evidence is None else "FAIL")
    return out


def check_728(evidence: Path | None) -> dict:
    if evidence is None:
        return {"status": "NOT_TESTED_SOURCE_UNAVAILABLE"}
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return {"status": "BLOCKED_NO_PYARROW"}
    raw_p = evidence / "datasets/longebench/mini/eval-00000-of-00001.parquet"
    snap = evidence / "custody/snapshots" / SNAPSHOT
    recipe_p = evidence / "scripts/freeze_dataset.py"
    man = json.loads((snap / "manifest.json").read_text())
    source_sha, _ = file_sha(raw_p)
    recipe_sha, _ = file_sha(recipe_p)
    version = "fco.longevity.ingest.v1"
    rows = pq.read_table(raw_p).to_pylist()
    source = {
        "fco_kind": "SourceDatasetFCO", "schema": version, "dataset": "insilicomedicine/longebench",
        "subset": "mini", "hf_revision": "0b6bab2ac5de29b0ad4fcbf062022a6b1c742e9f",
        "raw_sha256": source_sha, "row_count": len(rows),
        "source_path": "datasets/longebench/mini/eval-00000-of-00001.parquet",
        "license": "CC-BY-NC-4.0", "transform_script_sha256": recipe_sha,
    }
    sid = "fco:" + sha_hex(M.canonical(source))
    atoms = []
    assistant_in_public = 0
    for i, r in enumerate(rows):
        msgs = r["messages"]
        assert msgs[-1]["role"] == "assistant"
        permitted = msgs[:-1]
        assistant_in_public += sum(1 for m in permitted if m.get("role") == "assistant")
        cid = "case:" + sha_hex(M.canonical({"source": source_sha, "row_index": i, "lb_id": r["lb_id"]}))[:24]
        ctx = {"dataset": source_sha, "row": i, "lb_id": r["lb_id"], "pool": r["pool"],
               "domain": r["domain"], "format": r["format"], "task": r["task"]}
        atoms.append({"fco_kind": "EvaluationInputFCO", "schema": version, "case_id": cid, "context": ctx,
                      "messages": permitted, "source_fco": sid, "gold_visibility": "PROHIBITED_IN_MODEL_INPUT"})
    records = [source] + atoms
    lh = [M.leaf_hash(x) for x in records]
    root = M.root_from_leaf_hashes(lh).hex()
    disk_inputs = jsonl((snap / "inputs.jsonl").read_text())
    disk_match = sum(1 for a, d in zip(atoms, disk_inputs) if a == d["input"])
    proofs = jsonl((snap / "proofs.jsonl").read_text())
    ok = 0
    for i, pr in enumerate(proofs):
        idx = pr["index_in_tree"]
        if (idx == i + 1 and pr["leaf_hash"] == lh[idx].hex()
                and M.verify_inclusion(pr["leaf_hash"], pr["siblings"], PINNED["LN_MINI_728"])):
            ok += 1
    # Gold-answer leakage scan of the public files: oracle answers must not be
    # present as an assistant turn or as an "answer" key.
    pub_text = (snap / "inputs.jsonl").read_text() + (snap / "fcg_edges.jsonl").read_text() + (snap / "proofs.jsonl").read_text()
    leak_keys = sum(pub_text.count(k) for k in ('"answer":', '"oracle_metadata"', '"role":"assistant"'))
    snapshot_id = "LN-MINI-" + sha_hex(M.canonical({"source": source_sha, "recipe": recipe_sha, "version": version}))[:18]
    return {
        "rows": len(rows), "leaves": len(records),
        "pinned_root": PINNED["LN_MINI_728"], "recomputed_root": root,
        "root_vs_pin": "PASS" if root == PINNED["LN_MINI_728"] else "FAIL",
        "root_vs_manifest": "PASS" if root == man["public_merkle_root"] else "FAIL",
        "source_sha256": source_sha,
        "source_sha_vs_manifest": "PASS" if source_sha == man["source_sha256"] else "FAIL",
        "recipe_sha_vs_manifest": "PASS" if recipe_sha == man["recipe_sha256"] else "FAIL",
        "snapshot_id_rederived": "PASS" if snapshot_id == SNAPSHOT else f"FAIL:{snapshot_id}",
        "source_fco_id_vs_manifest": "PASS" if sid == man["source_fco_id"] else "FAIL",
        "input_records_identical_to_disk": f"{disk_match}/{len(atoms)}",
        "inclusion_proofs_verified_against_pin": f"{ok}/{len(proofs)}",
        "assistant_turns_in_public_inputs": assistant_in_public,
        "oracle_marker_strings_in_public_files": leak_keys,
        "odd_leaf_count_duplicate_ambiguity": "PRESENT" if len(records) % 2 else "ABSENT",
    }


def introducing_commit(repo: Path, rel: str) -> str:
    out = git(repo, "log", "--diff-filter=A", "--format=%H", "--", rel).decode().split()
    return out[-1]


def check_reviews(repo: Path) -> list[dict]:
    res = []
    roots = {}
    base = repo / "evidence/freeze/review_successor"
    for folder in sorted(base.glob("REVIEW-*")):
        man = json.loads((folder / "manifest.json").read_text())
        leaves = jsonl((folder / "leaves.jsonl").read_text())
        rel_m = str((folder / "manifest.json").relative_to(repo))
        commit = introducing_commit(repo, rel_m)
        bad = []
        for x in leaves:
            try:
                raw = git(repo, "show", f"{commit}:{x['path']}")
            except subprocess.CalledProcessError:
                bad.append({"path": x["path"], "status": "MISSING_AT_COMMIT"})
                continue
            if sha_hex(raw) != x["sha256"] or len(raw) != x["size_bytes"]:
                bad.append({"path": x["path"], "status": "BYTES_MISMATCH_AT_COMMIT"})
        root = M.root_of_records(leaves)
        roots[root] = folder.name
        paths = [x["path"] for x in leaves]
        # Is the parent pointer committed by this root? Only if some leaf's bytes contain it.
        parent = man.get("parent_project_root")
        bound = False
        for x in leaves:
            try:
                if parent and parent.encode() in git(repo, "show", f"{commit}:{x['path']}"):
                    bound = True
                    break
            except subprocess.CalledProcessError:
                pass
        res.append({
            "bundle": folder.name, "leaf_count": len(leaves), "recomputed_root": root,
            "root_vs_manifest": "PASS" if root == man["root"] else "FAIL",
            "leaf_order_vs_manifest": "PASS" if paths == man["leaf_order"] else "FAIL",
            "introducing_commit": commit,
            "leaf_bytes_at_introducing_commit": "PASS" if not bad else "FAIL",
            "leaf_byte_failures": bad,
            "declared_parent_root": parent, "declared_parent_commit": man.get("parent_repo_commit"),
            "parent_root_string_in_committed_leaf": "YES" if bound else "NO_MANIFEST_FIELD_ONLY",
            "parent_pointer_field_itself_hashed": "NO" if "manifest.json" not in [p.rsplit("/",1)[-1] for p in paths if p.startswith(rel_m.rsplit("/",1)[0])] else "YES",
        })
    known = set(roots) | {PINNED["PREDECESSOR_15"]}
    for r in res:
        r["declared_parent_exists"] = "PASS" if r["declared_parent_root"] in known else "FAIL"
        for k, v in PINNED.items():
            if r["recomputed_root"] == v:
                r["matches_pin"] = k
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--evidence", type=Path)
    ap.add_argument("--receipt", type=Path)
    a = ap.parse_args()
    repo = a.repo.resolve()
    head = git(repo, "rev-parse", "HEAD").decode().strip()
    receipt = {
        "schema": "claude.redteam.root_replay.v1",
        "repo_head": head,
        "verifier_sha256": file_sha(Path(__file__).resolve())[0],
        "merkle_impl_sha256": file_sha(Path(M.__file__).resolve())[0],
        "evidence_source": "PROVIDED" if a.evidence else "NOT_PROVIDED",
        "predecessor_15": check_predecessor(repo, a.evidence),
        "ln_mini_728": check_728(a.evidence),
        "review_successors": check_reviews(repo),
        "meaning": "INTEGRITY_ONLY_NOT_CAUSALITY",
        "signature": "NOT_SIGNED",
    }
    pins = {k: False for k in PINNED}
    if receipt["predecessor_15"]["root_vs_pin"] == "PASS":
        pins["PREDECESSOR_15"] = True
    if receipt["ln_mini_728"].get("root_vs_pin") == "PASS":
        pins["LN_MINI_728"] = True
    for r in receipt["review_successors"]:
        if r.get("matches_pin") in pins:
            pins[r["matches_pin"]] = True
    receipt["pins_reproduced"] = pins
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if a.receipt:
        a.receipt.parent.mkdir(parents=True, exist_ok=True)
        a.receipt.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
