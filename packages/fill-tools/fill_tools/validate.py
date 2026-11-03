"""validate_fill_plan: nothing reaches the form unless code can check it. Clinical answers need a real, usable source."""
from __future__ import annotations

import re
from datetime import datetime

NEVER = re.compile(r"signature|\bsign here\b|\bsigned?\b|attest|initials|to consent|office use|staff|registrar|\bclerk\b|clinician id|for office", re.I)
DATE_INPUTS = ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y")
WORD = re.compile(r"[a-z][a-z'-]{3,}")


def never_fill(field) -> bool:
    return bool(NEVER.search(field.asked()))


def _date(value: str):
    for pattern in DATE_INPUTS:
        try:
            return datetime.strptime(str(value).strip(), pattern)
        except ValueError:
            pass
    return None


def _option(value, options: list[str]):
    text = str(value).strip().lower()
    exact = [o for o in options if o.lower() == text]
    if exact:
        return exact[0]
    near = [o for o in options if text and (text in o.lower() or o.lower() in text)]
    return near[0] if len(near) == 1 else None


def _grounded(value, sources: list[str]) -> bool:
    """Most of a free-text answer's words must come from the facts it cites. Numbers and formats are checked elsewhere."""
    words = WORD.findall(str(value).lower())
    if not words:
        return True
    text = " ".join(sources).lower()
    return sum(w in text for w in words) / len(words) >= .5


def validate(field, answer: dict | None, passport) -> dict:
    """{decision, value, evidence, reason}, with decision one of fill, needs_user_input, needs_review."""
    def hold(decision: str, reason: str) -> dict:
        return {"decision": decision, "value": None, "evidence": [], "reason": reason}

    if answer is None:
        return hold("needs_review", "the model returned no answer for this field")
    decision, value = answer.get("decision"), answer.get("value")
    if decision != "fill":
        return hold("needs_review" if decision == "needs_review" else "needs_user_input", str(answer.get("reason") or "no supported answer"))
    if value in (None, "", []):
        return hold("needs_user_input", "the model proposed an empty answer")
    cited = {ref: passport.cited(ref) for ref in answer.get("evidence_fact_ids") or []}
    usable = {ref: found for ref, found in cited.items() if found}
    if not usable:
        return hold("needs_review", "no evidence that resolves to this record")
    held = [ref for ref, (status, _) in usable.items() if status != "known"]
    if held and len(held) == len(usable):
        return hold("needs_review", f"cited fact is not current: {', '.join(held)}")
    sources = [text for status, text in usable.values() if status == "known"]
    evidence = [ref for ref, (status, _) in usable.items() if status == "known"]
    if field.type in ("select", "radio", "combobox", "ariaradio"):
        choice = _option(value, field.options)
        if choice is None:
            return hold("needs_review", f"{value!r} is not one of the options")
        value = choice
    elif field.type == "checks":
        chosen = [_option(v, field.options) for v in (value if isinstance(value, list) else [value])]
        if None in chosen:
            return hold("needs_review", "a choice is not one of the options")
        value = chosen
    elif field.type == "date":
        parsed = _date(value)
        if parsed is None:
            return hold("needs_review", f"{value!r} is not a date")
        value = parsed.strftime("%Y-%m-%d")
    elif field.type == "number":
        match = re.search(r"-?\d+(\.\d+)?", str(value))
        if not match:
            return hold("needs_review", f"{value!r} is not a number")
        value = match[0]
    elif field.type == "repeat":
        rows = value if isinstance(value, list) else [value]
        rows = [row if isinstance(row, dict) else {field.columns[0]: row} for row in rows]
        if not all(_grounded(" ".join(map(str, row.values())), sources) for row in rows):
            return hold("needs_review", "a row is not supported by the facts it cites")
        value = rows
    elif field.type in ("text", "textarea"):
        if re.search(r"\d{1,2}/\d{1,2}/\d{4}|mm/dd/yyyy", field.asked() + " " + field.hint, re.I) and _date(value):
            value = _date(value).strftime("%m/%d/%Y")
        if not _grounded(value, sources):
            return hold("needs_review", "the answer is not supported by the facts it cites")
    return {"decision": "fill", "value": value, "evidence": evidence, "reason": answer.get("reason") or ""}
