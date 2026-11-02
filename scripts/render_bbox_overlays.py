#!/usr/bin/env python3
"""Draw bounding-box overlays on the synthetic form screenshots and write an HTML gallery.

Each overlay shows:
  green  gold DOM input box (with field key)
  red    a model's predicted box (e.g. V1 qwen2.5vl:3b), with the value it read
  blue   OCR text-line boxes (e.g. T1 Tesseract), thin
Inputs are committed evidence only; everything is synthetic.

    python3 scripts/render_bbox_overlays.py --data data/forms_vision_v1 \
        --pred evidence/forms_vision/V1-qwen2.5vl-3b/answers.jsonl \
        --ocr evidence/forms_vision/T1-tesseract-redteam/tesseract_forms_vision_v1.jsonl \
        --out evidence/forms_vision/overlays_v1
"""
import argparse
import html
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--pred", default=None, help="VLM answers.jsonl (fields[].pred.bbox)")
    ap.add_argument("--ocr", default=None, help="OCR jsonl with lines[].bbox")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data, out = ROOT / a.data, ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    gold = json.loads((data / "GOLD_BOXES.json").read_text())
    preds = {}
    if a.pred:
        for line in (ROOT / a.pred).read_text().splitlines():
            r = json.loads(line)
            preds[r["image_id"]] = r
    ocr = {}
    if a.ocr:
        for line in (ROOT / a.ocr).read_text().splitlines():
            r = json.loads(line)
            ocr[r["image_id"]] = r
    cards = []
    for img_id in sorted(gold):
        g = gold[img_id]
        im = Image.open(data / g["image"]).convert("RGB")
        d = ImageDraw.Draw(im)
        for ln in (ocr.get(img_id) or {}).get("lines", []):
            d.rectangle(ln["bbox"], outline=(40, 90, 220), width=1)
        for f in g["fields"]:
            d.rectangle(f["bbox"], outline=(20, 160, 60), width=3)
            d.text((f["bbox"][2] + 4, f["bbox"][1]), f["field_key"], fill=(20, 120, 50))
        p = preds.get(img_id)
        found = total = 0
        if p:
            for f in p["fields"]:
                total += 1
                found += bool(f["box_found"])
                if f.get("pred"):
                    b = f["pred"]["bbox"]
                    d.rectangle(b, outline=(220, 40, 40), width=2)
                    d.text((b[0] + 2, b[3] + 1), (f["pred"]["value"] or "")[:60], fill=(200, 30, 30))
        name = Path(g["image"]).stem + ".overlay.png"
        im.save(out / name, optimize=True)
        cards.append((img_id, name, g.get("template_key"), found, total))
    rows = "".join(
        f'<figure><a href="{html.escape(n)}"><img loading="lazy" src="{html.escape(n)}" alt="{html.escape(i)}"></a>'
        f'<figcaption>{html.escape(i)}<br>{html.escape(t or "")}' + (f" · model boxes matched {f}/{tt}" if tt else "") + "</figcaption></figure>"
        for i, n, t, f, tt in cards)
    (out / "index.html").write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>Form box overlays</title>"
        "<style>body{font:14px system-ui;margin:16px}figure{display:inline-block;width:300px;margin:6px;vertical-align:top}"
        "img{width:100%;border:1px solid #ccc}.k span{display:inline-block;width:12px;height:12px;margin:0 4px 0 12px}</style></head><body>"
        f"<h1>Synthetic form screenshots with bounding boxes</h1><p>{html.escape(a.data)} · SYNTHETIC (MITRE Synthea), no real patients.</p>"
        "<p class='k'><span style='background:#14a03c'></span>gold DOM input box"
        "<span style='background:#dc2828'></span>model predicted box + value read"
        "<span style='background:#285adc'></span>OCR text line</p>" + rows + "</body></html>")
    print(len(cards), "overlays ->", out)


if __name__ == "__main__":
    main()
