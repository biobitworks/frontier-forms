#!/usr/bin/env python3
"""Layout-agnostic Tesseract field extraction for an arbitrary folder of form PNGs.

Never reads gold files. For each OCR line containing "Label:" the words to the right of the colon are the
value; bbox = union of the value words (value-text box; input-box detection is not attempted).
Usage: tesseract_generic.py <png_dir> <out.jsonl> <receipt.json>
"""
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

PSM = "4"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    src, out, rec = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    ver = subprocess.run(["tesseract", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    lp = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout.splitlines()[0]
    td = Path(re.search(r'"(.+)"', lp).group(1)) / "eng.traineddata"
    pngs = sorted(p for p in src.glob("*.png"))
    rows = []
    for p in pngs:
        t0 = time.monotonic()
        tsv = subprocess.run(["tesseract", str(p), "stdout", "--psm", PSM, "tsv"], capture_output=True, text=True).stdout
        secs = time.monotonic() - t0
        lines = defaultdict(list)
        for ln in tsv.splitlines()[1:]:
            c = ln.split("\t")
            if len(c) == 12 and c[11].strip() and float(c[10]) >= 0:
                x, y, w, h = map(int, c[6:10])
                lines[(int(c[2]), int(c[3]), int(c[4]))].append((x, y, x + w, y + h, c[11], float(c[10])))
        fields, text_lines, line_boxes = [], [], []
        for key in sorted(lines, key=lambda k: (min(w[1] for w in lines[k]), k)):
            ws = sorted(lines[key])
            text_lines.append(" ".join(w[4] for w in ws))
            line_boxes.append({"text": text_lines[-1], "bbox": [min(w[0] for w in ws), min(w[1] for w in ws),
                               max(w[2] for w in ws), max(w[3] for w in ws)], "min_conf": min(w[5] for w in ws)})
            idx = next((i for i, w in enumerate(ws) if w[4].endswith(":")), None)
            if idx is None:
                continue
            label = " ".join(w[4] for w in ws[: idx + 1]).rstrip(":")
            val = ws[idx + 1:]
            if not val:
                fields.append({"label": label, "value": "", "bbox": None, "min_conf": None})
                continue
            fields.append({"label": label, "value": " ".join(w[4] for w in val),
                           "bbox": [min(w[0] for w in val), min(w[1] for w in val), max(w[2] for w in val), max(w[3] for w in val)],
                           "min_conf": min(w[5] for w in val)})
        rows.append({"image_id": p.stem, "image_sha256": sha(p.read_bytes()), "seconds": round(secs, 3),
                     "raw_output": "\n".join(text_lines), "fields": fields, "lines": line_boxes})
    out.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    rec.write_text(json.dumps({"tesseract_version": ver, "eng_traineddata_sha256": sha(td.read_bytes()), "psm": PSM,
                               "runner": "redteam/ehr/tesseract_generic.py", "runner_sha256": sha(Path(__file__).read_bytes()),
                               "images": len(rows), "output_sha256": sha(out.read_bytes()),
                               "bbox_semantics": "value-text box (union of OCR words right of the 'Label:' token); input boxes not detected",
                               "gold_read": False,
                               "note": "fields = only 'Label: value' on one OCR line; web-style forms with labels above input boxes yield "
                                       "few fields, so every OCR line with its box is also emitted under 'lines' for label-proximity scoring"}, indent=1, sort_keys=True) + "\n")
    print("DONE", len(rows))


if __name__ == "__main__":
    main()
