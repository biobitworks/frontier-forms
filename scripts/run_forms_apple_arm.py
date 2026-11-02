#!/usr/bin/env python3
"""Apple-native comparison arm: Vision OCR + PDFKit (Preview's form engine). Runs on macOS.

Two arms, both using the frozen B0 keyword rules so that only the form
front end differs from B0:

  A1-apple-pdfkit   field labels come from Apple Vision OCR of the printed PDF
                    form, fields are found and filled through PDFKit widgets
                    (as Preview does); the answer is the value PDFKit stores.
  A2-apple-ocr-rb   A1, then the filled PDF is rendered and every field is read
                    back with Vision OCR; the answer is what OCR reads.

    swiftc -O tools/apple_forms/AppleForms.swift -o /tmp/AppleForms
    python3 scripts/run_forms_apple_arm.py --tool /tmp/AppleForms --out evidence/forms_apple/run_v1

The frozen PDF forms are written once to evidence/forms_apple/forms/ and
then reused (their SHA-256 is recorded in the receipt).
"""
import argparse
import json
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from frontier_forms.forms import b0  # noqa: E402
from frontier_forms.forms.cohort import cohort_root, load_cohort, sha256_bytes, sha256_file  # noqa: E402
from frontier_forms.forms.harness import _http, jsonl, output_root, per_field_accuracy, score_field, summarize  # noqa: E402
from frontier_forms.forms.oracle import ORACLE_VERSION, gold_answers  # noqa: E402
from frontier_forms.forms.server import FormState, serve  # noqa: E402
from frontier_forms.forms.statistics_bridge import paired_vs_b0  # noqa: E402
from frontier_forms.forms.templates import TEMPLATE_DIR, load_templates  # noqa: E402

FORMS_DIR = ROOT / "evidence/forms_apple/forms"


def tool(bin_, *args):
    return subprocess.run([bin_, *args], check=True, capture_output=True, text=True).stdout


