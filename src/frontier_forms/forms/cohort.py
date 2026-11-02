"""Cohort loading, content hashing, Merkle root and declared split assignment.

A cohort is a directory of Synthea FHIR R4 patient bundles. Hospital and
practitioner bundles are ignored. Order is by Patient.id, never by file name
or mtime, so the same bytes always give the same cohort root.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

PATIENT_FILE = re.compile(r"_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.json$")
SPLIT_RULE = "split-v1: int(sha256('split-v1|'+patient_id)[:8],16)%100 -> <70 train, <85 validation, else test"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def merkle_root(leaf_hex: list[str]) -> str:
    """Binary SHA-256 Merkle root over hex leaves; odd node is promoted.

    Leaves and interior nodes are domain separated (0x00 / 0x01) so a leaf
    cannot be replayed as an interior node.
    """
    if not leaf_hex:
        return sha256_bytes(b"\x00EMPTY")
    level = [hashlib.sha256(b"\x00" + bytes.fromhex(h)).digest() for h in leaf_hex]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                nxt.append(hashlib.sha256(b"\x01" + level[i] + level[i + 1]).digest())
            else:
                nxt.append(level[i])
        level = nxt
    return level[0].hex()


def assign_split(patient_id: str) -> str:
    bucket = int(hashlib.sha256(f"split-v1|{patient_id}".encode()).hexdigest()[:8], 16) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "validation"
    return "test"


@dataclass(frozen=True)
class CohortMember:
    patient_id: str
    path: Path
    sha256: str
    split: str
    deceased: bool


def patient_of(bundle: dict) -> dict:
    return next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")


def load_cohort(bundle_dir: Path, limit: int | None = None, include_deceased: bool = False):
    """Return (members, bundles_by_patient_id).

    Selection is deterministic: sort living patients by Patient.id and take
    the first `limit`. The returned members carry the raw-file SHA-256.
    """
    candidates = []
    for path in sorted(Path(bundle_dir).glob("*.json")):
        if not PATIENT_FILE.search(path.name):
            continue
        raw = path.read_bytes()
        bundle = json.loads(raw)
        p = patient_of(bundle)
        deceased = "deceasedDateTime" in p or bool(p.get("deceasedBoolean"))
        if deceased and not include_deceased:
            continue
        candidates.append((p["id"], path, sha256_bytes(raw), deceased, bundle))
    candidates.sort(key=lambda c: c[0])
    if len({c[0] for c in candidates}) != len(candidates):
        raise ValueError("DUPLICATE_PATIENT_ID")
    if limit is not None:
        candidates = candidates[:limit]
    members = [CohortMember(pid, path, digest, assign_split(pid), dec)
               for pid, path, digest, dec, _ in candidates]
    bundles = {pid: bundle for pid, _, _, _, bundle in candidates}
    return members, bundles


def cohort_root(members: list[CohortMember]) -> str:
    leaves = [sha256_bytes(f"{m.patient_id}|{m.sha256}".encode()) for m in members]
    return merkle_root(leaves)
