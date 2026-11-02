"""Prebuilt filled forms with seeded, known injected errors (detector benchmark).

Each prebuilt form starts from the oracle's correct answers for one
(patient, template) case. A seeded RNG then injects 0-3 errors of declared
types. Errors E1-E4 and E6-E8 are made before the form is sealed. E5 is a
tamper made after sealing, so the seal still commits to the pre-tamper value.

Detectors see forms.jsonl only. The ground truth (truth.jsonl) records each
injected error instance: its type, the field(s) touched, and the before and
after values. Nothing in this module reads detector code.
"""
from __future__ import annotations

import hashlib
import json
import random

from .oracle import Record, gold_answers

INJECTION_VERSION = "inject-v1"
SEED = 20261102
VARIANTS_PER_CASE = 3
N_ERRORS_WEIGHTS = {0: 0.30, 1: 0.40, 2: 0.20, 3: 0.10}
ERROR_TYPES = {
    "E1_swap": "values of two filled single-line text fields exchanged",
    "E2_wrong_patient": "a filled value replaced by the same field's value from another patient",
    "E3_unit": "a number written in the wrong unit (kg<->lb, cm->in)",
    "E4_fabricated_none": "a field whose correct answer is 'ask the patient' filled with 'None'",
    "E5_post_seal_tamper": "a value changed after the form was sealed (one digit, or another patient's value)",
    "E6_dropped": "a required filled field left blank",
    "E7_typo": "one character replaced by an OCR-confusable character",
    "E8_stale": "a vital sign replaced by an older observation of the same code",
}
CONFUSABLE = {"o": "0", "O": "0", "l": "1", "I": "1", "e": "c", "a": "o", "S": "5", "s": "5",
              "B": "8", "g": "9", "n": "m", "r": "n", "t": "f", "i": "l", "u": "v", "m": "rn"}
VITAL_LOINC = {"height_cm": ("8302-2", 1.0), "weight_kg": ("29463-7", 1.0), "weight_lb": ("29463-7", 2.20462)}


def fmt(gold: dict) -> str:
    if gold["decision"] != "fill":
        return ""
    v = gold["value"]
    if gold["kind"] == "list":
        return "; ".join(v)
    if gold["kind"] == "number":
        return f"{v:g}"
    return str(v)


def leaf(form_id: str, field_key: str, value: str) -> str:
    return hashlib.sha256(f"{form_id}|{field_key}|{value}".encode()).hexdigest()


def _older_vital(bundle: dict, field_key: str, current: str):
    loinc, factor = VITAL_LOINC.get(field_key, (None, None))
    rec = Record(bundle)
    if field_key == "blood_pressure":
        obs = [o for o in rec.of("Observation") if o.get("status") in ("final", "amended")
               and "85354-9" in {c.get("code") for c in (o.get("code") or {}).get("coding") or []}]
        obs.sort(key=lambda o: o.get("effectiveDateTime") or "", reverse=True)
        for o in obs[1:]:
            comp = {}
            for c in o.get("component") or []:
                for cc in (c.get("code") or {}).get("coding") or []:
                    comp[cc.get("code")] = (c.get("valueQuantity") or {}).get("value")
            if comp.get("8480-6") is not None and comp.get("8462-4") is not None:
                v = f"{round(float(comp['8480-6']))}/{round(float(comp['8462-4']))}"
                if v != current:
                    return v
        return None
    if not loinc:
        return None
    obs = [o for o in rec.of("Observation") if o.get("status") in ("final", "amended")
           and loinc in {c.get("code") for c in (o.get("code") or {}).get("coding") or []}]
    obs.sort(key=lambda o: o.get("effectiveDateTime") or "", reverse=True)
    for o in obs[1:]:
        q = (o.get("valueQuantity") or {}).get("value")
        if q is None:
            continue
        v = f"{round(float(q) * factor, 1):g}"
        if v != current:
            return v
    return None


def _typo(rng, value):
    idx = [i for i, ch in enumerate(value) if ch in CONFUSABLE]
    if not idx:
        return None
    i = rng.choice(idx)
    return value[:i] + CONFUSABLE[value[i]] + value[i + 1:]


def _digit_change(rng, value):
    idx = [i for i, ch in enumerate(value) if ch.isdigit()]
    if not idx:
        return None
    i = rng.choice(idx)
    new = str((int(value[i]) + rng.randint(1, 8)) % 10)
    return value[:i] + new + value[i + 1:]


