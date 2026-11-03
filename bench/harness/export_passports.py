"""Export the Synthea passports from Supabase into a local frozen file, so the benchmark never touches the database.

    export_passports.py        writes data/synthea_passports.json (synthetic patients only)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parents[1] / ".env")

with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=15, autocommit=False) as db:
    db.execute("set transaction read only")
    people = db.execute("""select id::text, synthetic_id, display_name, demographics, contact, insurance, is_synthetic
                           from public.patient_passports where is_synthetic order by synthetic_id""").fetchall()
    rows = db.execute("""select f.passport_id::text, f.id::text, f.fact_key, f.value, f.status,
                                f.valid_from::text, f.valid_until::text, s.fhir_resource_type, s.fhir_resource_id
                         from public.passport_facts f left join public.source_records s on s.id = f.source_record_id
                         order by f.passport_id, f.fact_key, f.valid_from""").fetchall()

facts: dict[str, list[dict]] = {}
for pid, fid, key, value, status, start, end, kind, rid in rows:
    facts.setdefault(pid, []).append({"id": fid, "fact_key": key, "value": value, "status": status, "valid_from": start,
                                      "valid_until": end, "source": {"resource_type": kind, "resource_id": rid}})
out = [{"synthetic_id": sid, "display_name": name, "demographics": demo, "contact": contact, "insurance": ins,
        "facts": facts.get(pid, [])} for pid, sid, name, demo, contact, ins, synthetic in people if synthetic]
(HERE / "data/synthea_passports.json").write_text(json.dumps(out, indent=1, sort_keys=True, default=str))
print(len(out), "passports,", sum(len(p["facts"]) for p in out), "facts")
