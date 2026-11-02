#!/usr/bin/env python3
"""frontier-forms lane: dataset-freeze red team on fully synthetic inputs.

Builds a synthetic dataset, a synthetic freeze manifest over three synthetic files, then runs
data attacks, manifest attacks, fork/rollback, admission-gate and immutability challenges.
Every input is generated here; no private or restricted data is read.  Deterministic output
(except the immutability probe, which tests the local filesystem it runs on).

    python3 tools/public_redteam.py --out results/
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixture_attacks as fa  # noqa: E402
import freezelib as fl  # noqa: E402

VERSION = "SYNTHETIC_FREEZE_V1"


def build_synthetic_freeze(store: Path) -> dict:
    fx = fa.make_fixture()
    raw = fa.serialize(fx)
    files = {
        "F001__synthetic_pseudobulk.bin": raw,
        "F002__prereg.json": fl.canonical({"primary": "arm_vs_ref_relative_val_mse_gain>=0.01", "seed": 20261102,
                                           "arms": ["REF", "ARM"], "synthetic": True}),
        "F003__declared_split.json": fl.canonical(fa.incumbent_expected(raw)),
    }
    atoms = []
    for name, data in files.items():
        p = store / name
        p.write_bytes(data)
        src = "synthetic:" + name.split("__", 1)[1]
        origin = "generated:public_redteam.py#" + name
        h = fl.sha256_hex(data)
        atoms.append({"atom_id": name.split("__")[0], "atom_class": "SYNTHETIC", "source_id": src, "origin_ref": origin,
                      "content_sha256": h, "content_bytes": len(data), "occurrence_id": fl.occurrence_id(src, h, origin),
                      "transform_id": "IDENTITY_COPY_V1", "output_sha256": fl.sha256_hex(p.read_bytes()),
                      "partition_id": "SYNTHETIC", "dataset_version": VERSION, "consuming_run": "NONE",
                      "custody_state": "STORED_READBACK_VERIFIED", "rights_assertion_id": "RA-SYNTHETIC",
                      "reported_sha256": "NONE", "reported_by": "NONE", "derived_from": "NONE", "destination_path": name})
    src = "remote:not-downloaded.bin"
    atoms.append({"atom_id": "X001", "atom_class": "SOURCE_DATA", "source_id": src, "origin_ref": "NOT_READ",
                  "content_sha256": "UNKNOWN", "content_bytes": -1, "occurrence_id": fl.occurrence_id(src, "UNKNOWN", "NOT_READ"),
                  "transform_id": "NONE", "output_sha256": "NOT_STORED", "partition_id": "SOURCE", "dataset_version": VERSION,
                  "consuming_run": "NONE", "custody_state": "NOT_STORED", "rights_assertion_id": "RA-UNKNOWN",
                  "reported_sha256": "ab" * 32, "reported_by": "a remote receipt (citation only)", "derived_from": "NONE",
                  "destination_path": "NONE"})
    atoms.sort(key=lambda a: a["atom_id"])
    for a in atoms:
        a["leaf_sha256"] = fl.leaf_hash(fl.build_leaf(a))
    leaves = [a["leaf_sha256"] for a in atoms]
    root = fl.merkle_root(leaves)
    for i, a in enumerate(atoms):
        a["leaf_index"], a["inclusion_proof"] = i, fl.inclusion_proof(leaves, i)
    return {"schema": fl.FREEZE_SCHEMA, "dataset_version": VERSION, "atoms": atoms,
            "merkle": {"leaf_count": len(leaves), "root": root, "project_mmr": "NOT_COMMITTED", "signature": "NOT_SIGNED"}}


def run(out: Path) -> dict:
    results = []

    def add(**kw):
        kw.setdefault("baseline_hashchain", "N/A")
        kw["evidence_leaf"] = fl.leaf_hash({"schema": "frontier-forms.freeze_redteam.leaf", **kw})
        results.append(kw)

    fx = fa.make_fixture()
    base = fa.serialize(fx)
    inc_exp, v2_exp, base_sha = fa.incumbent_expected(base), fa.v2_expected(base), fl.sha256_hex(base)
    add(attack_id="RT00", attack="Control: unmodified fixture", layer="CONTROL", expected="ACCEPT",
        incumbent="ACCEPT" if fa.incumbent_check(base, inc_exp)[0] else "REJECT",
        successor="ACCEPT" if fa.v2_check(base, v2_exp)[0] else "REJECT", baseline_hashchain="ACCEPT")
    for aid, kind, desc, layer in fa.DATA_ATTACKS:
        raw = fa.serialize(fa.mutate(fx, kind))
        oi, wi = fa.incumbent_check(raw, inc_exp)
        ov, wv = fa.v2_check(raw, v2_exp)
        add(attack_id=aid, attack=desc, layer=layer, expected="REJECT",
            incumbent="ACCEPT (undetected)" if oi else "REJECT:" + wi,
            successor="ACCEPT (undetected)" if ov else "REJECT:" + wv,
            baseline_hashchain="ACCEPT (undetected)" if fl.sha256_hex(raw) == base_sha else "REJECT")
    lk = fa.leakage_report(base)
    add(attack_id="RT10", attack="Target identity shared across batch-level partitions", layer="SPLIT_ISOLATION",
        expected="no overlap if an unseen-perturbation claim is made",
        incumbent=f"overlap {lk['target_overlap_train_held']}/{lk['held_targets']} targets, unguarded", successor="reported, not fixed")

    with tempfile.TemporaryDirectory() as td:
        store = Path(td)
        m = build_synthetic_freeze(store)
        rb = lambda a: (store / a["destination_path"]).read_bytes() if (store / a["destination_path"]).is_file() else None  # noqa: E731

        def tv(mm, reader=rb):
            try:
                fl.verify_manifest(mm, reader)
                return "ACCEPT"
            except fl.FreezeError as e:
                return "REJECT:" + str(e).split(":")[0]

        add(attack_id="MK00", attack="Control: unmodified synthetic manifest", layer="MERKLE", expected="ACCEPT", incumbent=tv(m), successor="same")
        t = m["atoms"][0]
        orig = (store / t["destination_path"]).read_bytes()
        flip = bytearray(orig); flip[len(flip) // 2] ^= 1
        sub = lambda new: (lambda a: new if a["atom_id"] == t["atom_id"] else rb(a))  # noqa: E731
        cases = [("MK01", "Stored byte flip, metadata unchanged", tv(m, sub(bytes(flip)))),
                 ("MK02", "Bytes changed between manifest and consumption", tv(m, sub(orig + b" ")))]
        x = copy.deepcopy(m); x["atoms"][1]["content_sha256"] = x["atoms"][1]["output_sha256"] = fl.sha256_hex(b"forged")
        cases.append(("MK03", "Leaf substitution, leaf not recomputed", tv(x)))
        x = copy.deepcopy(m); del x["atoms"][1]
        cases.append(("MK05", "Missing leaf", tv(x)))
        x = copy.deepcopy(m); x["atoms"][0], x["atoms"][1] = x["atoms"][1], x["atoms"][0]
        cases.append(("MK06", "Reordered leaves", tv(x)))
        x = copy.deepcopy(m); x["atoms"][2]["occurrence_id"] = x["atoms"][1]["occurrence_id"]
        cases.append(("MK07", "Reused occurrence id", tv(x)))
        x = copy.deepcopy(m); x["atoms"].append(copy.deepcopy(x["atoms"][0]))
        cases.append(("MK08", "Duplicate atom", tv(x)))
        x = copy.deepcopy(m); x["merkle"]["root"] = "0" * 64
        cases.append(("MK09", "False SUCCESS: root not matching leaves", tv(x)))
        x = copy.deepcopy(m); ns = x["atoms"][-1]; ns["output_sha256"] = ns["reported_sha256"]
        cases.append(("MK10", "Reported remote checksum promoted to local custody", tv(x)))
        for aid, desc, obs in cases:
            add(attack_id=aid, attack=desc, layer="MERKLE", expected="REJECT", incumbent=obs, successor="same")

        def reroot(mm):
            for a in mm["atoms"]:
                a["leaf_sha256"] = fl.leaf_hash(fl.build_leaf(a))
            lv = [a["leaf_sha256"] for a in mm["atoms"]]
            mm["merkle"]["leaf_count"], mm["merkle"]["root"] = len(lv), fl.merkle_root(lv)
            return mm
        fork = copy.deepcopy(m); fork["atoms"][-1]["reported_by"] = "forked"; fork = reroot(fork)
        prefix = copy.deepcopy(m); prefix["atoms"] = prefix["atoms"][:2]; prefix = reroot(prefix)
        for aid, desc, mm in (("MK12", "Forked history, self-consistent", fork), ("MK13", "Rollback to older valid prefix", prefix)):
            add(attack_id=aid, attack=desc, layer="MERKLE", expected="REJECT", incumbent="unpinned: " + tv(mm),
                successor="pinned root: " + ("REJECT" if mm["merkle"]["root"] != m["merkle"]["root"] else "ACCEPT"),
                baseline_hashchain="undetected without an external anchor")

        p = store / "probe.bin"; p.write_bytes(b"original"); os.chmod(p, 0o444)
        try:
            with open(p, "wb") as fh:
                fh.write(b"x")
            ow = "overwrite SUCCEEDED"
        except PermissionError:
            ow = "overwrite refused"
        os.chmod(p, 0o644)
        add(attack_id="IM01", attack="Overwrite a 0444 file in the store (this machine's filesystem)", layer="CUSTODY",
            expected="REJECT", incumbent=ow + (" (running as root)" if hasattr(os, "geteuid") and os.geteuid() == 0 else ""),
            successor="immutability must rest on a pinned root, not file modes")
        synthetic_root = m["merkle"]["root"]

    def gate(ledger):
        seen = set()
        for r in ledger:
            if r["action"] == "ADMIT":
                if r["id"] in seen:
                    return "REJECT:DUPLICATE_ADMISSION"
                seen.add(r["id"])
            if r.get("independent") and r.get("verifier") == r.get("producer"):
                return "REJECT:INDEPENDENCE_NOT_ESTABLISHED"
            if r.get("signature") not in (None, "NOT_SIGNED") and not r.get("signature_material"):
                return "REJECT:SIGNATURE_WITHOUT_MATERIAL"
        return "ACCEPT"
    for aid, desc, led in (("AD01", "Duplicate job admission", [{"action": "ADMIT", "id": "P"}, {"action": "ADMIT", "id": "P"}]),
                           ("AD02", "Independent-replication claim by the producer itself", [{"action": "V", "id": "P", "independent": True, "verifier": "a", "producer": "a"}]),
                           ("AD03", "Signed-provenance label without signature", [{"action": "V", "id": "P", "signature": "SIGNED"}])):
        add(attack_id=aid, attack=desc, layer="ADMISSION", expected="REJECT", incumbent="no gate", successor=gate(led))

    out.mkdir(parents=True, exist_ok=True)
    leaves = [r["evidence_leaf"] for r in results]
    summary = {"schema": "frontier-forms.freeze_redteam.result.v1", "fixture_sha256": fl.sha256_hex(base),
               "synthetic_freeze_root": synthetic_root, "tests": results, "results_root": fl.merkle_root(leaves)}
    (out / "RESULTS.json").write_bytes(fl.canonical(summary))
    cols = ["attack_id", "attack", "layer", "expected", "incumbent", "successor", "baseline_hashchain", "evidence_leaf"]
    with open(out / "REDTEAM_TEST_MATRIX.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n"); w.writeheader()
        w.writerows({k: r.get(k, "") for k in cols} for r in results)
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "results")
    s = run(ap.parse_args().out)
    print(json.dumps({"tests": len(s["tests"]), "synthetic_freeze_root": s["synthetic_freeze_root"], "results_root": s["results_root"]}))
