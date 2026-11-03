#!/usr/bin/env python3
"""Render the README 'In progress: SFT' section from evidence/forms_model/SFT_STATUS.json.

Edit the JSON (per-run status, val loss, test numbers), then run:
    python3 scripts/update_readme_sft.py
Only the text between the sft-status markers in README.md is replaced.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- sft-status:start -->", "<!-- sft-status:end -->"


def render(s):
    out = [START, "", f"## {s['label']}: trained form-filling model (SFT)", "",
           f"**What:** {s['model']}, fine-tuned on {s['data']}. {len(s['runs'])} configs "
           f"{'were' if s.get('result') else 'are being'} trained.", ""]
    if s.get("result"):
        out += [f"**Result:** {s['result']}", ""]
    out += [f"**Protocol:** {s['protocol']}", "",
           "**Comparison points (frozen 54-form test split):**", "",
           "| Arm | Field accuracy | Full-form success | Source |", "|---|---|---|---|"]
    for c in s["comparators"]:
        out.append(f"| {c['arm']} | {c['field_accuracy'] or '—'} | {c['full_form']} | `{c['source']}` |")
    out += ["", f"**Runs (status as of {s['updated_utc']}):**", "",
            "| Run | Config | Status | Val loss | Test field accuracy | Test full-form |", "|---|---|---|---|---|---|"]
    for r in s["runs"]:
        out.append(f"| {r['run']} | {r['config']} | {r['status']} | {r['val_loss'] or '—'} | "
                   f"{r['test_field_accuracy'] or '—'} | {r['test_full_form'] or '—'} |")
    out += ["", "**Results will appear in:** " + " · ".join(f"`{x}`" for x in s["results_will_appear"]) + ".",
            "Status data: [`evidence/forms_model/SFT_STATUS.json`](evidence/forms_model/SFT_STATUS.json); "
            "refresh with `python3 scripts/update_readme_sft.py`. Only the config chosen on validation is scored on test, once.",
            "", END]
    return "\n".join(out)


def main():
    s = json.loads((ROOT / "evidence/forms_model/SFT_STATUS.json").read_text())
    p = ROOT / "README.md"
    r = p.read_text()
    block = render(s)
    if START in r:
        a, b = r.index(START), r.index(END) + len(END)
        r = r[:a] + block + r[b:]
    else:
        anchor = "## Judges — start here"
        i = r.index(anchor)
        r = r[:i] + block + "\n\n" + r[i:]
    p.write_text(r)
    print("README SFT section updated:", [x["status"] for x in s["runs"]])


if __name__ == "__main__":
    main()
