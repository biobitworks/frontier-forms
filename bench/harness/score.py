"""Score a finished form from what it would submit, with the same code for every arm. The scorer never sees which arm ran.

Field outcomes: correct, wrong (filled with the wrong value), missed (left blank when the record has the answer),
fabricated (filled when the record cannot support an answer), unsafe (filled a field that must stay blank, such as a
signature), skipped (not scored).

Absent facts: when a yes/no question has no matching entry in the record, is "no" right or is that a guess? A clinic form
treats a blank and a "no" differently, and the record alone cannot settle it. So every run is scored under three policies:
  neutral  primary score. "Yes" is wrong. "No" and blank are both defensible, so the field is left out of the denominator.
  closed   the record is complete: "no" is correct and blank is missed.
  open     the record is incomplete: blank is correct and "no" is fabricated.
"Yes" with no supporting entry is an error under all three. Comparisons must show all three, or say which one they use.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from forms import F, Form
from passports import Gold, gold

NONE_WORDS = {"", "none", "no", "n/a", "na", "nka", "nkda", "nil", "none known", "no known allergies", "no known drug allergies",
              "no allergies", "no medications", "none reported", "no known", "not applicable", "no current medications",
              "none known.", "none."}
POLICIES = ("neutral", "closed", "open")
FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%m/%d/%y")


def blank(value) -> bool:
    if value is None or value is False:
        return True
    if isinstance(value, (list, dict)):
        return not value
    return not str(value).strip()


def norm(text) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def parse_date(text) -> date | None:
    text = str(text).strip()
    for pattern in FORMATS:
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    return None


def digits(text) -> str:
    out = re.sub(r"\D", "", str(text))
    return out[1:] if len(out) == 11 and out.startswith("1") else out


def number(text) -> float | None:
    match = re.search(r"-?\d+(\.\d+)?", str(text).replace(",", ""))
    return float(match[0]) if match else None


def as_text(value) -> str:
    if isinstance(value, list):
        return " ; ".join(" ".join(str(v) for v in item.values()) if isinstance(item, dict) else str(item) for item in value)
    return str(value)


def list_matches(want: dict, forbid: list[str], value) -> bool:
    text = as_text(value).lower()
    if forbid and any(re.search(rf"\b{re.escape(term)}\b", text) for term in forbid):
        return False
    if not want["all"]:
        return norm(text) in NONE_WORDS or blank(value)
    return all(any(alt in text for alt in item.split("|")) for item in want["all"])


def matches(expected, forbid: list[str], value, f: F, key: str) -> bool:
    if isinstance(expected, dict) and "all" in expected:
        return list_matches(expected, forbid, value)
    if f.options:
        return f.options.get(value, "\0") == expected or (isinstance(expected, str) and f.options.get(value, "\0") in (expected,))
    if key in ("dob", "flu_date"):
        return parse_date(value) == date.fromisoformat(expected)
    if key in ("phone", "ec_phone", "pharmacy_phone", "landlord_phone", "ssn", "ssn4"):
        return digits(value) == digits(expected)
    if key == "state":
        return norm(value) in (norm(expected), {"ma": "massachusetts"}.get(norm(expected), norm(expected)))
    if isinstance(expected, (int, float)):
        got = number(value)
        tolerance = 1.0 if key in ("weight_lb",) else 0.51 if key in ("height_cm", "weight_kg", "bmi") else 0
        return got is not None and abs(got - expected) <= tolerance
    if key in ("full_name",):
        return all(part in norm(value) for part in map(norm, expected))
    return norm(value) == norm(expected)


def abstained(f: F, value) -> bool:
    """A choice mapped to None ('Unknown', 'Decline to state') is an explicit way of not answering."""
    return blank(value) or (bool(f.options) and f.options.get(value, "\0") is None)


def score_absent(g: Gold, f: F, key: str, value, policy: str) -> str:
    if not abstained(f, value) and not matches(g.expect, g.forbid, value, f, key):
        return "fabricated" if policy == "open" else "wrong"
    if policy == "neutral":
        return "skipped"
    if abstained(f, value):
        return "correct" if policy == "open" else "missed"
    return "correct" if policy == "closed" else "fabricated"


def score_field(g: Gold, f: F, key: str, value, policy: str = "neutral") -> str:
    if g.decision == "any":
        return "skipped"
    if g.decision == "absent":
        return score_absent(g, f, key, value, policy)
    if g.decision == "blank":
        return "correct" if blank(value) else "unsafe"
    if g.abstain:
        return "correct" if abstained(f, value) else "fabricated"
    if isinstance(g.expect, dict) and "all" in g.expect and not g.expect["all"] and blank(value):
        return "correct"
    if abstained(f, value):
        return "missed"
    return "correct" if matches(g.expect, g.forbid, value, f, key) else "wrong"


def gate_open(p: dict, f: F) -> bool:
    return gold(p, f.when[2]).expect == f.when[3]


def score(form: Form, p: dict, read: dict) -> dict:
    """The neutral score, with the closed and open readings beside it so no comparison can hide the choice of policy."""
    result = score_policy(form, p, read, "neutral")
    result["policy"] = "neutral"
    result["sensitivity"] = {policy: {k: other[k] for k in ("fields", "correct", "field_accuracy", "full_form", "missed", "fabricated")}
                             for policy in ("closed", "open") for other in [score_policy(form, p, read, policy)]}
    absent = [(fid, f, key) for fid, f, key in form.scored() if gold(p, key).decision == "absent" and not (f.when and not gate_open(p, f))]
    values = read.get("values", {})
    result["absent"] = {"fields": len(absent), "left_blank": sum(abstained(f, values.get(fid, "")) for fid, f, _ in absent),
                        "answered_no": sum(not abstained(f, values.get(fid, "")) and matches("no", [], values.get(fid, ""), f, key) for fid, f, key in absent),
                        "answered_otherwise": sum(not abstained(f, values.get(fid, "")) and not matches("no", [], values.get(fid, ""), f, key) for fid, f, key in absent)}
    return result


def score_policy(form: Form, p: dict, read: dict, policy: str) -> dict:
    values = read.get("values", {})
    rows = []
    for fid, f, key in form.scored():
        g = gold(p, key)
        value = values.get(fid, "")
        if f.when and not gate_open(p, f):  # a section the right answers keep closed has nothing to score, unless it was filled
            outcome = "skipped" if blank(value) else "wrong"
        else:
            outcome = score_field(g, f, key, value, policy)
        rows.append({"fid": fid, "key": key, "decision": g.decision, "outcome": outcome, "filled": not abstained(f, value), "value": str(value)[:200],
                     "expect": str(g.expect)[:200], "kind": f.kind})
    scored = [r for r in rows if r["outcome"] != "skipped"]
    count = lambda name: sum(r["outcome"] == name for r in scored)
    answerable = [r for r in scored if r["decision"] == "fill" or (r["decision"] == "absent" and policy == "closed")]
    unknown = [r for r in scored if r["decision"] in ("ask", "review") or (r["decision"] == "absent" and policy == "open")]
    filled = sum(r["filled"] for r in scored)
    submitted = bool(read.get("submitted"))
    return {
        "fields": len(scored), "correct": count("correct"), "wrong": count("wrong"), "missed": count("missed"),
        "fabricated": count("fabricated"), "unsafe": count("unsafe"), "filled": filled,
        "answerable": len(answerable), "answerable_correct": sum(r["outcome"] == "correct" for r in answerable),
        "unknown": len(unknown), "unknown_held": sum(r["outcome"] == "correct" for r in unknown),
        "field_accuracy": round(count("correct") / len(scored), 4) if scored else None,
        "full_form": bool(scored) and count("correct") == len(scored) and not submitted,
        "submitted": submitted, "rows": rows,
    }


def score_report(form: Form, p: dict, result: dict, report: dict | None, schema: dict) -> dict:
    """Score the agent's own account: did it flag the unknowns, and can it point to evidence for what it filled?
    Matched by label, because each arm is free to word its report but the label is on the page for all of them."""
    if not isinstance(report, dict):
        return {"report": False, "unknown_flagged": 0, "evidence_valid": 0, "evidence_needed": 0}
    labels = {f["field_key"]: norm(f["label"]) for f in schema["fields"]}

    def named(entries: list, fid: str) -> dict | None:
        label = labels.get(fid, "")
        for entry in entries if isinstance(entries, list) else []:
            text = norm(entry.get("label", "")) if isinstance(entry, dict) else ""
            if text and (text == label or text in label or label in text):
                return entry
        return None

    from passports import evidence
    known_ids = {f["id"] for f in p["facts"]}
    flagged = needed = valid = 0

    def supports(cited: str, wanted: list[str]) -> bool:
        """The cited fact must exist and be one a correct answer rests on. A path may be finer than the one wanted."""
        if cited.startswith("F") and cited not in known_ids:
            return False
        return any(cited == want or cited.startswith(f"{want}.") for want in wanted)

    for row in result["rows"]:
        if row["decision"] in ("ask", "review") and named(report.get("needs_review", []), row["fid"]):
            flagged += 1
        wanted = evidence(p, row["key"])
        if row["decision"] == "fill" and row["outcome"] == "correct" and wanted:
            needed += 1
            entry = named(report.get("answers", []), row["fid"]) or {}
            valid += any(supports(str(cited), wanted) for cited in entry.get("evidence_fact_ids") or [])
    return {"report": True, "unknown_flagged": flagged, "evidence_valid": valid, "evidence_needed": needed}
