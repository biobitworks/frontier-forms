"""retrieve_passport_facts: flatten a passport into citable facts and pick only those a set of questions needs."""
from __future__ import annotations

import json
import re

ROUTES = [
    (r"medic|medicine|drug|prescri|regimen|pills?\b", ["medication.active"]),
    (r"(medic|medicine|drug).*(past|stopped|previous|former|ever)", ["medication.past"]),
    (r"allerg|reaction", ["allergy."]),
    (r"diabet|blood pressure|hypertens|asthma|heart|cardiac|coronary|cancer|malignan|kidney|renal|depress|anxiety|stroke|cva|copd|emphysema|bronchitis|arthritis|obes|problem|diagnos|condition|told you have|medical history",
     ["condition."]),
    (r"vaccin|immuni|flu\b|influenza|covid|\bshot\b", ["immunization."]),
    (r"height|weight|stature|\bmass\b|\bbmi\b|body mass|pulse|heart rate|blood pressure|systolic|diastolic", ["vitals."]),
    (r"insur|health plan|payer|carrier|member|policy|group|subscriber|coverage|id number on card", ["insurance."]),
    (r"emergency|next of kin|notify|relationship|relation\b|their phone|their relat|call in an", ["emergency_contact"]),
    (r"e-?mail|phone|cell\b|telephone|mobile", ["contact."]),
    (r"pharmac|prescriptions", ["care_team.pharmacy"]),
    (r"doctor|physician|\bpcp\b|provider", ["care_team.pcp"]),
    (r"smok|tobacco|cigarette", ["social.smoking_status"]),
    (r"alcohol|drink", ["social.alcohol_use"]),
    (r"exercise", ["social.exercise"]),
    (r"occupation|employ|job|work|trade", ["social.occupation", "social.employer"]),
    (r"pregnan", ["pregnancy."]),
    (r"surg|operation", ["surgical_history"]),
    (r"directive", ["advance_directive"]),
    (r"family|relative|parent", ["family_history"]),
    (r"landlord|rent", ["housing."]),
    (r"income|salary|earn", ["finance."]),
    (r"vehicle|car\b|plate|model|make|manufacturer", ["vehicle"]),
    (r"school|college|education|graduat|completed", ["education."]),
]
HISTORY = ("medication.past", "condition.resolved", "immunization.")
DROP = {"code", "reactions", "criticality", "observed_at", "authored_on", "as_needed", "dose_quantity", "as_of"}


def compact(value):
    if isinstance(value, dict):
        return {k: v for k, v in value.items() if k not in DROP and v not in (None, [], "")}
    return value


class Passport:
    def __init__(self, data: dict):
        self.data = data
        self.base = {}
        for prefix in ("demographics", "contact"):
            self._flatten(prefix, data.get(prefix) or {})
        self.facts = {f["id"]: f for f in data["facts"]}

    def _flatten(self, prefix: str, value) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                self._flatten(f"{prefix}.{key}", item)
        elif isinstance(value, list):
            self.base[prefix] = ", ".join(map(str, value))
        elif value not in (None, ""):
            self.base[prefix] = value

    def retrieve(self, questions: list[str]) -> str:
        """The record lines for these questions. A question no route recognises gets every current fact."""
        keys, unrouted = set(), False
        for question in questions:
            hits = [route for pattern, route in ROUTES if re.search(pattern, question, re.I)]
            keys.update(k for route in hits for k in route)
            identity = re.search(r"name|birth|born|\bage\b|sex|gender|marital|relationship status|race|ethnic|hispanic|language|ssn|social security|address|street|city|town|state|zip|postal|phone|cell|telephone|email|e-mail|mobile", question, re.I)
            unrouted = unrouted or not (hits or identity)
        lines = [f"{path} = {value}" for path, value in self.base.items()]
        for fact in self.data["facts"]:
            key = fact["fact_key"]
            wanted = key.startswith(tuple(keys)) if keys else False
            if wanted or (unrouted and not key.startswith(HISTORY)):
                dates = "".join(f" {name}={fact[name]}" for name in ("valid_until",) if fact.get(name))
                lines.append(f"{fact['id']} {key} [{fact['status']}]{dates} {json.dumps(compact(fact['value']), default=str)}")
        return "\n".join(lines)

    def cited(self, ref: str) -> tuple[str, str] | None:
        """(status, text) for a citation, or None if it does not exist."""
        ref = str(ref).strip()
        if ref in self.facts:
            fact = self.facts[ref]
            return fact["status"], json.dumps(fact["value"], default=str)
        matches = [str(v) for path, v in self.base.items() if path == ref or path.startswith(f"{ref}.")]
        return ("known", " ".join(matches)) if matches else None