def build(members, bundles, templates):
    """Return (forms, truth). Deterministic for a given cohort and templates."""
    rng = random.Random(SEED)
    base = {}
    for m in members:
        for tkey in sorted(templates):
            t = templates[tkey]
            if m.split in t["splits"]:
                gold = gold_answers(bundles[m.patient_id], t)
                base[(m.patient_id, tkey)] = {k: fmt(g) for k, g in gold.items()}
    by_template = {}
    for (pid, tkey), vals in base.items():
        by_template.setdefault(tkey, []).append((pid, vals))

    forms, truth = [], []
    counts, weights = list(N_ERRORS_WEIGHTS), list(N_ERRORS_WEIGHTS.values())
    for m in members:
        for tkey in sorted(templates):
            if (m.patient_id, tkey) not in base:
                continue
            t = templates[tkey]
            fdef = {f["field_key"]: f for f in t["fields"]}
            gold = gold_answers(bundles[m.patient_id], t)
            for variant in range(VARIANTS_PER_CASE):
                form_id = hashlib.sha256(f"{INJECTION_VERSION}|{m.patient_id}|{tkey}|{variant}".encode()).hexdigest()[:20]
                values = dict(base[(m.patient_id, tkey)])
                n_err = rng.choices(counts, weights)[0]
                used, errors, tampers = set(), [], []
                attempts = 0
                while len(errors) + len(tampers) < n_err and attempts < 50:
                    attempts += 1
                    etype = rng.choice(sorted(ERROR_TYPES))
                    free = [k for k in sorted(values) if k not in used]
                    filled = [k for k in free if values[k]]
                    inst = None
                    if etype == "E1_swap":
                        cands = [k for k in filled if fdef[k]["type"] == "text"]
                        pairs = [(a, b) for a in cands for b in cands if a < b and values[a] != values[b]]
                        if pairs:
                            a, b = rng.choice(pairs)
                            inst = {"fields": [a, b], "before": [values[a], values[b]], "after": [values[b], values[a]]}
                            values[a], values[b] = values[b], values[a]
                    elif etype == "E2_wrong_patient":
                        if filled:
                            k = rng.choice(filled)
                            others = sorted({v[k] for pid, v in by_template[tkey] if pid != m.patient_id and v[k] and v[k] != values[k]})
                            if others:
                                new = rng.choice(others)
                                inst = {"fields": [k], "before": [values[k]], "after": [new]}
                                values[k] = new
                    elif etype == "E3_unit":
                        cands = [k for k in filled if k in VITAL_LOINC]
                        if cands:
                            k = rng.choice(cands)
                            v = float(values[k])
                            new = {"weight_kg": v * 2.20462, "weight_lb": v / 2.20462, "height_cm": v / 2.54}[k]
                            new = f"{round(new, 1):g}"
                            inst = {"fields": [k], "before": [values[k]], "after": [new]}
                            values[k] = new
                    elif etype == "E4_fabricated_none":
                        cands = [k for k in free if not values[k] and gold[k]["decision"] != "fill"
                                 and fdef[k]["type"] in ("text", "textarea")]
                        if cands:
                            k = rng.choice(cands)
                            inst = {"fields": [k], "before": [""], "after": ["None"]}
                            values[k] = "None"
                    elif etype == "E5_post_seal_tamper":
                        if filled:
                            k = rng.choice(filled)
                            new = _digit_change(rng, values[k])
                            if new is None:
                                others = sorted({v[k] for pid, v in by_template[tkey] if pid != m.patient_id and v[k] and v[k] != values[k]})
                                new = rng.choice(others) if others else None
                            if new and new != values[k]:
                                tampers.append({"fields": [k], "before": [values[k]], "after": [new]})
                                used.add(k)
                                continue
                    elif etype == "E6_dropped":
                        cands = [k for k in filled if fdef[k].get("required")]
                        if cands:
                            k = rng.choice(cands)
                            inst = {"fields": [k], "before": [values[k]], "after": [""]}
                            values[k] = ""
                    elif etype == "E7_typo":
                        cands = [k for k in filled if fdef[k]["type"] in ("text", "textarea") and _typo(random.Random(0), values[k])]
                        if cands:
                            k = rng.choice(cands)
                            new = _typo(rng, values[k])
                            inst = {"fields": [k], "before": [values[k]], "after": [new]}
                            values[k] = new
                    elif etype == "E8_stale":
                        cands = [k for k in filled if k in VITAL_LOINC or k == "blood_pressure"]
                        rng.shuffle(cands)
                        for k in cands:
                            new = _older_vital(bundles[m.patient_id], k, values[k])
                            if new:
                                inst = {"fields": [k], "before": [values[k]], "after": [new]}
                                values[k] = new
                                break
                    if inst:
                        inst["error_type"] = etype
                        errors.append(inst)
                        used.update(inst["fields"])
                seal = {k: leaf(form_id, k, values[k]) for k in sorted(values)}
                for tp in tampers:
                    tp["error_type"] = "E5_post_seal_tamper"
                    values[tp["fields"][0]] = tp["after"][0]
                    errors.append(tp)
                forms.append({
                    "form_id": form_id, "patient_id": m.patient_id, "split": m.split, "template_key": tkey,
                    "variant": variant,
                    "fields": {k: {"value": values[k], "label": fdef[k]["label"], "type": fdef[k]["type"],
                                   "required": bool(fdef[k].get("required")), "options": fdef[k].get("options")}
                               for k in sorted(values)},
                    "seal": {"leaves": seal, "algorithm": "sha256(form_id|field_key|value)"},
                })
                for i, e in enumerate(errors):
                    truth.append({"instance_id": f"{form_id}:{i}", "form_id": form_id, "patient_id": m.patient_id,
                                  "split": m.split, "template_key": tkey, **e})
    return forms, truth


def jsonl(rows) -> bytes:
    return b"".join(json.dumps(r, sort_keys=True).encode() + b"\n" for r in rows)