def as_value(v):
    if v is None:
        return None
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def answer_from(text):
    t = (text or "").strip()
    return {"decision": "fill", "value": t} if t else {"decision": "needs_user_input", "value": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", required=True)
    ap.add_argument("--cohort", default=str(ROOT / "data/forms_cohort_v1/bundles"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--samples", type=int, default=0, help="keep the first N filled PDFs per template for spot checks")
    args = ap.parse_args()

    templates = load_templates()
    FORMS_DIR.mkdir(parents=True, exist_ok=True)
    inspected = {}
    for key in sorted(templates):
        pdf = FORMS_DIR / f"{key}.pdf"
        if not pdf.exists():
            tool(args.tool, "make-pdf", str(TEMPLATE_DIR / f"{key}.json"), str(pdf))
        ins = json.loads(tool(args.tool, "inspect", str(pdf)))
        # PDFKit renames widgets on save (text0, choice0, ...). Widgets are laid out
        # top to bottom in template order, so geometry gives the scoring key.
        ordered = sorted(ins["fields"], key=lambda f: -f["rect"][1])
        if len(ordered) != len(templates[key]["fields"]):
            raise SystemExit(f"WIDGET_COUNT_MISMATCH:{key}")
        for f, tf in zip(ordered, templates[key]["fields"]):
            f["field_key"] = tf["field_key"]
        inspected[key] = ins

    members, bundles = load_cohort(Path(args.cohort), limit=args.limit)
    httpd = serve(FormState(members, bundles, templates))
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    rows = {"A1-apple-pdfkit": [], "A2-apple-ocr-rb": []}
    sample_counts = {}
    t0 = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            for m in members:
                passport = _http(base, f"/api/passport/{m.patient_id}")
                for key in sorted(templates):
                    t = templates[key]
                    if m.split not in t["splits"]:
                        continue
                    values = {}
                    for f in inspected[key]["fields"]:
                        dec, val = b0.map_field(f["label"], f, passport)
                        if dec == "fill" and val not in (None, ""):
                            values[f["name"]] = as_value(val)
                    vpath, fpath = Path(tmp) / "v.json", Path(tmp) / "filled.pdf"
                    vpath.write_text(json.dumps(values))
                    tool(args.tool, "fill", str(FORMS_DIR / f"{key}.pdf"), str(vpath), str(fpath))
                    rb = json.loads(tool(args.tool, "readback", str(fpath)))
                    kept = sample_counts.get(key, 0)
                    if kept < args.samples:
                        sdir = Path(args.out) / "samples"
                        sdir.mkdir(parents=True, exist_ok=True)
                        (sdir / f"{key}__{m.patient_id[:8]}.pdf").write_bytes(fpath.read_bytes())
                        (sdir / f"{key}__{m.patient_id[:8]}.readback.json").write_text(json.dumps(rb, indent=2, sort_keys=True))
                        sample_counts[key] = kept + 1
                    gold = gold_answers(bundles[m.patient_id], t)
                    for arm, src in (("A1-apple-pdfkit", "pdf_value"), ("A2-apple-ocr-rb", "text")):
                        name_to_key = {f["name"]: f["field_key"] for f in inspected[key]["fields"]}
                        pred = {name_to_key[k]: answer_from(v[src]) for k, v in rb.items()}
                        fields = {k: score_field(g, pred.get(k)) for k, g in sorted(gold.items())}
                        if arm == "A2-apple-ocr-rb":
                            for k in fields:
                                nm = next(n for n, fk in name_to_key.items() if fk == k)
                                fields[k]["ocr_min_confidence"] = round(rb[nm]["min_confidence"], 3)
                        case_key = f"{m.patient_id}|{key}"
                        rows[arm].append({
                            "case_key": case_key,
                            "case_digest_sha256": sha256_bytes(f"{case_key}|{m.sha256}|{ORACLE_VERSION}".encode()),
                            "patient_id": m.patient_id, "split": m.split, "template_key": key, "task": key,
                            "arm": arm, "echo_validated": True, "fields": fields,
                            "required_fields_correct": all(f["correct"] for f in fields.values() if f["required"]),
                            "all_fields_correct": all(f["correct"] for f in fields.values()),
                            "plan_sha256": sha256_bytes(json.dumps(values, sort_keys=True).encode()),
                        })
    finally:
        httpd.shutdown()
        httpd.server_close()
    elapsed = time.perf_counter() - t0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    b0_rows = [json.loads(x) for x in (ROOT / "evidence/forms_b0/run_v1/predictions.jsonl").read_text().splitlines()]
    receipt = {
        "arms": sorted(rows), "oracle": ORACLE_VERSION, "mapping_rules": b0.B0_VERSION,
        "n_patients": len(members), "cohort_root": cohort_root(members),
        "frozen_pdf_forms_sha256": {p.name: sha256_file(p) for p in sorted(FORMS_DIR.glob("*.pdf"))},
        "tool_source_sha256": sha256_file(ROOT / "tools/apple_forms/AppleForms.swift"),
        "inspected_labels": {k: [(f["field_key"], f["name"], f["label"], round(f["label_confidence"], 3)) for f in v["fields"]]
                             for k, v in inspected.items()},
        "host": {"machine": platform.machine(), "macos": platform.mac_ver()[0], "python": platform.python_version()},
        "hosted_inference": "NONE", "wall_seconds": round(elapsed, 1),
    }
    for arm, rs in rows.items():
        tag = arm.split("-")[0]
        data = jsonl(rs)
        (out / f"predictions_{tag}.jsonl").write_bytes(data)
        summary = {"arm": arm, "oracle": ORACLE_VERSION, "metrics": summarize(rs),
                   "per_field_accuracy": per_field_accuracy(rs), "paired_vs_B0": paired_vs_b0(b0_rows, rs)}
        (out / f"summary_{tag}.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        receipt[f"{tag}_predictions_sha256"] = sha256_bytes(data)
        receipt[f"{tag}_output_root"] = output_root(rs)
        print(arm, json.dumps(summary["metrics"]["overall"]), json.dumps(summary["paired_vs_B0"]["overall"]))
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
