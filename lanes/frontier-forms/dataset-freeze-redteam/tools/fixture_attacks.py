"""Synthetic-fixture data attacks and input bindings (public-safe extract of Lane B).

INCUMBENT models a common training-kernel input check: filename lookup, gene count, batch split
equality and SHA-256 of *positional* row-index lists (file size recorded, never compared).
BINDING_V2 is the proposed successor: hash file bytes at consumption, bind gene names and
per-row content.  All data here is synthetic.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import freezelib as fl  # noqa: E402

SALT = "FIXTURE-SALT-20261102"
N_GENES = 24
TRAIN_CAP, VAL_CAP = 60, 16


# --------------------------------------------------------------------------- fixture
def make_fixture(seed: int = 20261102) -> dict:
    rng = random.Random(seed)
    batches = [f"Flex_{p}_{i:02d}" for p in (1, 2, 3) for i in range(1, 9)]          # 24 batches
    targets = [f"GENE{t:03d}" for t in range(12)]
    genes = [f"g{j:03d}" for j in range(N_GENES)]
    rows = []
    for b in batches:
        for t in rng.sample(targets, 6):
            rows.append({"batch": b, "target_gene": t, "cells": rng.randint(50, 400),
                         "x": [round(rng.gammavariate(2.0, 3.0), 4) for _ in genes]})
    return {"genes": genes, "rows": rows}


def serialize(fx: dict) -> bytes:
    """Deterministic container: canonical JSON header + little-endian float32 matrix."""
    header = fl.canonical({"genes": fx["genes"],
                           "obs": [{k: r[k] for k in ("batch", "target_gene", "cells")} for r in fx["rows"]]})
    mat = b"".join(struct.pack("<%df" % len(r["x"]), *r["x"]) for r in fx["rows"])
    return struct.pack("<I", len(header)) + header + mat


def deserialize(raw: bytes) -> dict:
    n = struct.unpack("<I", raw[:4])[0]
    head = json.loads(raw[4:4 + n])
    g = len(head["genes"])
    mat = raw[4 + n:]
    rows = []
    for i, o in enumerate(head["obs"]):
        x = list(struct.unpack("<%df" % g, mat[i * 4 * g:(i + 1) * 4 * g]))
        rows.append({**o, "x": x})
    return {"genes": head["genes"], "rows": rows}


def hval(s: str) -> int:
    return int(hashlib.sha256((SALT + "|" + s).encode()).hexdigest(), 16)


def split(fx: dict) -> dict:
    """Same algorithm as the incumbent kernel: batch-level split, then salted positional subsample."""
    bb = [r["batch"] for r in fx["rows"]]
    groups = sorted(set(bb), key=hval)
    test_b, val_b, train_b = set(groups[:6]), set(groups[6:9]), set(groups[9:])
    train_ids = [i for i, b in enumerate(bb) if b in train_b]
    val_ids = [i for i, b in enumerate(bb) if b in val_b]
    held = [i for i, b in enumerate(bb) if b in test_b]
    return {"test_b": sorted(test_b), "val_b": sorted(val_b), "train_b": sorted(train_b),
            "train_rows": sorted(train_ids, key=lambda i: hval("train_" + str(i)))[:TRAIN_CAP],
            "val_rows": sorted(val_ids, key=lambda i: hval("valid_" + str(i)))[:VAL_CAP],
            "held": held}


def row_content_hash(r: dict, genes: list[str]) -> str:
    return fl.sha256_hex(fl.canonical({"batch": r["batch"], "target_gene": r["target_gene"], "cells": r["cells"],
                                       "x": dict(zip(genes, [float(struct.unpack('<f', struct.pack('<f', v))[0]) for v in r["x"]]))}))


# --------------------------------------------------------------------------- bindings
def incumbent_expected(raw: bytes) -> dict:
    fx = deserialize(raw)
    s = split(fx)
    return {"gene_count": len(fx["genes"]), "holdout_batches": s["test_b"], "valid_batches": s["val_b"],
            "train_batches": s["train_b"],
            "train_row_ids_sha256": fl.sha256_hex(fl.canonical(s["train_rows"])),
            "validation_row_ids_sha256": fl.sha256_hex(fl.canonical(s["val_rows"])),
            "holdout_row_ids_sha256": fl.sha256_hex(fl.canonical(s["held"])), "heldout_rows": len(s["held"])}


def incumbent_check(raw: bytes, exp: dict) -> tuple[bool, str]:
    """Return (accepted, reason).  Mirrors the incumbent kernel's checks; st_size is recorded, not compared."""
    try:
        fx = deserialize(raw)
    except Exception as e:  # noqa: BLE001
        return False, "PARSE_ERROR:" + type(e).__name__
    if len(fx["genes"]) != exp["gene_count"]:
        return False, "GENE_AXIS_MISMATCH"
    s = split(fx)
    if s["test_b"] != exp["holdout_batches"] or s["val_b"] != exp["valid_batches"] or s["train_b"] != exp["train_batches"]:
        return False, "FROZEN_SPLIT_DRIFT"
    if set(s["test_b"]) & (set(s["train_b"]) | set(s["val_b"])):
        return False, "BATCH_OVERLAP"
    ok = (fl.sha256_hex(fl.canonical(s["train_rows"])) == exp["train_row_ids_sha256"]
          and fl.sha256_hex(fl.canonical(s["val_rows"])) == exp["validation_row_ids_sha256"]
          and fl.sha256_hex(fl.canonical(s["held"])) == exp["holdout_row_ids_sha256"]
          and len(s["held"]) == exp["heldout_rows"])
    return (True, "ACCEPTED") if ok else (False, "FROZEN_ROW_ID_DRIFT")


