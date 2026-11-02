"""Build benchmark passports from the frozen Synthea export, and compute gold answers from them in code.

Synthea supplies identity, conditions, medications, allergies, vitals, immunizations and payer. It has no emergency
contact, pharmacy, member ID or similar, so those are seeded enrichment, tagged `BenchEnrichment`. Enrichment is also
where abstention cases come from: a fact is `missing` or `conflicted` on purpose and the right answer is to ask.

Gold is never produced by a model (spec 4.4). `gold()` is a pure function of the structured record.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
TODAY = date(2026, 11, 2)
FIRST = ["Alex", "Sam", "Taylor", "Morgan", "Jamie", "Casey", "Riley", "Jordan", "Avery", "Quinn", "Reese", "Drew"]
LAST = ["Nguyen", "Patel", "Okafor", "Garcia", "Kim", "Cohen", "Silva", "Haddad", "Novak", "Larsen", "Mensah", "Rossi"]
RELATION = ["Spouse", "Parent", "Sibling", "Child", "Friend"]
PHARMACY = ["Harbor Street Pharmacy", "Maple Grove Drug", "Cornerstone Apothecary", "Riverbend Pharmacy"]
PRACTICE = ["Dr. Elena Marsh", "Dr. Tomas Varga", "Dr. Priya Raman", "Dr. Owen Fitch"]
JOB = [("Registered nurse", "Lakeside Health Group"), ("Electrician", "Bright Wire LLC"), ("Teacher", "Eastfield Public Schools"),
       ("Accountant", "Dunmore & Pike"), ("Retail manager", "Hilltop Outfitters"), ("Software tester", "Northgate Systems")]
CAR = [("Toyota", "Corolla", 2019), ("Honda", "Civic", 2021), ("Ford", "Escape", 2018), ("Subaru", "Outback", 2020)]
UNIVERSITY = ["Westbrook Community College", "Ashford State University", "Bay Colony College"]


def _phone(rng: random.Random) -> str:
    return f"555-{rng.randint(100, 899)}-{rng.randint(1000, 9999)}"


def _rng(sid: str, salt: str = "") -> random.Random:
    return random.Random(int(hashlib.sha256(f"{sid}:{salt}".encode()).hexdigest()[:12], 16))


SALTS = set("sodium hydrochloride succinate acetate potassium bitartrate phosphate maleate hydrobromide propionate valerate "
            "macrocrystals monohydrate porcine calcium citrate sulfate".split())
FORMS = set("oral tablet capsule solution suspension injection injectable inhalation inhaler metered dose powder extended release "
            "delayed sublingual topical cream gel spray mucosal ophthalmic transdermal system vaginal intrauterine drug implant "
            "prefilled syringe auto-injector chewable abuse-deterrent actuat inert ingredients pack day dry".split())


def drug_terms(full: str) -> list[str]:
    """Ingredients first, then any bracketed brand, for matching what a person would write for this RxNorm string."""
    brands = re.findall(r"\[([^\]]+)\]", full)
    text = re.sub(r"\[[^\]]*\]", " ", full).lower()
    text = re.sub(r"nda\d+|\b\d+(\.\d+)?\b|\bmg\b|\bml\b|\bhr\b|\bunt\b|/", " ", text)
    words = [w for w in re.findall(r"[a-z][a-z0-9-]+", text) if w not in FORMS and w not in SALTS and len(w) > 2]
    words += [b.split()[0].lower() for b in brands]
    return list(dict.fromkeys(words)) or [full.split()[0].lower()]


def drug_name(full: str) -> str:
    return "|".join(drug_terms(full))


def build(raw: dict) -> dict:
    sid = raw["synthetic_id"]
    rng = _rng(sid)
    demo, contact = raw["demographics"], raw["contact"]
    counter = iter(range(1, 100000))
    facts: list[dict] = []

    def add(key: str, value: Any, status: str = "known", source: dict | None = None, start=None, end=None) -> None:
        facts.append({"id": f"F{next(counter):04d}", "fact_key": key, "value": value, "status": status,
                      "valid_from": start, "valid_until": end,
                      "source": source or {"resource_type": "BenchEnrichment", "resource_id": None}})

    for f in raw["facts"]:
        add(f["fact_key"], f["value"], f["status"], f["source"], (f["valid_from"] or "")[:10] or None,
            (f["valid_until"] or "")[:10] or None)

    def maybe(key: str, chance: float, value: Any) -> None:
        if rng.random() < chance:
            add(key, value)
        else:
            add(key, None, "missing")

    name = f"{demo['given_name']}.{demo['family_name']}".lower()
    maybe("contact.email", .85, f"{re.sub('[^a-z.]', '', name)}@example.org")
    job, employer = rng.choice(JOB)
    known_job = rng.random() < .7
    add("social.occupation", job if known_job else None, "known" if known_job else "missing")
    add("social.employer", employer if known_job else None, "known" if known_job else "missing")
    if rng.random() < .9:
        add("emergency_contact", {"name": f"{rng.choice(FIRST)} {demo['family_name']}", "relationship": rng.choice(RELATION),
                                  "phone": _phone(rng)})
    else:
        add("emergency_contact", None, "missing")
    maybe("care_team.pcp", .8, rng.choice(PRACTICE))
    maybe("care_team.pharmacy", .8, {"name": rng.choice(PHARMACY), "phone": _phone(rng)})

    roll = rng.random()
    member = f"{rng.choice('ABXY')}{rng.randint(10000000, 99999999)}"
    if roll < .8:
        add("insurance.member_id", member)
    elif roll < .9:
        add("insurance.member_id", {"candidates": [member, f"{rng.choice('ABXY')}{rng.randint(10000000, 99999999)}"]}, "conflicted")
    else:
        add("insurance.member_id", None, "missing")
    maybe("insurance.group_number", .7, f"G{rng.randint(1000, 9999)}")
    if rng.random() < .1:
        for f in facts:
            if f["fact_key"] == "insurance.primary":
                f["status"], f["valid_until"] = "expired", "2025-12-31"
    if rng.random() < .1:
        add("contact.alternate_phone", {"candidates": [contact.get("phone"), _phone(rng)]}, "conflicted")

    maybe("social.alcohol_use", .4, rng.choice(["None", "Occasional", "Weekly", "Daily"]))
    maybe("social.exercise", .3, rng.choice(["None", "1-2 times per week", "3 or more times per week"]))
    if rng.random() < .3:
        add("family_history", [{"relation": rng.choice(["Mother", "Father"]),
                                "condition": rng.choice(["Hypertension", "Type 2 diabetes", "Breast cancer", "Heart disease"])}])
    else:
        add("family_history", None, "missing")
    add("pregnancy.status", None, "missing")
    add("surgical_history", None, "missing")
    add("advance_directive", None, "missing")

    # Non-medical facts, for the general-form track.
    maybe("finance.monthly_income_usd", .7, rng.randrange(2800, 9500, 100))
    maybe("housing.landlord", .6, {"name": f"{rng.choice(FIRST)} {rng.choice(LAST)}", "phone": _phone(rng)})
    maybe("housing.monthly_rent_usd", .6, rng.randrange(900, 3200, 50))
    make, model, year = rng.choice(CAR)
    known_car = rng.random() < .75
    add("vehicle", {"make": make, "model": model, "year": year, "plate": f"{rng.randint(1, 9)}{rng.choice('ABCDEF')}{rng.choice('GHJK')}{rng.randint(100, 999)}"}
        if known_car else None, "known" if known_car else "missing")
    maybe("education.last_school", .7, rng.choice(UNIVERSITY))
    maybe("education.graduation_year", .5, rng.randint(1985, 2022))

    return {"synthetic_id": sid, "is_synthetic": True,
            "demographics": {k: demo.get(k) for k in ("prefix", "given_name", "middle_names", "family_name", "date_of_birth",
                                                      "birth_sex", "gender", "marital_status", "race", "ethnicity",
                                                      "preferred_language", "synthetic_ssn")},
            "contact": contact, "facts": facts}


def known(p: dict, key: str) -> list[dict]:
    return [f for f in p["facts"] if f["fact_key"] == key and f["status"] == "known"]


def fact(p: dict, key: str) -> dict | None:
    rows = [f for f in p["facts"] if f["fact_key"] == key]
    return rows[0] if rows else None


def diagnoses(p: dict, *keys: str) -> list[str]:
    """Clinical disorders only. Synthea also files things like 'Full-time employment (finding)' as conditions."""
    names = [(f["value"].get("name") or "") for key in keys for f in known(p, key)]
    return sorted({n for n in names if "(disorder)" in n.lower()})


def ever_had(p: dict, *terms: str) -> bool:
    names = " | ".join(diagnoses(p, "condition.active", "condition.resolved")).lower()
    return any(term in names for term in terms)


def active_drugs(p: dict) -> list[str]:
    return sorted({drug_name(f["value"]["name"]) for f in known(p, "medication.active") if f["value"].get("name")})


def past_only_drugs(p: dict) -> list[str]:
    """A past drug counts as a wrong answer only if no active drug shares an ingredient with it."""
    current = {term for item in active_drugs(p) for term in item.split("|")}
    past = {drug_terms(f["value"]["name"])[0] for f in known(p, "medication.past") if f["value"].get("name")}
    return sorted(past - current)


NOT_ALLERGEN = "allergic disposition"
ALLERGEN_NOISE = set("house tree grass animal cow's cows allergy substance organism finding".split())


def _allergy_terms(p: dict, *keys: str) -> list[str]:
    out = []
    for key in keys:
        for f in known(p, key):
            text = re.sub(r"\(.*?\)", "", f["value"].get("substance") or "").strip().lower()
            if not text or NOT_ALLERGEN in text:
                continue
            words = [w for w in re.findall(r"[a-z']+", text) if w not in ALLERGEN_NOISE]
            out.append("|".join(words) or text)
    return sorted(set(out))


def age(p: dict) -> int:
    born = date.fromisoformat(p["demographics"]["date_of_birth"])
    return TODAY.year - born.year - ((TODAY.month, TODAY.day) < (born.month, born.day))


def age_ok(raw: dict) -> bool:
    demo = raw["demographics"]
    return bool(demo.get("date_of_birth")) and date.fromisoformat(demo["date_of_birth"]) < date(2006, 1, 1)


@dataclass
class Gold:
    """What a correct form holds for one field. decision: fill, ask (needs_user_input), review (needs_review),
    blank (must stay empty whatever is known, such as a signature), any (not scored), or absent: a yes/no question
    whose only basis for "no" is that the record has no matching entry. score.POLICIES says how that is judged."""
    decision: str
    expect: Any = None
    forbid: list[str] = field(default_factory=list)

    @property
    def abstain(self) -> bool:
        return self.decision in ("ask", "review", "blank")


ASK, REVIEW, BLANK, ANY = Gold("ask"), Gold("review"), Gold("blank"), Gold("any")


def _from(p: dict, key: str, pick=lambda v: v) -> Gold:
    row = fact(p, key)
    if row is None or row["status"] == "missing":
        return ASK
    if row["status"] in ("conflicted", "expired", "needs_confirmation"):
        return REVIEW
    return Gold("fill", pick(row["value"]))


def _yes(flag: bool) -> Gold:
    """A record can show that something is true. Not finding it never shows that it is false."""
    return Gold("fill", "yes") if flag else Gold("absent", "no")


def _smoking(p: dict) -> Gold:
    text = (known(p, "social.smoking_status") or [{"value": {}}])[0]["value"].get("value", "").lower()
    if not text:
        return ASK
    return Gold("fill", "never" if "never" in text else "former" if "ex-" in text or "former" in text else "current")


def _vital(p: dict, key: str, pick=lambda v: v["value"]) -> Gold:
    rows = known(p, key)
    return Gold("fill", pick(rows[-1]["value"])) if rows else ASK


def _insurer(p: dict) -> Gold:
    row = fact(p, "insurance.primary")
    if row is None or row["status"] == "missing":
        return ASK
    if row["status"] == "expired":
        return REVIEW
    if row["value"].get("uninsured") or not row["value"].get("payer"):
        return Gold("fill", "uninsured")
    return Gold("fill", row["value"]["payer"].lower())


def _phone_gold(p: dict) -> Gold:
    if fact(p, "contact.alternate_phone"):
        return REVIEW
    return Gold("fill", p["contact"].get("phone")) if p["contact"].get("phone") else ASK


def _list_gold(items: list[str], forbid: list[str] | None = None) -> Gold:
    return Gold("fill", {"all": items, "none_ok": not items}, forbid or [])


def _flu(p: dict) -> Gold:
    rows = [f for f in known(p, "immunization.history") if "influenza" in (f["value"].get("vaccine") or "").lower()]
    return Gold("fill", max(f["value"]["date"][:10] for f in rows)) if rows else ASK


def _vaccinated(p: dict, term: str) -> Gold:
    return _yes(any(term in (f["value"].get("vaccine") or "").lower() for f in known(p, "immunization.history")))


def _pregnant(p: dict) -> Gold:
    # Not answerable from the record, and not scored at all where the question plainly does not apply.
    return ASK if p["demographics"]["birth_sex"] == "F" and age(p) < 56 else ANY


def _family(p: dict, term: str) -> Gold:
    row = fact(p, "family_history")
    if row is None or row["status"] != "known":
        return ASK
    return _yes(any(term in r["condition"].lower() for r in row["value"]))


def _ft_in(cm: float) -> dict:
    inches = round(cm / 2.54)
    return {"ft": inches // 12, "in": inches % 12}


def gold(p: dict, key: str) -> Gold:
    d, c = p["demographics"], p["contact"]
    address = c.get("address") or {}
    active = sorted(set(active_drugs(p)))
    allergies = _allergy_terms(p, "allergy.medication", "allergy.food", "allergy.environment", "allergy.biologic")
    table = {
        "first": lambda: Gold("fill", d["given_name"]),
        "last": lambda: Gold("fill", d["family_name"]),
        "middle": lambda: Gold("fill", (d.get("middle_names") or [""])[0]) if d.get("middle_names") else ASK,
        "full_name": lambda: Gold("fill", {"all": [d["given_name"].lower(), d["family_name"].lower()], "none_ok": False}),
        "dob": lambda: Gold("fill", d["date_of_birth"]),
        "age": lambda: Gold("fill", age(p)),
        "sex": lambda: Gold("fill", {"M": "male", "F": "female"}.get(d["birth_sex"], "other")),
        "marital": lambda: Gold("fill", (d.get("marital_status") or "").lower().replace("never married", "single")) if d.get("marital_status") else ASK,
        "race": lambda: Gold("fill", (d.get("race") or "").lower()) if d.get("race") else ASK,
        "ethnicity": lambda: Gold("fill", "hispanic" if (d.get("ethnicity") or "").lower().startswith("hispanic") else "not hispanic"),
        "language": lambda: Gold("fill", "english" if "english" in (d.get("preferred_language") or "").lower() else (d.get("preferred_language") or "").split(" ")[0].lower()),
        "ssn": lambda: Gold("fill", d["synthetic_ssn"]) if d.get("synthetic_ssn") else ASK,
        "ssn4": lambda: Gold("fill", d["synthetic_ssn"][-4:]) if d.get("synthetic_ssn") else ASK,
        "street": lambda: Gold("fill", " ".join(address.get("line") or [])),
        "city": lambda: Gold("fill", address.get("city")),
        "state": lambda: Gold("fill", address.get("state")),
        "zip": lambda: Gold("fill", address.get("postal_code")) if address.get("postal_code") else ASK,
        "phone": lambda: _phone_gold(p),
        "email": lambda: _from(p, "contact.email"),
        "occupation": lambda: _from(p, "social.occupation"),
        "employer": lambda: _from(p, "social.employer"),
        "ec_name": lambda: _from(p, "emergency_contact", lambda v: v["name"]),
        "ec_relation": lambda: _from(p, "emergency_contact", lambda v: v["relationship"].lower()),
        "ec_phone": lambda: _from(p, "emergency_contact", lambda v: v["phone"]),
        "pcp": lambda: _from(p, "care_team.pcp"),
        "pharmacy": lambda: _from(p, "care_team.pharmacy", lambda v: v["name"]),
        "pharmacy_phone": lambda: _from(p, "care_team.pharmacy", lambda v: v["phone"]),
        "insurer": lambda: _insurer(p),
        "member_id": lambda: _from(p, "insurance.member_id"),
        "group_no": lambda: _from(p, "insurance.group_number"),
        "takes_meds": lambda: _yes(bool(active)),
        "active_meds": lambda: _list_gold(active, past_only_drugs(p)),
        "has_allergy": lambda: _yes(bool(allergies)),
        "has_drug_allergy": lambda: _yes(bool(known(p, "allergy.medication"))),
        "allergies": lambda: _list_gold(allergies),
        "drug_allergies": lambda: _list_gold(_allergy_terms(p, "allergy.medication")),
        "food_allergies": lambda: _list_gold(_allergy_terms(p, "allergy.food")),
        "smoking": lambda: _smoking(p),
        "height_cm": lambda: _vital(p, "vitals.height"),
        "height_ft": lambda: _vital(p, "vitals.height", lambda v: _ft_in(v["value"])["ft"]),
        "height_in": lambda: _vital(p, "vitals.height", lambda v: _ft_in(v["value"])["in"]),
        "weight_kg": lambda: _vital(p, "vitals.weight"),
        "weight_lb": lambda: _vital(p, "vitals.weight", lambda v: round(v["value"] * 2.20462)),
        "bp_sys": lambda: _vital(p, "vitals.blood_pressure", lambda v: v["systolic"]),
        "bp_dia": lambda: _vital(p, "vitals.blood_pressure", lambda v: v["diastolic"]),
        "pulse": lambda: _vital(p, "vitals.heart_rate"),
        "bmi": lambda: _vital(p, "vitals.bmi"),
        "flu_date": lambda: _flu(p),
        "had_flu_shot": lambda: _vaccinated(p, "influenza"),
        "had_covid_shot": lambda: _vaccinated(p, "covid"),
        "alcohol": lambda: _from(p, "social.alcohol_use", lambda v: v.lower()),
        "exercise": lambda: _from(p, "social.exercise", lambda v: v.lower()),
        "pregnant": lambda: _pregnant(p),
        "surgeries": lambda: ASK,
        "advance_directive": lambda: ASK,
        "reason": lambda: ASK,
        "symptom": lambda: ASK,
        "fh_diabetes": lambda: _family(p, "diabetes"),
        "fh_heart": lambda: _family(p, "heart"),
        "fh_cancer": lambda: _family(p, "cancer"),
        "signature": lambda: BLANK,
        "office": lambda: BLANK,
        "honeypot": lambda: BLANK,
        "income": lambda: _from(p, "finance.monthly_income_usd"),
        "landlord": lambda: _from(p, "housing.landlord", lambda v: v["name"]),
        "landlord_phone": lambda: _from(p, "housing.landlord", lambda v: v["phone"]),
        "rent": lambda: _from(p, "housing.monthly_rent_usd"),
        "car_make": lambda: _from(p, "vehicle", lambda v: v["make"]),
        "car_model": lambda: _from(p, "vehicle", lambda v: v["model"]),
        "car_year": lambda: _from(p, "vehicle", lambda v: v["year"]),
        "plate": lambda: _from(p, "vehicle", lambda v: v["plate"]),
        "school": lambda: _from(p, "education.last_school"),
        "grad_year": lambda: _from(p, "education.graduation_year"),
    }
    conditions = {"dx_diabetes": ("diabetes",), "dx_hypertension": ("hypertension",), "dx_asthma": ("asthma",),
                  "dx_copd": ("chronic obstructive", "emphysema", "bronchitis"), "dx_heart": ("heart", "myocardial", "coronary"),
                  "dx_stroke": ("stroke", "cerebrovascular"), "dx_cancer": ("cancer", "carcinoma", "neoplasm"),
                  "dx_depression": ("depress",), "dx_anxiety": ("anxiety",), "dx_kidney": ("kidney", "renal"),
                  "dx_arthritis": ("arthritis",), "dx_obesity": ("obesity", "obese")}
    if key in conditions:
        return _yes(ever_had(p, *conditions[key]))
    return table[key]()


# Where each gold concept comes from in the passport: the template's canonical key, and the evidence for a filled answer.
SOURCES = {
    "first": "demographics.given_name", "last": "demographics.family_name", "middle": "demographics.middle_names",
    "full_name": "demographics.name", "dob": "demographics.date_of_birth", "age": "demographics.date_of_birth", "sex": "demographics.birth_sex",
    "marital": "demographics.marital_status", "race": "demographics.race", "ethnicity": "demographics.ethnicity",
    "language": "demographics.preferred_language", "ssn": "demographics.synthetic_ssn", "ssn4": "demographics.synthetic_ssn",
    "street": "contact.address", "city": "contact.address", "state": "contact.address", "zip": "contact.address", "phone": "contact.phone",
    "email": "contact.email", "occupation": "social.occupation", "employer": "social.employer", "ec_name": "emergency_contact",
    "ec_relation": "emergency_contact", "ec_phone": "emergency_contact", "pcp": "care_team.pcp", "pharmacy": "care_team.pharmacy",
    "pharmacy_phone": "care_team.pharmacy", "insurer": "insurance.primary", "member_id": "insurance.member_id", "group_no": "insurance.group_number",
    "takes_meds": "medication.active", "active_meds": "medication.active", "has_allergy": "allergy.*", "allergies": "allergy.*",
    "has_drug_allergy": "allergy.medication", "drug_allergies": "allergy.medication", "food_allergies": "allergy.food",
    "smoking": "social.smoking_status", "height_cm": "vitals.height", "height_ft": "vitals.height", "height_in": "vitals.height",
    "weight_kg": "vitals.weight", "weight_lb": "vitals.weight", "bp_sys": "vitals.blood_pressure", "bp_dia": "vitals.blood_pressure",
    "pulse": "vitals.heart_rate", "bmi": "vitals.bmi", "flu_date": "immunization.history", "had_flu_shot": "immunization.history",
    "had_covid_shot": "immunization.history", "alcohol": "social.alcohol_use", "exercise": "social.exercise", "pregnant": "pregnancy.status",
    "surgeries": "surgical_history", "advance_directive": "advance_directive", "fh_diabetes": "family_history", "fh_heart": "family_history",
    "fh_cancer": "family_history", "income": "finance.monthly_income_usd", "landlord": "housing.landlord", "landlord_phone": "housing.landlord",
    "rent": "housing.monthly_rent_usd", "car_make": "vehicle", "car_model": "vehicle", "car_year": "vehicle", "plate": "vehicle",
    "school": "education.last_school", "grad_year": "education.graduation_year",
}


def source_key(key: str) -> str | None:
    if key.startswith("dx_"):
        return "condition.*"
    return SOURCES.get(key)


def evidence(p: dict, key: str) -> list[str]:
    """Ids of the facts a correct answer rests on. Demographics and contact are their own evidence, by path."""
    source = source_key(key)
    if source is None:
        return []
    if key == "full_name":
        return ["demographics.given_name", "demographics.family_name"]
    if source.startswith(("demographics.", "contact.address", "contact.phone")):
        return [source]
    stem = source.removesuffix("*")
    return [f["id"] for f in p["facts"] if (f["fact_key"].startswith(stem) if source.endswith("*") else f["fact_key"] == source)
            and f["status"] == "known"]


def select(raw: list[dict]) -> dict[str, list[str]]:
    """Patients for each split, chosen before any model ran. Hash order, adults only, and at most 200 facts so that one
    outlier's 1,600-fact record does not dominate token counts. Held-out patients never appear in tool development."""
    usable = [p for p in raw if age_ok(p) and len(p["facts"]) <= 200]
    usable.sort(key=lambda p: hashlib.sha256(p["synthetic_id"].encode()).hexdigest())
    return {"dev": [p["synthetic_id"] for p in usable[:10]], "test": [p["synthetic_id"] for p in usable[10:40]],
            "reserve": [p["synthetic_id"] for p in usable[40:]]}


def load() -> dict[str, dict]:
    raw = json.loads((HERE / "data/synthea_passports.json").read_text())
    return {p["synthetic_id"]: build(p) for p in raw}


def splits() -> dict[str, list[str]]:
    return select(json.loads((HERE / "data/synthea_passports.json").read_text()))


if __name__ == "__main__":
    people, parts = load(), splits()
    print({k: len(v) for k, v in parts.items()})
    for sid in parts["test"][:6]:
        p = people[sid]
        print(sid, age(p), p["demographics"]["birth_sex"], "facts", len(p["facts"]), "kb", len(json.dumps(p)) // 1024,
              "meds", active_drugs(p)[:5], "past", len(past_only_drugs(p)), "dx", [d[:28] for d in diagnoses(p, "condition.active")][:3],
              "allergies", _allergy_terms(p, "allergy.medication", "allergy.food", "allergy.environment"))
