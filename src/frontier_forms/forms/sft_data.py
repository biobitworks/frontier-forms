"""Supervised fine-tuning data for the frontier-forms field mapper (separate lane from Vita DAISY).

One example per (patient, template, field). The model sees what B0 sees: the
field as rendered (label, type, options) and a compact text view of the
teammate passport. The target is the oracle's answer as JSON. Only train-split
patients and train-allowed templates are used for training; validation-split
patients are used for checkpoint selection; test-split patients and the
held-out urgent-care layout are never in training data.
"""
from __future__ import annotations

import json

from .inject import fmt
from .oracle import gold_answers

PROMPT_VERSION = "sft-prompt-v1"
# Historical facts no form field asks for; dropped to keep prompts short.
DROPPED_FACT_KEYS = {"medication.past", "condition.resolved", "immunization.history"}
SYSTEM = ("You fill one field of a medical intake form for a SYNTHETIC patient. "
          "Use only the patient facts given. Reply with JSON: "
          '{"decision": "fill" or "needs_user_input", "value": string or null}.')


def passport_text(p: dict) -> str:
    d, c = p.get("demographics") or {}, p.get("contact") or {}
    a = c.get("address") or {}
    ins = p.get("insurance") or {}
    lines = [
        f"name: {p.get('display_name')} (given {d.get('given_name')}, family {d.get('family_name')})",
        f"birth_date: {d.get('date_of_birth')}; gender: {d.get('gender')}",
        f"phone: {c.get('phone')}; address: {' '.join(a.get('line') or [])}, {a.get('city')}, {a.get('state')} {a.get('postal_code')}",
        f"language: {d.get('preferred_language')}; marital: {d.get('marital_status')}",
        f"insurance: {'uninsured' if ins.get('uninsured') else ins.get('payer')}",
    ]
    groups = {}
    for f in p.get("facts", []):
        groups.setdefault(f["fact_key"], []).append(f)
    for key in sorted(groups):
        if key in DROPPED_FACT_KEYS:
            continue
        for f in groups[key]:
            v = f.get("value") or {}
            if key.startswith("medication."):
                lines.append(f"{key}: {v.get('name')}")
            elif key.startswith("allergy."):
                lines.append(f"{key}: {v.get('substance')} [status {v.get('clinical_status')}]")
            elif key.startswith("condition."):
                lines.append(f"{key}: {v.get('name')}")
            elif key == "vitals.blood_pressure":
                lines.append(f"{key}: {v.get('systolic')}/{v.get('diastolic')} {v.get('unit')} at {v.get('observed_at')}")
            elif key.startswith("vitals.") or key.startswith("social."):
                lines.append(f"{key}: {v.get('value')} {v.get('unit') or ''} at {v.get('observed_at')}".rstrip())
    return "\n".join(lines)


def field_text(f: dict) -> str:
    s = f"Field label: {f['label']}\nField type: {f['type']}"
    if f.get("options"):
        s += f"\nAllowed options: {', '.join(repr(o) for o in f['options'] if o)}"
    return s


def prompt(field: dict, passport_txt: str) -> str:
    return f"{SYSTEM}\n\nPatient facts:\n{passport_txt}\n\n{field_text(field)}\n\nJSON:"


def target(gold: dict) -> str:
    if gold["decision"] != "fill":
        return json.dumps({"decision": "needs_user_input", "value": None})
    return json.dumps({"decision": "fill", "value": fmt(gold)})


def build(members, bundles, templates, passports):
    rows = {"train": [], "validation": []}
    for m in members:
        if m.split not in rows:
            continue
        ptxt = passport_text(passports[m.patient_id])
        for tkey in sorted(templates):
            t = templates[tkey]
            if "train" not in t["splits"]:
                continue  # held-out layouts never enter training or selection
            gold = gold_answers(bundles[m.patient_id], t)
            for f in t["fields"]:
                rows[m.split].append({"patient_id": m.patient_id, "template_key": tkey, "field_key": f["field_key"],
                                      "prompt": prompt(f, ptxt), "completion": " " + target(gold[f["field_key"]])})
    return rows


def parse_completion(text: str):
    """Return (decision, value) from model text; malformed output abstains."""
    t = text.strip()
    end = t.find("}")
    if end != -1:
        t = t[: end + 1]
    try:
        obj = json.loads(t)
    except ValueError:
        return "needs_user_input", None
    if not isinstance(obj, dict):
        return "needs_user_input", None
    if obj.get("decision") == "fill" and obj.get("value") not in (None, ""):
        return "fill", str(obj["value"])
    return "needs_user_input", None
