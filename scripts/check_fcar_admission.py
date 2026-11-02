#!/usr/bin/env python3
"""Read-only Frontier Forms freeze/challenge/replicate/admit gate.

This is a *local Frontier Forms* admission firewall. It does not read or modify
Vita DAISY training data, weights, checkpoints or jobs. Never promote discovery
results on the strength of a hash or a significant paired test.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_FAMILIES = {
    "fco_lomo", "detector_lomo", "training_size_cross_section",
    "model_weight_comparison", "actual_training_snapshot", "methodology_only"
}
FORBIDDEN_PROMOTION = {"SUPPORTED", "SUPPORTED_GAIN", "ADMITTED", "PROMOTED"}
def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def read_json(path: Path) -> dict:
    return json.loads(path.read_bytes())

def assess(freeze: dict, graph: dict, pointer: dict, snapshot: dict) -> dict:
    """Check declared *existing* source and gate states, not independent clinical truth."""
    if freeze.get("lane") != "frontier-forms" or graph.get("lane") != "frontier-forms":
        raise ValueError("CROSS_PROGRAM_SOURCE")
    if freeze.get("dataset", {}).get("id") != "FF-SYNTHEA-FORMS-COHORT-V1":
        raise ValueError("WRONG_COHORT")
    if freeze["dataset"]["subset_cohort_root"] != graph.get("dataset_root"):
        raise ValueError("FROZEN_COHORT_ROOT_MISMATCH")
    if snapshot.get("program_id") != "frontier-forms":
        raise ValueError("WRONG_SNAPSHOT_PROGRAM")
    if snapshot.get("source_cohort_root") != freeze["dataset"]["subset_cohort_root"]:
        raise ValueError("SNAPSHOT_COHORT_DRIFT")
    if pointer.get("root") != snapshot.get("root"):
        raise ValueError("POINTER_SNAPSHOT_ROOT_MISMATCH")
    events = pointer.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("MISSING_EVENTS")
    ids = [e.get("id") for e in events]
    if len(set(ids)) != len(ids):
        raise ValueError("DUPLICATE_EVENT_ID")
    methods = [e for e in events if e.get("family") == "methodology_only"]
    if len(methods) != 1 or methods[0].get("id") != "FF-VITA-DAISY-ABSTRACT-ONLY":
        raise ValueError("DAISY_METHOD_BOUNDARY_MISSING")
    method = methods[0]
    for field in ("delta", "model_weights_sha256", "source_root",
                  "ci95_patient_cluster", "mcnemar_p_two_sided"):
        if method.get(field) is not None:
            raise ValueError("DAISY_MEASURED_EVIDENCE_TRANSFER:" + field)
    if (method.get("status") != "NOT_COMPUTED"
        or not str(method.get("replication", "")).startswith("NOT_TESTED")
        or method.get("model_weights_changed") is not False):
        raise ValueError("DAISY_METHOD_MISLABELED")
    for e in events:
        family = e.get("family")
        if family not in ALLOWED_FAMILIES:
            raise ValueError("UNKNOWN_EVIDENCE_FAMILY:" + str(family))
        if family == "methodology_only":
            continue
        if e.get("source_program_id", "frontier-forms") != "frontier-forms":
            raise ValueError("CROSS_PROGRAM_EVIDENCE")
        if "daisy" in (str(e.get("model", "")) + " " + str(e.get("id", ""))).lower():
            raise ValueError("FOREIGN_MODEL_CHECKPOINT_IN_FORMS")
        if e.get("promoted") is True or e.get("status") in FORBIDDEN_PROMOTION:
            # A successor admission schema must present a separately frozen,
            # independently audited replication record; current v1 has none.
            raise ValueError("UNSUPPORTED_PROMOTION:" + str(e.get("id")))
    challenges = [e for e in events if e.get("family") in ("fco_lomo", "detector_lomo")]
    if not challenges:
        raise ValueError("MISSING_CHALLENGER_RECORDS")
    if freeze.get("state") not in {"FROZEN_PENDING_PI_REVIEW", "FROZEN_VERIFIED"}:
        raise ValueError("FREEZE_NOT_RECORDED")
    replicated = [e for e in events if e.get("family") != "methodology_only"
                  and isinstance(e.get("replication_receipt"), dict)
                  and e["replication_receipt"].get("independent_cohort_verified") is True
                  and e["replication_receipt"].get("independent_oracle_verified") is True]
    # Version 1 intentionally never supports clinical admission: even if
    # one entry claims independent replication, PI admission is a separate gate.
    return {
        "schema": "frontier_forms.fcar_boundary_assessment.v1",
        "program_id": "frontier-forms",
        "methodology_source": "Vita DAISY — abstraction only, no evidence import",
        "freeze": {"state": "RECORDED_PENDING_PI_REVIEW" if freeze["state"] == "FROZEN_PENDING_PI_REVIEW"
                   else "RECORDED_FROZEN", "cohort": freeze["dataset"]["id"],
                   "patients_reported_in_freeze": freeze["dataset"]["n_patients"],
                   "subset_cohort_root": freeze["dataset"]["subset_cohort_root"]},
        "challenge": {"state": "DISCOVERY_EVIDENCE_PRESENT",
                      "fco_lomo_events": sum(e["family"] == "fco_lomo" for e in events),
                      "detector_lomo_events": sum(e["family"] == "detector_lomo" for e in events),
                      "all_challenger_promotions": False},
        "replicate": {"deterministic_integrity_replay": "SEPARATE_FROM_PROSPECTIVE_REPLICATION",
                      "independent_replicated_records_declared": len(replicated),
                      "independent_prospective_replication": "NOT_TESTED" if not replicated else "REPORTED_REQUIRES_PI_REVIEW"},
        "admit": {"state": "HOLD_NO_INDEPENDENT_PI_ADMISSION",
                  "clinical_or_model_superiority_supported": False,
                  "reason": "v1 requires an independent prospective replication and human scientific decision"},
        "boundary": {"methodology_only": True, "daisy_weight_hash_imported": False,
                     "daisy_performance_imported": False, "daisy_program_root_imported": False},
        "source_snapshot_root": snapshot["root"],
        "n_events": len(events)
    }

def live_assessment(root: Path) -> dict:
    pointer = read_json(root / "dashboard/training_progress_latest.json")
    snapshot_path = root / pointer["source_snapshot"]
    manifest = read_json(snapshot_path / "manifest.json")
    # Reuse the existing exact-byte root/statistical verifier; do not run
    # inference, training, new bootstrap samples or DAISY jobs.
    import sys
    sys.path.insert(0, str(root / "scripts"))
    from verify_training_progress import verify
    verified = verify(snapshot_path)
    if verified["root"] != pointer["root"]:
        raise ValueError("EXISTING_RECEIPT_REPLAY_FAILED")
    freeze_path = root / "evidence/forms_b0/B0_FREEZE_V1.json"
    graph_path = root / "evidence/forms_arms/run_v1/FCG_ARMS_V1.json"
    result = assess(read_json(freeze_path), read_json(graph_path), pointer, manifest)
    result["source_bytes"] = {
        "freeze_manifest_sha256": sha(freeze_path.read_bytes()),
        "challenge_graph_sha256": sha(graph_path.read_bytes()),
        "training_pointer_sha256": sha((root / "dashboard/training_progress_latest.json").read_bytes()),
        "verified_snapshot_manifest_sha256": sha((snapshot_path / "manifest.json").read_bytes())}
    result["receipt_verifier"] = "scripts/verify_training_progress.py:PASS_EXISTING_BYTES"
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path, help="Write new public-safe JSON, preserving existing bytes")
    a = p.parse_args()
    result = live_assessment(a.root)
    raw = (json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if a.output:
        dest = a.output
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.read_bytes() != raw:
            raise SystemExit("IMMUTABLE_RECEIPT_COLLISION")
        if not dest.exists():
            dest.write_bytes(raw)
    print(json.dumps(result, sort_keys=True))
if __name__ == "__main__":
    main()
