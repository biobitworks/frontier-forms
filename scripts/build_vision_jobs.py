#!/usr/bin/env python3
"""Write render jobs for the vision arm: blank forms + B0-filled test-split forms.

    PYTHONPATH=src python3 scripts/build_vision_jobs.py > /tmp/vision_jobs.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frontier_forms.forms import b0  # noqa: E402
from frontier_forms.forms.cohort import load_cohort  # noqa: E402
from frontier_forms.forms.passport import build_passport  # noqa: E402
from frontier_forms.forms.templates import load_templates, render_html  # noqa: E402

templates = load_templates()
members, bundles = load_cohort(ROOT / "data/forms_cohort_v1/bundles")
jobs = [{"id": f"blank__{k}", "template_key": k, "values": {}} for k in sorted(templates)]
for m in members:
    if m.split != "test":
        continue
    p = build_passport(bundles[m.patient_id], m.path.name, f"SYN-{m.patient_id[:8]}")
    for k in sorted(templates):
        plan = b0.fill_plan(render_html(templates[k]), p)
        vals = {a["field_key"]: ("" if a["value"] is None else (f"{a['value']:g}" if isinstance(a["value"], float) else str(a["value"])))
                for a in plan["answers"]}
        jobs.append({"id": f"filled__{k}__{m.patient_id}", "template_key": k, "patient_id": m.patient_id, "values": vals})
print(json.dumps(jobs))
