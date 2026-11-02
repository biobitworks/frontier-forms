"""Detection mechanisms for the prebuilt error-injected forms (see PREREG.json).

M1_merkle_breakpoint  recompute field leaves and the form root; flag leaves that differ from the seal
M2_lean4_constraints  flags produced by `lean --run lean/FormChecks.lean` (loaded from its output)
M3_fco_source_binding recompute each field from the teammate passport with the full candidate mapping

Detectors read forms.jsonl only. They never read truth.jsonl or the oracle.
"""
from __future__ import annotations

import json
import re

from .arms import MODULES, map_field
from .cohort import merkle_root
from .inject import leaf

MECHANISMS = ("M1_merkle_breakpoint", "M2_lean4_constraints", "M3_fco_source_binding")
FULL = frozenset(MODULES)


def m1_merkle(form: dict) -> dict:
    fid = form["form_id"]
    sealed = form["seal"]["leaves"]
    flags = {k for k, f in form["fields"].items() if leaf(fid, k, f["value"]) != sealed.get(k)}
    keys = sorted(form["fields"])
    root_now = merkle_root([leaf(fid, k, form["fields"][k]["value"]) for k in keys])
    root_sealed = merkle_root([sealed[k] for k in keys])
    return {"flags": flags, "root_match": root_now == root_sealed}


def load_lean_flags(path) -> dict:
    out = {}
    for line in open(path):
        line = line.strip()
        if line:
            row = json.loads(line)
            out[row["form_id"]] = {f["field_key"]: f["rule"] for f in row["flags"]}
    return out


def _norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().casefold()


def _same(expected, actual, typ):
    if expected in (None, ""):
        return _norm(actual) == ""
    if _norm(actual) == "":
        return False
    if typ == "number":
        try:
            return abs(float(expected) - float(actual)) <= 0.05
        except ValueError:
            return False
    if ";" in str(expected) or ";" in str(actual):
        return {_norm(x) for x in str(expected).split(";") if _norm(x)} == \
               {_norm(x) for x in str(actual).split(";") if _norm(x)}
    return _norm(expected) == _norm(actual)


def m3_source_binding(form: dict, passport: dict) -> set:
    flags = set()
    for k, f in form["fields"].items():
        dec, val = map_field(f["label"], {"options": f.get("options") or []}, passport, FULL)
        expected = val if dec == "fill" else ""
        if isinstance(expected, float):
            expected = f"{expected:g}"
        if not _same(expected, f["value"], f["type"]):
            flags.add(k)
    return flags