def v2_expected(raw: bytes) -> dict:
    fx = deserialize(raw)
    s = split(fx)
    rc = lambda ids: fl.sha256_hex(fl.canonical([row_content_hash(fx["rows"][i], fx["genes"]) for i in ids]))  # noqa: E731
    return {"file_sha256": fl.sha256_hex(raw), "file_bytes": len(raw),
            "gene_axis_sha256": fl.sha256_hex(fl.canonical(fx["genes"])),
            "train_content_sha256": rc(s["train_rows"]), "val_content_sha256": rc(s["val_rows"]),
            "held_content_sha256": rc(s["held"]), **incumbent_expected(raw)}


def v2_check(raw: bytes, exp: dict) -> tuple[bool, str]:
    """Proposed successor binding: hash bytes at consumption, bind gene names and row content."""
    if len(raw) != exp["file_bytes"]:
        return False, "FILE_SIZE_DRIFT"
    if fl.sha256_hex(raw) != exp["file_sha256"]:
        return False, "FILE_CONTENT_DRIFT"
    ok, why = incumbent_check(raw, exp)
    if not ok:
        return ok, why
    fx = deserialize(raw)
    if fl.sha256_hex(fl.canonical(fx["genes"])) != exp["gene_axis_sha256"]:
        return False, "GENE_AXIS_NAME_DRIFT"
    return True, "ACCEPTED"


def leakage_report(raw: bytes) -> dict:
    fx = deserialize(raw)
    s = split(fx)
    content = lambda ids: {row_content_hash(fx["rows"][i], fx["genes"])[:0] + fl.sha256_hex(  # noqa: E731
        fl.canonical(fx["rows"][i]["x"])) for i in ids}
    tgt = lambda ids: {fx["rows"][i]["target_gene"] for i in ids}  # noqa: E731
    tr, va, he = s["train_rows"], s["val_rows"], s["held"]
    return {"expression_vector_overlap_train_held": len(content(tr) & content(he)),
            "expression_vector_overlap_train_val": len(content(tr) & content(va)),
            "batch_overlap": len(set(s["train_b"]) & set(s["test_b"])),
            "target_overlap_train_held": len(tgt(tr) & tgt(he)), "held_targets": len(tgt(he))}


