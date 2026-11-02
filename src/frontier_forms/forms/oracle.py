"""Independent gold oracle: expected form answers computed from raw FHIR R4.

This module never imports the passport builder or B0. It reads the source
bundle directly and applies the predeclared rules in GOLD_RULES. A rule that
cannot be answered from the record yields decision `needs_user_input`.

Gold rules are clinical/semantic choices fixed before any B0 scores were seen.
Changing one is a new oracle version and requires a new freeze.
"""
from __future__ import annotations

import re

ORACLE_VERSION = "oracle-v1"

GOLD_RULES = {
    "patient.full_name": "official HumanName: first given + family, trailing Synthea digits removed",
    "patient.given_name": "official HumanName first given, digits removed",
    "patient.family_name": "official HumanName family, digits removed",
    "patient.birth_date": "Patient.birthDate verbatim",
    "patient.gender": "Patient.gender verbatim (female/male/other/unknown)",
    "patient.phone": "first telecom with system=phone",
    "patient.address_line": "first address, lines joined with a space",
    "patient.city": "first address city",
    "patient.state": "first address state",
    "patient.postal_code": "first address postalCode",
    "patient.language": "first communication.language text/display",
    "patient.marital_status": "maritalStatus text/display",
    "coverage.primary_payer": "insurer.display of the ExplanationOfBenefit with the latest billablePeriod.start; NO_INSURANCE -> 'Uninsured'",
    "medication.active_list": "set of medication display names from MedicationRequest with status=active; none active -> 'None'",
    "allergy.medication_active_list": "AllergyIntolerance category=medication, clinicalStatus=active; none -> needs_user_input (absence of a record is not 'no known allergies')",
    "allergy.other_active_list": "AllergyIntolerance category in food/environment, clinicalStatus=active; none -> needs_user_input",
    "condition.active_disorder_list": "Condition clinicalStatus=active and SNOMED semantic tag '(disorder)'; findings/situations are not medical conditions; none -> 'None'",
    "vitals.height_cm": "latest final/amended Observation LOINC 8302-2 in cm, 1 decimal",
    "vitals.weight_kg": "latest final/amended Observation LOINC 29463-7 in kg, 1 decimal",
    "vitals.weight_lb": "same weight converted kg*2.20462, 1 decimal",
    "vitals.blood_pressure": "latest LOINC 85354-9 panel, systolic/diastolic as integers 'S/D'",
    "social.smoking_category": "latest LOINC 72166-2: SNOMED 266919005 never; 8517006 former; 449868002/77176002/428041000124106/428071000124103 current; else needs_user_input",
    "pregnancy.current": "not reliably encoded in Synthea output -> needs_user_input",
}

NEVER = {"266919005"}
FORMER = {"8517006"}
CURRENT = {"449868002", "77176002", "428041000124106", "428071000124103"}


def _strip(s):
    return re.sub(r"\d+$", "", s) if s else s


def _text(cc):
    if not cc:
        return None
    if cc.get("text"):
        return cc["text"]
    for c in cc.get("coding") or []:
        if c.get("display"):
            return c["display"]
    return None


def _codes(cc):
    return {c.get("code") for c in (cc or {}).get("coding") or []}


def _status(cc):
    for c in (cc or {}).get("coding") or []:
        if c.get("code"):
            return c["code"]
    return None


def fill(value, kind="scalar"):
    return {"decision": "fill", "value": value, "kind": kind}


def ask():
    return {"decision": "needs_user_input", "value": None, "kind": "scalar"}


class Record:
    def __init__(self, bundle):
        self.by_type = {}
        self.by_ref = {}
        for e in bundle["entry"]:
            r = e["resource"]
            self.by_type.setdefault(r["resourceType"], []).append(r)
            self.by_ref[e.get("fullUrl") or f"urn:uuid:{r['id']}"] = r
            self.by_ref[f"{r['resourceType']}/{r['id']}"] = r
        self.patient = self.by_type["Patient"][0]

    def of(self, t):
        return self.by_type.get(t, [])

    def official_name(self):
        names = self.patient.get("name") or []
        for n in names:
            if n.get("use") == "official":
                return n
        return names[0] if names else {}

    def latest_obs(self, loinc):
        best = None
        for o in self.of("Observation"):
            if o.get("status") not in ("final", "amended") or loinc not in _codes(o.get("code")):
                continue
            t = o.get("effectiveDateTime") or ""
            if best is None or t > (best.get("effectiveDateTime") or ""):
                best = o
        return best


