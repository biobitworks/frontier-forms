"""B0: frozen deterministic autofill baseline (no model, no FCO/FCG, no validation).

B0 is the reference arm every later module is compared against:

    B0 -> + source binding -> + FCO/FCG -> + validation -> full candidate

What B0 does, and nothing more:
  1. inspect_form: parse the served HTML (labels, names, types, options);
  2. map each label to a passport value with the ordered keyword rules below;
  3. emit a structured fill plan (spec section 10.2) with empty evidence ids.

B0 reads only the teammate passport from the local server. It never sees the
template canonical keys, the oracle or the raw FHIR bundle.

FROZEN: this file's SHA-256 is pinned in evidence/forms_b0/B0_FREEZE_V1.json and
checked by tests. Do not edit; supersede with a new arm file and a new freeze.
"""
from __future__ import annotations

from html.parser import HTMLParser

B0_VERSION = "B0-v1"
LIST_SEP = "; "


class _FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.labels = {}
        self.fields = []
        self._label_for = None
        self._label_text = []
        self._select = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "label":
            self._label_for = a.get("for")
            self._label_text = []
        elif tag in ("input", "textarea", "select") and a.get("name"):
            f = {"name": a["name"], "id": a.get("id"), "type": a.get("type", tag) if tag == "input" else tag,
                 "options": []}
            self.fields.append(f)
            if tag == "select":
                self._select = f
        elif tag == "option" and self._select is not None:
            self._select["options"].append(a.get("value", ""))

    def handle_endtag(self, tag):
        if tag == "label" and self._label_for:
            self.labels[self._label_for] = "".join(self._label_text).strip()
            self._label_for = None
        elif tag == "select":
            self._select = None

    def handle_data(self, data):
        if self._label_for is not None:
            self._label_text.append(data)


def inspect_form(html: str) -> list[dict]:
    p = _FormParser()
    p.feed(html)
    return [{**f, "label": p.labels.get(f["id"], "")} for f in p.fields]


def _facts(passport, key):
    return [f for f in passport.get("facts", []) if f["fact_key"] == key]


def _names(passport, keys, field, status=None):
    out = []
    for k in keys:
        for f in _facts(passport, k):
            if status and f.get("status") != status:
                continue
            v = (f.get("value") or {}).get(field)
            if v and v not in out:
                out.append(v)
    return LIST_SEP.join(out) if out else "None"


def _latest_value(passport, key):
    fs = _facts(passport, key)
    return fs[0]["value"] if fs else None


def _pick_option(options, text):
    t = (text or "").lower()
    if "never" in t and "never" in options:
        return "never"
    if ("ex-" in t or "former" in t) and "former" in options:
        return "former"
    if "smok" in t and "current" in options:
        return "current"
    return None


def map_field(label: str, field: dict, passport: dict):
    """Return (decision, value) for one field. Ordered keyword rules, first match wins."""
    lab = label.lower()
    d, c = passport.get("demographics") or {}, passport.get("contact") or {}
    addr = c.get("address") or {}
    if "surname" in lab or "last name" in lab:
        return "fill", d.get("family_name")
    if "first name" in lab or "given name" in lab:
        return "fill", d.get("given_name")
    if "allerg" in lab:
        if "food" in lab or "environment" in lab:
            return "fill", _names(passport, ["allergy.food", "allergy.environment"], "substance", "known")
        return "fill", _names(passport, ["allergy.medication"], "substance", "known")
    if "medication" in lab or "medicine" in lab:
        return "fill", _names(passport, ["medication.active"], "name")
    if "name" in lab:
        return "fill", passport.get("display_name")
    if "birth" in lab or "dob" in lab:
        return "fill", d.get("date_of_birth")
    if lab.strip() in ("sex", "gender") or "sex" in lab.split():
        return "fill", d.get("gender")
    if "phone" in lab:
        return "fill", c.get("phone")
    if "street" in lab or "address" in lab:
        return "fill", " ".join(addr.get("line") or []) or None
    if "city" in lab:
        return "fill", addr.get("city")
    if "state" in lab:
        return "fill", addr.get("state")
    if "zip" in lab or "postal" in lab:
        return "fill", addr.get("postal_code")
    if "language" in lab:
        return "fill", d.get("preferred_language")
    if "marital" in lab:
        return "fill", d.get("marital_status")
    if "insurance" in lab or "carrier" in lab or "payer" in lab:
        ins = passport.get("insurance") or {}
        if ins.get("uninsured"):
            return "fill", "Uninsured"
        return "fill", ins.get("payer")
    if "condition" in lab or "problem" in lab:
        return "fill", _names(passport, ["condition.active"], "name")
    if "height" in lab:
        v = _latest_value(passport, "vitals.height")
        return "fill", (v or {}).get("value")
    if "weight" in lab:
        v = _latest_value(passport, "vitals.weight")
        return "fill", (v or {}).get("value")
    if "blood pressure" in lab:
        v = _latest_value(passport, "vitals.blood_pressure")
        if v and v.get("systolic") is not None and v.get("diastolic") is not None:
            return "fill", f"{round(v['systolic'])}/{round(v['diastolic'])}"
        return "needs_user_input", None
    if "smok" in lab or "tobacco" in lab:
        v = _latest_value(passport, "social.smoking_status")
        opt = _pick_option(field.get("options") or [], (v or {}).get("value"))
        return ("fill", opt) if opt else ("needs_user_input", None)
    return "needs_user_input", None


def fill_plan(html: str, passport: dict) -> dict:
    answers = []
    for f in inspect_form(html):
        decision, value = map_field(f["label"], f, passport)
        if decision == "fill" and value in (None, ""):
            decision, value = "needs_user_input", None
        answers.append({"field_key": f["name"], "decision": decision, "value": value,
                        "evidence_fact_ids": [], "reason": f"{B0_VERSION} keyword rule"})
    return {"arm": B0_VERSION, "answers": answers}
