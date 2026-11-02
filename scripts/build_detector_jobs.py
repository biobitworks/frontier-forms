#!/usr/bin/env python3
"""Render jobs for the trained field-box detector (V2) and its validator evaluation.

Images are rendered from the local form server by tools/render/render_forms.js and
kept LOCAL (never committed). Only this job list's hash, GOLD_BOXES annotations
and receipts are published as JSON.

Splits follow split-v1, so patients are held out:
  train       train-split patients, seen templates only, 2 randomized layouts each
  validation  validation-split patients, seen templates, 1 randomized layout each
  test        test-split patients, all templates (urgent_care_history_v1 is a held-out
              layout never seen in training), default layout plus 1 randomized layout

Domain randomization (values) uses one perturbation per image:
  name_digits       legitimate digits in a name (Synthea style); written value == plan
  o_zero            0 -> O in phone/ZIP as written; written != plan       (MISMATCH)
  zip_drop_zero     leading zero of ZIP lost as written                   (MISMATCH)
  empty_field       planned value not written                             (MISMATCH)
  dropdown_wrong    another dropdown option written                       (MISMATCH)
  clip_long         very long list in a text area; written == plan but clipped on screen
  forged_nearby     look-alike text printed next to an input; written == plan
  clean             no change
Each image's `plan_values` is what the filler intended. The rendered DOM value is what
was actually written. The validator only sees the plan and the image.

    PYTHONPATH=src python3 scripts/build_detector_jobs.py > jobs.json
"""
import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frontier_forms.forms import b0  # noqa: E402
from frontier_forms.forms.cohort import load_cohort  # noqa: E402
from frontier_forms.forms.passport import build_passport  # noqa: E402
from frontier_forms.forms.templates import load_templates, render_html  # noqa: E402

SEED = 20261102
PERTURBATIONS = ["clean", "name_digits", "o_zero", "zip_drop_zero", "empty_field", "dropdown_wrong", "clip_long", "forged_nearby"]
MISMATCH = {"o_zero", "zip_drop_zero", "empty_field", "dropdown_wrong"}


def css(rng):
    fs = rng.randint(13, 17)
    return (f"body{{font-size:{fs}px;margin:{rng.randint(10, 48)}px;width:{rng.randint(680, 860)}px;"
            f"letter-spacing:{rng.choice([0, 0, 0.3, 0.6])}px}} .row{{margin:{rng.randint(4, 18)}px 0}} "
            f"input,select{{width:{rng.randint(380, 640)}px;height:{rng.randint(22, 34)}px;font-size:{fs - 1}px}} "
            f"textarea{{width:{rng.randint(380, 640)}px;height:{rng.randint(44, 96)}px;font-size:{fs - 2}px}} "
            f"label{{margin-bottom:{rng.randint(1, 8)}px}}")


def fmt(v):
    return "" if v is None else (f"{v:g}" if isinstance(v, float) else str(v))


def perturb(kind, values, template, rng):
    """Return (written_values, target_field_key or None, forge or None)."""
    w = dict(values)
    ftype = {f["field_key"]: f for f in template["fields"]}
    filled = [k for k, v in values.items() if v]
    pick = lambda keys: rng.choice(sorted(keys)) if keys else None  # noqa: E731
    if kind == "name_digits":
        k = pick([k for k in filled if "name" in k])
        if k:
            w[k] = values[k] + str(rng.randint(100, 999))
        return w, None, None  # legitimate value: plan follows the written value
    if kind == "o_zero":
        k = pick([k for k in filled if k in ("phone", "zip") and "0" in values[k]])
        if k:
            w[k] = values[k].replace("0", "O")
        return w, k, None
    if kind == "zip_drop_zero":
        k = pick([k for k in filled if k == "zip" and values[k].startswith("0")])
        if k:
            w[k] = values[k].lstrip("0")
        return w, k, None
    if kind == "empty_field":
        k = pick([k for k in filled if ftype[k]["type"] != "select"])
        if k:
            w[k] = ""
        return w, k, None
    if kind == "dropdown_wrong":
        k = pick([k for k in filled if ftype[k]["type"] == "select"])
        if k:
            w[k] = pick([o for o in ftype[k]["options"] if o and o != values[k]])
        return w, k, None
    if kind == "clip_long":
        k = pick([k for k in filled if ftype[k]["type"] == "textarea"])
        if k:
            w[k] = "; ".join([values[k]] * 6)
        return w, None, None
    if kind == "forged_nearby":
        k = pick([k for k in filled if ftype[k]["type"] != "textarea"])
        if k:
            return w, None, {"field_key": k, "text": re.sub(r"\d", lambda m: str((int(m.group()) + 3) % 10), values[k]) or "N/A"}
    return w, None, None


def main():
    templates = load_templates()
    members, bundles = load_cohort(ROOT / "data/forms_cohort_v1/bundles")
    jobs = []
    for m in members:
        p = build_passport(bundles[m.patient_id], m.path.name, f"SYN-{m.patient_id[:8]}")
        for k in sorted(templates):
            t = templates[k]
            if m.split not in t["splits"]:
                continue
            plan = {a["field_key"]: fmt(a["value"]) for a in b0.fill_plan(render_html(t), p)["answers"]}
            variants = {"train": ["rand0", "rand1"], "validation": ["rand0"], "test": ["default", "rand0"]}[m.split]
            for var in variants:
                jid = f"{m.split}__{k}__{m.patient_id}__{var}"
                rng = random.Random(f"{SEED}:{jid}")
                kind = PERTURBATIONS[int(hashlib.sha256(jid.encode()).hexdigest(), 16) % len(PERTURBATIONS)]
                written, target, forge = perturb(kind, plan, t, rng)
                plan_v = dict(plan)
                if kind in ("name_digits", "clip_long"):
                    plan_v = dict(written)  # the intended value really is this
                job = {"id": jid, "template_key": k, "patient_id": m.patient_id, "split": m.split, "values": written,
                       "plan_values": plan_v,
                       "perturbation": {"kind": kind, "target_field": target, "mismatch": bool(target) and kind in MISMATCH,
                                        "layout": var, "held_out_layout": m.split == "test" and "test" == "".join(t["splits"])}}
                if var != "default":
                    job["css"] = css(rng)
                if forge:
                    job["forge"] = forge
                jobs.append(job)
    print(json.dumps(jobs, sort_keys=True))


if __name__ == "__main__":
    main()
