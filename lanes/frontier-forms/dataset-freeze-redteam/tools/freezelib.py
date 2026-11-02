"""Freeze library: canonical leaves, RFC6962-style Merkle tree, inclusion proofs, manifest verifier.

Conventions (inherited from the originating project's custody policy):

* hash algorithm: SHA-256, lowercase hex
* canonical JSON: UTF-8, sorted keys, compact separators, ensure_ascii=False,
  allow_nan=False, followed by a single "\n"
* leaf hash: sha256(0x00 || canonical_leaf_bytes)
* node hash: sha256(0x01 || left_hex_ascii || right_hex_ascii)
* tree recipe: split at the largest power of two strictly below n (RFC 6962 style)

An independent verifier must NOT import this module; reimplement from the recipe.
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable

FREEZE_SCHEMA = "cloudmer.dataset_freeze.v1"
LEAF_SCHEMA = "cloudmer.dataset_freeze.v1.atom_leaf"


class FreezeError(ValueError):
    """Raised when a freeze, leaf, or proof fails verification."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def leaf_hash(leaf_obj: dict) -> str:
    return sha256_hex(b"\x00" + canonical(leaf_obj))


def node_hash(left: str, right: str) -> str:
    return sha256_hex(b"\x01" + left.encode("ascii") + right.encode("ascii"))


def _split(n: int) -> int:
    return 1 << ((n - 1).bit_length() - 1)


def merkle_root(leaves: list[str]) -> str:
    if not leaves:
        raise FreezeError("EMPTY_LEAVES")
    if len(leaves) == 1:
        return leaves[0]
    k = _split(len(leaves))
    return node_hash(merkle_root(leaves[:k]), merkle_root(leaves[k:]))


def inclusion_proof(leaves: list[str], index: int) -> list[dict]:
    """Audit path from leaf to root: list of {side, hash} siblings, bottom-up."""
    if not 0 <= index < len(leaves):
        raise FreezeError("INDEX_OUT_OF_RANGE")
    if len(leaves) == 1:
        return []
    k = _split(len(leaves))
    if index < k:
        return inclusion_proof(leaves[:k], index) + [
            {"side": "R", "hash": merkle_root(leaves[k:])}]
    return inclusion_proof(leaves[k:], index - k) + [
        {"side": "L", "hash": merkle_root(leaves[:k])}]


def verify_inclusion(leaf: str, index: int, size: int, proof: list[dict], root: str) -> bool:
    """Verify an audit path, binding index and tree size (rejects reordered leaves)."""
    if not 0 <= index < size:
        return False

    def walk(idx: int, n: int, path: list[dict]) -> str | None:
        if n == 1:
            return leaf if not path else None
        if not path:
            return None
        k = _split(n)
        sib = path[-1]
        if idx < k:
            if sib["side"] != "R":
                return None
            sub = walk(idx, k, path[:-1])
            return None if sub is None else node_hash(sub, sib["hash"])
        if sib["side"] != "L":
            return None
        sub = walk(idx - k, n - k, path[:-1])
        return None if sub is None else node_hash(sib["hash"], sub)

    return walk(index, size, proof) == root


def occurrence_id(source_id: str, content_sha256: str, origin_ref: str) -> str:
    return "occ:" + sha256_hex(canonical({"source_id": source_id,
                                          "content_sha256": content_sha256,
                                          "origin_ref": origin_ref}))


def build_leaf(atom: dict) -> dict:
    """The exact object hashed for an atom.  Field order is irrelevant (canonical)."""
    keys = ("atom_id", "atom_class", "source_id", "origin_ref", "content_sha256",
            "content_bytes", "occurrence_id", "transform_id", "output_sha256",
            "partition_id", "dataset_version", "consuming_run", "custody_state",
            "rights_assertion_id", "reported_sha256", "reported_by", "derived_from")
    missing = [k for k in keys if k not in atom]
    if missing:
        raise FreezeError("LEAF_MISSING_FIELDS:" + ",".join(missing))
    return {"schema": LEAF_SCHEMA, **{k: atom[k] for k in keys}}


def verify_manifest(manifest: dict, read_bytes) -> dict:
    """Recompute every stored atom from bytes supplied by ``read_bytes(atom)``.

    ``read_bytes`` returns the destination bytes for an atom, or None if the atom
    is not stored.  Returns a per-atom status map plus the recomputed root.
    Raises FreezeError on the first integrity violation.
    """
    if manifest.get("schema") != FREEZE_SCHEMA:
        raise FreezeError("SCHEMA_MISMATCH")
    atoms = manifest["atoms"]
    ids = [a["atom_id"] for a in atoms]
    if len(ids) != len(set(ids)):
        raise FreezeError("DUPLICATE_ATOM_ID")
    occ = [a["occurrence_id"] for a in atoms]
    if len(occ) != len(set(occ)):
        raise FreezeError("REUSED_OCCURRENCE_ID")
    if ids != sorted(ids):
        raise FreezeError("LEAF_ORDER_NOT_CANONICAL")
    if len(atoms) != manifest["merkle"]["leaf_count"]:
        raise FreezeError("LEAF_COUNT_MISMATCH")
    statuses, leaves = {}, []
    # Never reflect a producer-supplied "VERIFIED" into the readback result.
    # This vocabulary is distinct from the returned verifier status.
    allowed_custody = {"STORED_READBACK_VERIFIED", "NOT_STORED", "UNKNOWN"}
    for a in atoms:
        if a.get("custody_state") not in allowed_custody:
            raise FreezeError("CUSTODY_STATE_NOT_RECOGNIZED:" + a["atom_id"])
        if a["occurrence_id"] != occurrence_id(a["source_id"], a["content_sha256"], a["origin_ref"]):
            raise FreezeError("OCCURRENCE_ID_MISMATCH:" + a["atom_id"])
        if a["custody_state"] == "STORED_READBACK_VERIFIED":
            raw = read_bytes(a)
            if raw is None:
                raise FreezeError("STORED_ATOM_MISSING:" + a["atom_id"])
            h = sha256_hex(raw)
            if h != a["output_sha256"] or len(raw) != a["content_bytes"]:
                raise FreezeError("BYTE_DRIFT:" + a["atom_id"])
            if a["transform_id"] == "IDENTITY_COPY_V1" and a["output_sha256"] != a["content_sha256"]:
                raise FreezeError("IDENTITY_TRANSFORM_HASH_MISMATCH:" + a["atom_id"])
            statuses[a["atom_id"]] = "VERIFIED"
        else:
            if a["output_sha256"] not in ("NOT_STORED", "UNKNOWN"):
                raise FreezeError("UNSTORED_ATOM_CLAIMS_OUTPUT_HASH:" + a["atom_id"])
            statuses[a["atom_id"]] = a["custody_state"]
        lh = leaf_hash(build_leaf(a))
        if lh != a["leaf_sha256"]:
            raise FreezeError("LEAF_HASH_MISMATCH:" + a["atom_id"])
        leaves.append(lh)
    root = merkle_root(leaves)
    if root != manifest["merkle"]["root"]:
        raise FreezeError("ROOT_MISMATCH")
    return {"root": root, "leaf_count": len(leaves), "atoms": statuses}


def hash_chain(records: Iterable[bytes]) -> list[str]:
    """Baseline comparator: linear hash chain h_i = sha256(h_{i-1} || sha256(r_i))."""
    prev, out = "0" * 64, []
    for r in records:
        prev = sha256_hex(prev.encode("ascii") + sha256_hex(r).encode("ascii"))
        out.append(prev)
    return out
