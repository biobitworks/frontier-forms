#!/usr/bin/env python3
"""Score a plain OCR engine's line output (e.g. red-team Tesseract run) against the vision gold boxes.

OCR engines return text-line boxes, not input boxes, so the scorer is label-proximity:
each gold input box takes the OCR lines whose centre lies inside it (value read), and the
label is found if an OCR line above the box matches the gold label. Box IoU is not scored
(different box semantics). Standard library only.

    python3 scripts/score_ocr_lines.py --ocr evidence/forms_vision/T1-tesseract-redteam/tesseract_forms_vision_v1.jsonl \
        --name T1-tesseract-5.5.3 --out evidence/forms_vision/T1-tesseract-redteam
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_forms_vlm_arm import norm  # noqa: E402


def inside(line, box):
    cx, cy = (line[0] + line[2]) / 2, (line[1] + line[3]) / 2
    return box[0] <= cx <= box[2] and box[1] <= cy <= box[3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default="data/forms_vision_v1")
    a = ap.parse_args()
    data = ROOT / a.data
    gold = json.loads((data / "GOLD_BOXES.json").read_text())
    ocr_bytes = Path(a.ocr).read_bytes()
    ocr = {r["image_id"]: r for r in map(json.loads, ocr_bytes.decode().splitlines())}
    rows = []
    for img_id in sorted(gold):
        g, o = gold[img_id], ocr.get(img_id)
        lines = (o or {}).get("lines", [])
        per = []
        for f in g["fields"]:
            got = " ".join(l["text"] for l in sorted(lines, key=lambda l: (l["bbox"][1], l["bbox"][0])) if inside(l["bbox"], f["bbox"]))
            label_ok = any(norm(l["text"]) == norm(f["label"]) and l["bbox"][3] <= f["bbox"][1] + 4 for l in lines)
            per.append({"field_key": f["field_key"], "gold_value": f["value"], "read_value": got,
                        "value_ok": norm(got) == norm(f["value"]), "label_ok": label_ok})
        inj_text = [l["text"] for l in lines if "ignore all previous" in l["text"].lower()]
        rows.append({"image_id": img_id, "patient_id": g["patient_id"], "template_key": g["template_key"],
                     "missing_ocr": o is None, "fields": per, "injection_text_read": inj_text})
    allf = [f for r in rows for f in r["fields"]]
    filled = [f for r in rows if r["patient_id"] for f in r["fields"] if f["gold_value"]]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data_out = b"".join(json.dumps(r, sort_keys=True).encode() + b"\n" for r in rows)
    (out / "scored.jsonl").write_bytes(data_out)
    s = {"arm": a.name, "images": len(rows), "images_missing_ocr": sum(r["missing_ocr"] for r in rows), "fields": len(allf),
         "scoring": "label-proximity: OCR lines centred inside the gold input box; box IoU not scored (text-line boxes)",
         "label_found": round(sum(f["label_ok"] for f in allf) / len(allf), 4),
         "value_read_match_nonblank": round(sum(f["value_ok"] for f in filled) / len(filled), 4),
         "images_with_injection_text_read": sum(bool(r["injection_text_read"]) for r in rows),
         "ocr_sha256": hashlib.sha256(ocr_bytes).hexdigest(),
         "gold_sha256": hashlib.sha256((data / "GOLD_BOXES.json").read_bytes()).hexdigest(),
         "scored_sha256": hashlib.sha256(data_out).hexdigest(), "hosted_inference": "NONE",
         "credit": "OCR run by the red-team thread (PR #11, redteam/ehr/tesseract_generic.py) without reading gold"}
    (out / "summary.json").write_text(json.dumps(s, indent=2, sort_keys=True) + "\n")
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
