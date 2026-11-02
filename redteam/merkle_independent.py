#!/usr/bin/env python3
"""Independent re-implementation of the FCO Merkle scheme used by the predecessor.

Written from the *declared* construction string only, without importing any
predecessor code:
    leaf  = SHA256(0x00 || canonical_json(record))
    node  = SHA256(0x01 || left || right)
    odd level -> duplicate the last node
Canonical JSON: sort_keys, separators (',',':'), ensure_ascii=False, UTF-8.

A matching root proves byte identity of the committed records. It does not
prove that the records are true, that a leaf caused any result, or that a
manifest's *unhashed* fields (parent pointers, status strings) are authentic.
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable, Sequence

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def h(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def leaf_hash(record) -> bytes:
    return h(LEAF_PREFIX + canonical(record))


def node_hash(left: bytes, right: bytes) -> bytes:
    return h(NODE_PREFIX + left + right)


def levels_from_leaf_hashes(leaf_hashes: Sequence[bytes]) -> list[list[bytes]]:
    if not leaf_hashes:
        raise ValueError("EMPTY_TREE")
    levels = [list(leaf_hashes)]
    while len(levels[-1]) > 1:
        cur = list(levels[-1])
        if len(cur) % 2 == 1:
            cur.append(cur[-1])
        levels[-1] = cur  # record the padded level so proofs can see the duplicate
        levels.append([node_hash(cur[i], cur[i + 1]) for i in range(0, len(cur), 2)])
    return levels


def root_from_leaf_hashes(leaf_hashes: Sequence[bytes]) -> bytes:
    return levels_from_leaf_hashes(leaf_hashes)[-1][0]


def root_of_records(records: Iterable) -> str:
    return root_from_leaf_hashes([leaf_hash(r) for r in records]).hex()


def inclusion_proof(leaf_hashes: Sequence[bytes], index: int) -> list[dict]:
    levels = levels_from_leaf_hashes(leaf_hashes)
    proof = []
    pos = index
    for level in levels[:-1]:
        sib = pos ^ 1
        proof.append({"sibling": level[sib].hex(), "side": "left" if sib < pos else "right"})
        pos //= 2
    return proof


def verify_inclusion(leaf_hex: str, proof: Sequence[dict], root_hex: str) -> bool:
    cur = bytes.fromhex(leaf_hex)
    for step in proof:
        sib = bytes.fromhex(step["sibling"])
        if step["side"] == "left":
            cur = node_hash(sib, cur)
        elif step["side"] == "right":
            cur = node_hash(cur, sib)
        else:
            return False
    return cur.hex() == root_hex


def rfc6962_root(leaf_hashes: Sequence[bytes]) -> bytes:
    """Reference RFC 6962 split (no duplication) used only to show the ambiguity
    of duplicate-last-odd trees; never used to claim predecessor roots."""
    n = len(leaf_hashes)
    if n == 1:
        return leaf_hashes[0]
    k = 1
    while k * 2 < n:
        k *= 2
    return node_hash(rfc6962_root(leaf_hashes[:k]), rfc6962_root(leaf_hashes[k:]))
