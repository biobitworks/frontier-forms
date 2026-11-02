"""Form templates and their HTML rendering.

The canonical_key on each field is the oracle's answer mapping. It is never
rendered into HTML or returned by the public server API, so a filler only
sees what a browser would see: labels, names, types and options.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def load_templates(directory: Path = TEMPLATE_DIR) -> dict:
    out = {}
    for path in sorted(Path(directory).glob("*.json")):
        t = json.loads(path.read_text())
        keys = [f["field_key"] for f in t["fields"]]
        if len(set(keys)) != len(keys):
            raise ValueError(f"DUPLICATE_FIELD_KEY:{t['template_key']}")
        out[t["template_key"]] = t
    return out


def public_schema(template: dict) -> dict:
    """What a client may see: no canonical keys, no gold."""
    return {
        "template_key": template["template_key"],
        "title": template["title"],
        "fields": [{k: v for k, v in f.items() if k != "canonical_key"} for f in template["fields"]],
    }


def render_html(template: dict) -> str:
    e = html.escape
    rows = []
    for f in template["fields"]:
        fid = f"f_{f['field_key']}"
        req = " required" if f.get("required") else ""
        label = f'<label for="{e(fid)}">{e(f["label"])}</label>'
        if f["type"] == "textarea":
            ctl = f'<textarea id="{e(fid)}" name="{e(f["field_key"])}"{req}></textarea>'
        elif f["type"] == "select":
            opts = "".join(f'<option value="{e(o)}">{e(o) or "-- select --"}</option>' for o in f["options"])
            ctl = f'<select id="{e(fid)}" name="{e(f["field_key"])}"{req}>{opts}</select>'
        else:
            typ = "number" if f["type"] == "number" else "text"
            step = ' step="0.1"' if typ == "number" else ""
            ctl = f'<input id="{e(fid)}" name="{e(f["field_key"])}" type="{typ}"{step}{req}>'
        rows.append(f"<div class=\"row\">{label}{ctl}</div>")
    notice = ""
    if template.get("untrusted_notice"):
        notice = f'<p class="notice">{e(template["untrusted_notice"])}</p>'
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{e(template['title'])}</title></head><body>"
        "<p class=\"banner\">SYNTHETIC DEMO FORM. Not a real clinic. Do not enter real patient data.</p>"
        f"<h1>{e(template['title'])}</h1>{notice}"
        f"<form id=\"intake\" method=\"post\" action=\"/forms/{e(template['template_key'])}/submit\">"
        + "".join(rows)
        + "<button type=\"submit\">Submit</button></form></body></html>"
    )
