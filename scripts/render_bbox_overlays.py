#!/usr/bin/env python3
"""Bounding-box overlays for the synthetic form screenshots, as JSON plus a self-contained HTML viewer.

The repo's JSON-only publication gate (scripts/check_synthetic_json_policy.py) rejects
new PNG/PDF files. So this writes no new pixels. It writes:
  <out>.json   per image: gold DOM boxes, model-predicted boxes + values read, OCR line boxes
  <out>.html   viewer that draws those boxes on a <canvas> over the already-committed
               screenshots (relative paths into data/), opened from a local clone

Colors: green = gold input box, red = model box (+ value read), blue = OCR text line.

    python3 scripts/render_bbox_overlays.py --data data/forms_vision_v1 \
        --pred evidence/forms_vision/V1-qwen2.5vl-3b/answers.jsonl \
        --ocr evidence/forms_vision/T1-tesseract-redteam/tesseract_forms_vision_v1.jsonl \
        --out evidence/forms_vision/bbox_overlays_v1
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

VIEWER = """<!doctype html><html><head><meta charset="utf-8"><title>Form box overlays</title>
<style>body{font:14px system-ui,sans-serif;margin:16px}figure{display:inline-block;margin:8px;vertical-align:top;width:460px}
canvas{width:100%;border:1px solid #ccc}figcaption{font-size:12px;color:#444}.k span{display:inline-block;width:12px;height:12px;margin:0 4px 0 12px}
label{margin-right:12px}</style></head><body>
<h1>Synthetic form screenshots with bounding boxes</h1>
<p>__TITLE__ · SYNTHETIC (MITRE Synthea), no real patients. Open from a local clone of the repo, because the images load from relative paths.</p>
<p class="k"><span style="background:#14a03c"></span>gold DOM input box <span style="background:#dc2828"></span>model box + value read <span style="background:#285adc"></span>OCR text line</p>
<p><label><input type="checkbox" id="g" checked> gold</label><label><input type="checkbox" id="m" checked> model</label><label><input type="checkbox" id="o" checked> OCR</label></p>
<div id="grid"></div>
<script>
const DATA = __DATA__;
function draw(fig, rec) {
  const c = fig.querySelector('canvas'), x = c.getContext('2d'), img = fig._img;
  c.width = img.naturalWidth; c.height = img.naturalHeight; x.drawImage(img, 0, 0);
  const R = (b, col, w) => { x.strokeStyle = col; x.lineWidth = w; x.strokeRect(b[0], b[1], b[2]-b[0], b[3]-b[1]); };
  x.font = '11px sans-serif';
  if (document.getElementById('o').checked) rec.ocr_lines.forEach(b => R(b, '#285adc', 1));
  if (document.getElementById('g').checked) rec.gold.forEach(f => { R(f.bbox, '#14a03c', 3); x.fillStyle = '#14783c'; x.fillText(f.field_key, f.bbox[2]+4, f.bbox[1]+10); });
  if (document.getElementById('m').checked) rec.model.forEach(p => { R(p.bbox, '#dc2828', 2); x.fillStyle = '#c81e1e'; x.fillText((p.value||'').slice(0,60), p.bbox[0]+2, p.bbox[3]+11); });
}
const grid = document.getElementById('grid'), figs = [];
for (const rec of DATA.images) {
  const fig = document.createElement('figure');
  fig.innerHTML = '<canvas></canvas><figcaption></figcaption>';
  fig.querySelector('figcaption').textContent = rec.image_id + (rec.model_total ? ` · model boxes matched ${rec.model_matched}/${rec.model_total}` : '');
  const img = new Image(); img.onload = () => draw(fig, rec); img.src = DATA.image_base + rec.image; fig._img = img;
  grid.appendChild(fig); figs.push([fig, rec]);
}
['g','m','o'].forEach(id => document.getElementById(id).onchange = () => figs.forEach(([f, r]) => f._img.complete && draw(f, r)));
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--pred", default=None, help="VLM answers.jsonl (fields[].pred.bbox)")
    ap.add_argument("--ocr", default=None, help="OCR jsonl with lines[].bbox")
    ap.add_argument("--out", required=True, help="output path stem (writes .json and .html)")
    a = ap.parse_args()
    data, out = ROOT / a.data, ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    gold = json.loads((data / "GOLD_BOXES.json").read_text())
    load = lambda p: {r["image_id"]: r for r in map(json.loads, (ROOT / p).read_text().splitlines())} if p else {}  # noqa: E731
    preds, ocr = load(a.pred), load(a.ocr)
    images = []
    for img_id in sorted(gold):
        g, p = gold[img_id], preds.get(img_id)
        model = [{"field_key": f["field_key"], "bbox": f["pred"]["bbox"], "value": f["pred"]["value"], "iou": f["iou"]}
                 for f in (p or {}).get("fields", []) if f.get("pred")]
        images.append({"image_id": img_id, "image": g["image"], "template_key": g.get("template_key"),
                       "image_sha256": hashlib.sha256((data / g["image"]).read_bytes()).hexdigest(),
                       "gold": [{"field_key": f["field_key"], "bbox": f["bbox"], "value": f["value"]} for f in g["fields"]],
                       "model": model,
                       "model_matched": sum(bool(f["box_found"]) for f in (p or {}).get("fields", [])),
                       "model_total": len((p or {}).get("fields", [])),
                       "ocr_lines": [ln["bbox"] for ln in (ocr.get(img_id) or {}).get("lines", [])]})
    doc = {"source_images": a.data, "model_answers": a.pred, "ocr": a.ocr,
           "gold_sha256": hashlib.sha256((data / "GOLD_BOXES.json").read_bytes()).hexdigest(),
           "image_base": os.path.relpath(data, out.parent) + "/", "images": images}
    body = json.dumps(doc, indent=1, sort_keys=True)
    out.with_suffix(".json").write_text(body + "\n")
    out.with_suffix(".html").write_text(VIEWER.replace("__TITLE__", a.data).replace("__DATA__", body))
    print(len(images), "images ->", out.with_suffix(".json"), out.with_suffix(".html"))


if __name__ == "__main__":
    main()