def baseline_check(raw: bytes, exp_file_sha: str) -> bool:
    return fl.sha256_hex(raw) == exp_file_sha


# --------------------------------------------------------------------------- data attacks
def mutate(fx: dict, kind: str) -> dict:
    m = copy.deepcopy(fx)
    s = split(fx)
    if kind == "byte_flip_same_size":
        m["rows"][s["train_rows"][0]]["x"][3] += 1.0
    elif kind == "row_reorder_within_batch":
        b = m["rows"][s["train_rows"][0]]["batch"]
        idx = [i for i, r in enumerate(m["rows"]) if r["batch"] == b]
        rot = [m["rows"][i] for i in idx[1:] + idx[:1]]
        for i, r in zip(idx, rot):
            m["rows"][i] = r
    elif kind == "gene_reorder":
        perm = list(range(len(m["genes"])))[::-1]
        for r in m["rows"]:
            r["x"] = [r["x"][j] for j in perm]
    elif kind == "gene_rename":
        m["genes"] = ["ENSG_" + g for g in m["genes"]]
    elif kind == "sample_id_swap_train_holdout":
        a, b = s["train_b"][0], s["test_b"][0]
        for r in m["rows"]:
            r["batch"] = b if r["batch"] == a else (a if r["batch"] == b else r["batch"])
    elif kind == "duplicate_record":
        m["rows"].insert(s["held"][0] + 1, copy.deepcopy(m["rows"][s["held"][0]]))
    elif kind == "duplicate_record_append":
        m["rows"].append(copy.deepcopy(m["rows"][-1]))
    elif kind == "missing_record":
        del m["rows"][s["held"][-1]]
    elif kind == "missing_record_tail":
        del m["rows"][-1]
    elif kind == "holdout_row_copied_into_train":
        m["rows"][s["train_rows"][0]]["x"] = list(m["rows"][s["held"][0]]["x"])
    elif kind == "label_switch":
        i, j = s["train_rows"][0], s["train_rows"][1]
        m["rows"][i]["target_gene"], m["rows"][j]["target_gene"] = m["rows"][j]["target_gene"], m["rows"][i]["target_gene"]
    elif kind == "batch_in_two_partitions":
        tb = s["test_b"][0]
        for i in s["train_rows"][:3]:
            m["rows"][i]["batch"] = tb
    else:
        raise ValueError(kind)
    return m


DATA_ATTACKS = [
    ("RT01", "byte_flip_same_size", "Modified file bytes with unchanged size/metadata", "DATA_INTEGRITY"),
    ("RT02", "row_reorder_within_batch", "Reordered rows (positional row ids unchanged)", "DATA_INTEGRITY"),
    ("RT03", "gene_reorder", "Reordered gene axis, same shape", "DATA_INTEGRITY"),
    ("RT04", "gene_rename", "Gene identifiers changed, same shape", "DATA_INTEGRITY"),
    ("RT05", "sample_id_swap_train_holdout", "Sample/batch ID swap between train and holdout", "SPLIT_ISOLATION"),
    ("RT06", "duplicate_record", "Duplicate record inserted inside a holdout batch", "DATA_INTEGRITY"),
    ("RT06b", "duplicate_record_append", "Duplicate record appended at file end", "DATA_INTEGRITY"),
    ("RT07", "missing_record", "Missing record in a holdout batch", "DATA_INTEGRITY"),
    ("RT07b", "missing_record_tail", "Missing record at file end", "DATA_INTEGRITY"),
    ("RT08", "holdout_row_copied_into_train", "Train/holdout leakage: held-out expression copied into a train row", "SPLIT_ISOLATION"),
    ("RT09", "batch_in_two_partitions", "Batch/donor leakage: holdout batch label on train rows", "SPLIT_ISOLATION"),
    ("RT11", "label_switch", "Label (target identity) switching between rows", "DATA_INTEGRITY"),
]
