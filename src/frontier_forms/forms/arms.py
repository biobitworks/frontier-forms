"""Module arms built on top of the frozen B0 (b0.py is never edited).

Each module is one named mechanism ("leaf"). An arm is B0 plus a set of
modules, so incremental additions (B0 + one module) and LOMO removals
(full - one module) differ from their parent in exactly one leaf. Only those
single-leaf edges are used to attribute an outcome change to a module.

Modules
  L1_evidence_abstain  A list answer with no supporting passport fact is not
                       written as "None"; the field is left for the patient.
  L2_unit_validation   Read the unit printed in the label (lb/kg, in/cm) and
                       convert the passport value to it.
  L3_clinical_filter   For "conditions/problems" fields, drop facts whose SNOMED
                       semantic tag is (finding) or (situation): social and
                       administrative findings are not medical conditions.

Design provenance (disclosed): these modules were written on 2026-11-02 after
B0 run v1 per-field errors were inspected on all splits. The test split is
therefore not untouched for design purposes; any claim needs replication on a
new cohort or template set. See evidence/forms_arms/README.md.
"""
from __future__ import annotations

import re

from . import b0

MODULES = ("L1_evidence_abstain", "L2_unit_validation", "L3_clinical_filter")
NON_CONDITION_TAGS = {"finding", "situation"}
LB_PER_KG = 2.20462
CM_PER_IN = 2.54


def _unit(label: str):
    m = re.search(r"\(([^)]+)\)", label)
    return m.group(1).strip().lower() if m else None


def _conditions(passport):
    out = []
    for f in passport.get("facts", []):
        if f["fact_key"] != "condition.active":
            continue
        v = f.get("value") or {}
        if (v.get("semantic_tag") or "").lower() in NON_CONDITION_TAGS:
            continue
        if v.get("name") and v["name"] not in out:
            out.append(v["name"])
    return b0.LIST_SEP.join(out) if out else "None"


def map_field(label: str, field: dict, passport: dict, modules: frozenset):
    lab = label.lower()
    decision, value = b0.map_field(label, field, passport)
    if "L3_clinical_filter" in modules and ("condition" in lab or "problem" in lab):
        value = _conditions(passport)
    if "L2_unit_validation" in modules and decision == "fill" and value is not None:
        unit = _unit(label)
        if "weight" in lab and unit in ("lb", "lbs", "ib"):
            value = round(float(value) * LB_PER_KG, 1)
        elif "height" in lab and unit in ("in", "inches"):
            value = round(float(value) / CM_PER_IN, 1)
    if "L1_evidence_abstain" in modules and decision == "fill" and value == "None":
        decision, value = "needs_user_input", None
    return decision, value


def make_arm(modules) -> tuple[str, callable]:
    mods = frozenset(modules)
    unknown = mods - set(MODULES)
    if unknown:
        raise ValueError(f"UNKNOWN_MODULE:{sorted(unknown)}")
    name = "B0" if not mods else "B0+" + "+".join(m.split("_")[0] for m in MODULES if m in mods)

    def fill_plan(html: str, passport: dict) -> dict:
        answers = []
        for f in b0.inspect_form(html):
            decision, value = map_field(f["label"], f, passport, mods)
            if decision == "fill" and value in (None, ""):
                decision, value = "needs_user_input", None
            answers.append({"field_key": f["name"], "decision": decision, "value": value,
                            "evidence_fact_ids": [], "reason": name})
        return {"arm": name, "answers": answers}

    return name, fill_plan
