#!/usr/bin/env python3
"""Local vision-language model (Ollama, e.g. qwen2.5vl:3b) reading form images with bounding boxes.

Images and gold boxes come from data/forms_vision_v1 (rendered by
tools/render/render_forms.js from the served forms; gold = DOM input boxes and
the values actually written in them). For every image the model is asked to
list each input box with its label, the text written in it, and a pixel
bounding box. Standard library only.

Scores per image: box recall at IoU>=0.5, mean IoU of matched boxes, label
match, and value-read match (against the value written in the box, not the
oracle), plus seconds per page. Raw model output is kept verbatim.

    python3 scripts/run_forms_vlm_arm.py --model qwen2.5vl:3b --name V1-qwen2.5vl-3b --out evidence/forms_vision/V1-qwen2.5vl-3b
"""
import argparse
import base64
import json
import platform
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_forms_ollama_arm import model_identity, post  # noqa: E402

DATA = ROOT / "data/forms_vision_v1"
PROMPT = ("This image is a SYNTHETIC medical intake form. List every input box (text box, text area or dropdown). "
          "For each one return the printed label above it, the exact text currently written inside it (empty string if blank), "
          "and its bounding box in pixel coordinates of this image as [x1, y1, x2, y2]. "
          'Reply with JSON only: {"fields": [{"label": "...", "value": "...", "bbox": [x1, y1, x2, y2]}]}')


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def parse(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return []
    try:
        obj = json.loads(m.group(0))
    except ValueError:
        return []
    out = []
    for f in obj.get("fields", []) if isinstance(obj, dict) else []:
        b = f.get("bbox") if isinstance(f, dict) else None
        if isinstance(b, list) and len(b) == 4 and all(isinstance(x, (int, float)) for x in b):
            out.append({"label": str(f.get("label", "")), "value": str(f.get("value", "") or ""), "bbox": [float(x) for x in b]})
    return out


def score(gold_fields, pred):
    pairs = sorted(((iou(g["bbox"], p["bbox"]), gi, pi) for gi, g in enumerate(gold_fields) for pi, p in enumerate(pred)),
                   reverse=True)
    used_g, used_p, matches = set(), set(), []
    for v, gi, pi in pairs:
        if v < 0.5 or gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        matches.append((gi, pi, v))
    per = []
    for gi, g in enumerate(gold_fields):
        m = next((x for x in matches if x[0] == gi), None)
        p = pred[m[1]] if m else None
        per.append({"field_key": g["field_key"], "iou": round(m[2], 3) if m else 0.0, "box_found": bool(m),
                    "label_ok": bool(p) and norm(p["label"]) == norm(g["label"]),
                    "value_ok": bool(p) and norm(p["value"]) == norm(g["value"]),
                    "pred": p, "gold_bbox": g["bbox"], "gold_value": g["value"]})
    return per, len(pred) - len(matches)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5vl:3b")
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261102)
    args = ap.parse_args()
    gold = json.loads((DATA / "GOLD_BOXES.json").read_text())
    ident = model_identity(args.model)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for img_id in sorted(gold):
        g = gold[img_id]
        b64 = base64.b64encode((DATA / g["image"]).read_bytes()).decode()
        t = time.perf_counter()
        r = post("/api/generate", {"model": args.model, "prompt": PROMPT, "images": [b64], "stream": False,
                                   "options": {"temperature": 0, "seed": args.seed, "num_predict": 1500}})
        dt = time.perf_counter() - t
        raw = r.get("response", "")
        pred = parse(raw)
        per, extra = score(g["fields"], pred)
        rows.append({"image_id": img_id, "template_key": g["template_key"], "patient_id": g["patient_id"],
                     "seconds": round(dt, 2), "raw_output": raw, "n_pred": len(pred), "false_boxes": extra, "fields": per})
        print(img_id, f"{dt:.1f}s", sum(f["box_found"] for f in per), "/", len(per), flush=True)
    data = b"".join(json.dumps(x, sort_keys=True).encode() + b"\n" for x in rows)
    (out / "answers.jsonl").write_bytes(data)
    allf = [f for r in rows for f in r["fields"]]
    filled = [f for r in rows if r["patient_id"] for f in r["fields"] if f["gold_value"]]
    secs = sorted(r["seconds"] for r in rows)
    summary = {
        "arm": args.name, "images": len(rows), "fields": len(allf),
        "box_recall_iou50": round(sum(f["box_found"] for f in allf) / len(allf), 4),
        "mean_iou_matched": round(sum(f["iou"] for f in allf if f["box_found"]) / max(1, sum(f["box_found"] for f in allf)), 4),
        "label_match": round(sum(f["label_ok"] for f in allf) / len(allf), 4),
        "value_read_match_nonblank": round(sum(f["value_ok"] for f in filled) / len(filled), 4) if filled else None,
        "false_boxes": sum(r["false_boxes"] for r in rows),
        "seconds_per_page_median": secs[len(secs) // 2], "seconds_per_page_max": secs[-1],
        "model_identity": ident, "hosted_inference": "NONE",
        "answers_sha256": __import__("hashlib").sha256(data).hexdigest(),
        "gold_sha256": __import__("hashlib").sha256((DATA / "GOLD_BOXES.json").read_bytes()).hexdigest(),
        "host": {"machine": platform.machine(), "platform": platform.platform()},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("model_identity", "host")}))


if __name__ == "__main__":
    main()
