"""The full harness: inspect, map, validate, apply, verify. It repeats until no new field appears and no step remains."""
from __future__ import annotations

import time

from .apply_form import apply_field, click_next, same
from .inspect_form import inspect_form
from .map_fields import Usage, map_fields
from .passport import Passport
from .validate import never_fill, validate


def fill_form(page, passport: Passport, model: str, prices: dict, *, max_rounds: int = 25) -> dict:
    usage = Usage(prices)
    done: dict[str, dict] = {}
    labels: dict[str, str] = {}
    answers, review, blocked, errors = [], [], [], []
    started = time.perf_counter()
    for _ in range(max_rounds):
        schema = inspect_form(page)
        new = [f for f in schema.fields if f.key not in done]
        if not new:
            if not schema.has_next:
                break
            click_next(page)
            after = inspect_form(page)
            if after.alert or {f.key for f in after.fields} == {f.key for f in schema.fields}:
                errors.append(after.alert or "Next did not advance")
                break
            continue
        for field in new:
            labels[field.key] = field.label or field.question
            done[field.key] = {}
        guarded = [f for f in new if never_fill(f)]
        blocked += [{"label": labels[f.key], "reason": "must be completed by a person"} for f in guarded]
        ask = [f for f in new if not never_fill(f)]
        plan = map_fields(ask, passport, model, usage) if ask else {}
        for field in ask:  # in page order, because an answer here may reveal the next question
            checked = validate(field, plan.get(field.key), passport)
            done[field.key] = checked
            if checked["decision"] != "fill":
                review.append({"label": labels[field.key], "decision": checked["decision"], "reason": checked["reason"]})
                continue
            try:
                apply_field(page, field, checked["value"])
            except Exception as error:
                errors.append(f"{labels[field.key]}: {str(error).splitlines()[0][:160]}")
                review.append({"label": labels[field.key], "decision": "needs_review", "reason": "could not be applied to the form"})
                done[field.key] = {**checked, "decision": "needs_review"}
                continue
            answers.append({"label": labels[field.key], "value": checked["value"], "evidence_fact_ids": checked["evidence"]})
    final = {f.key: f for f in inspect_form(page).fields}
    unconfirmed = [labels[k] for k, c in done.items() if c.get("decision") == "fill" and k in final and not same(final[k], c["value"], final[k].value)]
    return {"answers": answers, "needs_review": review, "blocked": blocked, "unconfirmed": unconfirmed, "errors": errors,
            "seconds": round(time.perf_counter() - started, 2), **usage.row()}
