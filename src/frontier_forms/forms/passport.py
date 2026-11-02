"""Teammate patient passport, built with the merged Supabase importer's own code.

`scripts/import_fhir.py` (teammate PR #4) defines `PassportBuilder`, the exact
FHIR -> passport normalisation the Supabase app uses. We load that class
unchanged so the local B0 sees the same passport the team's database would
hold. Two things differ, both outside the builder's logic:

* no database: psycopg/dotenv are stubbed only if they are not installed;
* the builder's uuid4 row ids are replaced by deterministic content ids, so
  replays are byte-identical.

The importer file's SHA-256 is pinned in the B0 freeze manifest.
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
IMPORTER = REPO / "scripts" / "import_fhir.py"
_MODULE = None


def _stub_missing(name: str, **attrs):
    if name in sys.modules:
        return
    try:
        importlib.import_module(name)
        return
    except Exception:
        pass
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod


def load_importer():
    """Import scripts/import_fhir.py without needing a database driver."""
    global _MODULE
    if _MODULE is not None:
        return _MODULE
    _stub_missing("psycopg", connect=None)
    _stub_missing("psycopg.types")
    _stub_missing("psycopg.types.json", Jsonb=lambda x: x)
    _stub_missing("dotenv", load_dotenv=lambda *a, **k: None)
    spec = importlib.util.spec_from_file_location("ff_teammate_import_fhir", IMPORTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MODULE = mod
    return mod


def _cid(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]


def build_passport(bundle: dict, source_file: str, synthetic_id: str) -> dict:
    """Return a JSON-serialisable passport with deterministic ids."""
    mod = load_importer()
    builder = mod.PassportBuilder(bundle, source_file)
    row = builder.passport_row(synthetic_id)
    builder.build_facts()
    pid = builder.patient["id"]
    remap = {}
    sources = []
    for s in builder.source_records:
        new = "src_" + _cid(pid, s["fhir_resource_type"], s["fhir_resource_id"])
        remap[s["id"]] = new
        sources.append({**s, "id": new, "payload": None})  # payload dropped: B0 reads facts only
    facts = []
    for i, f in enumerate(builder.facts):
        src = remap.get(f["source_record_id"], f["source_record_id"])
        facts.append({**f, "id": "fact_" + _cid(pid, f["fact_key"], src, str(i)),
                      "source_record_id": src})
    return {
        "synthetic": True,
        "synthetic_id": synthetic_id,
        "patient_id": pid,
        **row,
        "source_records": sources,
        "facts": facts,
    }
