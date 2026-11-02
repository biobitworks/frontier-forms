"""Build everything derived from the frozen patients and forms, and lock it.

    freeze.py          writes ../site (what browsers see), data/templates, data/gold and data/passports, then data/freeze.json
    freeze.py --check  rebuilds in memory and fails if anything differs from data/freeze.json

Patients and template families are held out together: dev templates pair only with dev patients and test templates only
with test patients. The field-to-fact mapping and gold live here, outside the served site and unreadable to sandboxed agents.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import forms as form_lib
import passports as pp

HERE = Path(__file__).resolve().parent
DATA, SITE = HERE / "data", HERE.parent / "site"
TYPES = {"phonemask": "tel", "combo": "select", "dateparts": "date", "ariamatrix": "radio", "matrix": "radio", "hidden": "text"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _dump(value) -> str:
    return json.dumps(value, indent=1, sort_keys=True) + "\n"


def schema(form: form_lib.Form) -> dict:
    fields = []
    for fid, f, key in form.scored():
        label = f.label
        if f.kind in ("matrix", "ariamatrix"):
            label = f"{f.label}: {f.rows[int(fid.rsplit('_', 1)[1])][1]}"
        validation = {k: v for k, v in (("format", f.fmt), ("hint", f.hint)) if v}
        fields.append({"field_key": fid, "label": label, "type": TYPES.get(f.kind, f.kind), "widget": f.kind, "required": f.required,
                       "options": list(f.options) if f.options else None, "columns": [c for _, c in f.sub] if f.sub else None,
                       "validation": validation, "visible_when": {"field_key": f.when[0], "equals": f.when[1]} if f.when else None,
                       "selector": f'[data-fid="{fid}"]', "passport_key": pp.source_key(key), "concept": key})
    return {"template_key": form.name, "title": form.title, "modality": "html", "split": form.split, "track": form.track,
            "layout": form.layout, "features": form.features(), "multistep": form.wizard, "fields": fields}


def gold_file(form: form_lib.Form, p: dict) -> dict:
    out = {}
    for fid, f, key in form.scored():
        g = pp.gold(p, key)
        out[fid] = {"concept": key, "decision": g.decision, "expect": g.expect, "forbid": g.forbid,
                    "evidence_fact_ids": pp.evidence(p, key) if g.decision == "fill" else []}
    return {"template_key": form.name, "synthetic_id": p["synthetic_id"], "fields": out}


def outputs() -> dict[str, str]:
    """Every derived file, as {path under data/: contents}."""
    people, parts = pp.load(), pp.splits()
    files = {}
    for name, form in form_lib.all_forms().items():
        files[f"templates/{name}.json"] = _dump(schema(form))
        for sid in parts[form.split]:
            files[f"gold/{name}/{sid}.json"] = _dump(gold_file(form, people[sid]))
    for sid in parts["dev"] + parts["test"]:
        files[f"passports/{sid}.json"] = _dump(people[sid])
    return files


def manifest(files: dict[str, str]) -> dict:
    site = {str(path.relative_to(SITE)): _sha(path.read_text()) for path in sorted(SITE.rglob("*")) if path.is_file()}
    forms = form_lib.all_forms()
    return {"splits": pp.splits(), "template_families": {s: [n for n, f in forms.items() if f.split == s] for s in ("dev", "test")},
            "pairing": "dev templates with dev patients only; test templates with test patients only",
            "source": {"synthea_passports.json": _sha((DATA / "synthea_passports.json").read_text())},
            "site": site, "data": {path: _sha(text) for path, text in sorted(files.items())}}


def main() -> None:
    files = outputs()
    frozen = DATA / "freeze.json"
    if "--check" in sys.argv:
        form_lib.build_site(SITE)
        same = json.loads(frozen.read_text()) == json.loads(json.dumps(manifest(files)))
        print("freeze intact" if same else "FREEZE BROKEN: derived files differ from data/freeze.json")
        raise SystemExit(0 if same else 1)
    if frozen.exists() and "--refreeze" not in sys.argv:
        raise SystemExit("data/freeze.json exists. Use --check, or --refreeze only before any held-out result has been seen.")
    shutil.rmtree(SITE, ignore_errors=True)
    form_lib.build_site(SITE)
    for path, text in files.items():
        target = DATA / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    frozen.write_text(_dump(manifest(files)))
    print(len(files), "data files,", sum(1 for p in SITE.rglob("*") if p.is_file()), "site files")


if __name__ == "__main__":
    main()
