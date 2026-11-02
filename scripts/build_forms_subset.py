#!/usr/bin/env python3
"""Deterministically reduce raw Synthea bundles to the resources the form lane reads.

The full 100-patient Synthea output is ~380 MB, too large for git. This
transform keeps, per patient bundle and in original entry order:

  Patient, AllergyIntolerance, Condition, MedicationRequest, Immunization (whole);
  Medication resources referenced by a kept MedicationRequest (whole);
  Observation whose LOINC is a tracked vital or smoking code (whole);
  ExplanationOfBenefit reduced to resourceType/id/status/created/billablePeriod/insurer/patient.

Output is canonical JSON (sorted keys, no extra whitespace). The raw-file
SHA-256 of every input is recorded in the manifest, so the subset is bound to
the exact raw bytes it came from. Raw bytes can be regenerated from the pinned
Synthea jar + seed recorded in data/forms_cohort_v1/GENERATION.json.

    python3 scripts/build_forms_subset.py RAW_FHIR_DIR data/forms_cohort_v1 --limit 100
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frontier_forms.forms.cohort import cohort_root, load_cohort  # noqa: E402

TRANSFORM_VERSION = "forms-subset-v1"
WHOLE = {"Patient", "AllergyIntolerance", "Condition", "MedicationRequest", "Immunization"}
LOINC = {"8302-2", "29463-7", "39156-5", "85354-9", "8867-4", "72166-2"}
EOB_KEEP = ("resourceType", "id", "status", "created", "billablePeriod", "insurer", "patient")


def reduce_bundle(bundle):
    entries = bundle["entry"]
    med_refs = {(e["resource"].get("medicationReference") or {}).get("reference")
                for e in entries if e["resource"]["resourceType"] == "MedicationRequest"}
    out = []
    for e in entries:
        r = e["resource"]
        t = r["resourceType"]
        full = e.get("fullUrl")
        keep = None
        if t in WHOLE:
            keep = r
        elif t == "Medication" and (full in med_refs or f"Medication/{r['id']}" in med_refs):
            keep = r
        elif t == "Observation" and {c.get("code") for c in (r.get("code") or {}).get("coding") or []} & LOINC:
            keep = r
        elif t == "ExplanationOfBenefit":
            keep = {k: r[k] for k in EOB_KEEP if k in r}
        if keep is not None:
            ent = {"resource": keep}
            if full:
                ent["fullUrl"] = full
            out.append(ent)
    return {"resourceType": "Bundle", "type": bundle.get("type", "transaction"), "entry": out}


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()
    members, bundles = load_cohort(Path(args.raw_dir), limit=args.limit)
    out = Path(args.out_dir)
    bdir = out / "bundles"
    bdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for m in members:
        data = canonical(reduce_bundle(bundles[m.patient_id]))
        name = f"patient_{m.patient_id}.json"
        (bdir / name).write_bytes(data)
        rows.append({"patient_id": m.patient_id, "split": m.split, "raw_file": m.path.name,
                     "raw_sha256": m.sha256, "subset_file": f"bundles/{name}",
                     "subset_sha256": hashlib.sha256(data).hexdigest()})
    sub_members, _ = load_cohort(bdir, limit=None)
    manifest = {
        "dataset_id": "FF-SYNTHEA-FORMS-COHORT-V1",
        "transform": TRANSFORM_VERSION,
        "n_patients": len(rows),
        "raw_cohort_root": cohort_root(members),
        "subset_cohort_root": cohort_root(sub_members),
        "members": rows,
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(manifest["n_patients"], manifest["raw_cohort_root"], manifest["subset_cohort_root"])


if __name__ == "__main__":
    main()