def gold_value(rec: Record, key: str) -> dict:
    p = rec.patient
    if key in ("patient.full_name", "patient.given_name", "patient.family_name"):
        n = rec.official_name()
        given = _strip((n.get("given") or [None])[0])
        family = _strip(n.get("family"))
        v = {"patient.full_name": " ".join(x for x in (given, family) if x),
             "patient.given_name": given, "patient.family_name": family}[key]
        return fill(v) if v else ask()
    if key == "patient.birth_date":
        return fill(p["birthDate"]) if p.get("birthDate") else ask()
    if key == "patient.gender":
        return fill(p["gender"]) if p.get("gender") else ask()
    if key == "patient.phone":
        for t in p.get("telecom") or []:
            if t.get("system") == "phone" and t.get("value"):
                return fill(t["value"])
        return ask()
    if key in ("patient.address_line", "patient.city", "patient.state", "patient.postal_code"):
        a = (p.get("address") or [None])[0]
        if not a:
            return ask()
        v = {"patient.address_line": " ".join(a.get("line") or []) or None,
             "patient.city": a.get("city"), "patient.state": a.get("state"),
             "patient.postal_code": a.get("postalCode")}[key]
        return fill(v) if v else ask()
    if key == "patient.language":
        comm = (p.get("communication") or [None])[0]
        v = _text(comm.get("language")) if comm else None
        return fill(v) if v else ask()
    if key == "patient.marital_status":
        v = _text(p.get("maritalStatus"))
        return fill(v) if v else ask()
    if key == "coverage.primary_payer":
        eobs = rec.of("ExplanationOfBenefit")
        if not eobs:
            return ask()
        latest = max(eobs, key=lambda e: ((e.get("billablePeriod") or {}).get("start") or e.get("created") or "", e["id"]))
        payer = (latest.get("insurer") or {}).get("display")
        if not payer:
            return ask()
        return fill("Uninsured" if payer == "NO_INSURANCE" else payer)
    if key == "medication.active_list":
        names = set()
        for m in rec.of("MedicationRequest"):
            if m.get("status") != "active":
                continue
            cc = m.get("medicationCodeableConcept")
            if cc is None:
                ref = (m.get("medicationReference") or {}).get("reference")
                med = rec.by_ref.get(ref) if ref else None
                cc = med.get("code") if med else None
            t = _text(cc)
            if t:
                names.add(t)
        return fill(sorted(names), "list") if names else fill("None")
    if key in ("allergy.medication_active_list", "allergy.other_active_list"):
        cats = {"medication"} if key == "allergy.medication_active_list" else {"food", "environment"}
        subs = set()
        for a in rec.of("AllergyIntolerance"):
            if not cats & set(a.get("category") or []):
                continue
            if _status(a.get("clinicalStatus")) != "active":
                continue
            t = _text(a.get("code"))
            if t:
                subs.add(t)
        return fill(sorted(subs), "list") if subs else ask()
    if key == "condition.active_disorder_list":
        names = set()
        for c in rec.of("Condition"):
            if _status(c.get("clinicalStatus")) != "active":
                continue
            t = _text(c.get("code")) or ""
            if re.search(r"\(disorder\)\s*$", t):
                names.add(t)
        return fill(sorted(names), "list") if names else fill("None")
    if key in ("vitals.height_cm", "vitals.weight_kg", "vitals.weight_lb"):
        o = rec.latest_obs("8302-2" if key == "vitals.height_cm" else "29463-7")
        q = (o or {}).get("valueQuantity") or {}
        if q.get("value") is None:
            return ask()
        unit = q.get("unit") or q.get("code")
        v = float(q["value"])
        if key == "vitals.height_cm" and unit != "cm":
            return ask()
        if key != "vitals.height_cm" and unit != "kg":
            return ask()
        if key == "vitals.weight_lb":
            v = v * 2.20462
        return fill(round(v, 1), "number")
    if key == "vitals.blood_pressure":
        o = rec.latest_obs("85354-9")
        if not o:
            return ask()
        comp = {}
        for c in o.get("component") or []:
            for code in _codes(c.get("code")):
                comp[code] = (c.get("valueQuantity") or {}).get("value")
        s, d = comp.get("8480-6"), comp.get("8462-4")
        if s is None or d is None:
            return ask()
        return fill(f"{round(float(s))}/{round(float(d))}")
    if key == "social.smoking_category":
        o = rec.latest_obs("72166-2")
        codes = _codes((o or {}).get("valueCodeableConcept"))
        if codes & NEVER:
            return fill("never")
        if codes & FORMER:
            return fill("former")
        if codes & CURRENT:
            return fill("current")
        return ask()
    if key == "pregnancy.current":
        return ask()
    raise KeyError(f"UNDECLARED_CANONICAL_KEY:{key}")


def gold_answers(bundle: dict, template: dict) -> dict:
    rec = Record(bundle)
    return {f["field_key"]: {**gold_value(rec, f["canonical_key"]), "required": bool(f.get("required"))}
            for f in template["fields"]}
