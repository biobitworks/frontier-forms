#!/usr/bin/env python3
"""Build a YOLO-format detection dataset from the frozen SYNFORM2 renders (train/dev/test by the frozen split) so a small
local detector can be trained as a field-LOCALISATION validator. Labels come from the renderer's exact geometry (no human
annotation): 7 value-box classes (one per field) + 7 label-box classes. Images are symlinked/copied from the frozen public
dir; nothing in SYNFORM2 is modified. Writes <out>/dataset.yaml, images/{train,val,test}, labels/{train,val,test} and a
manifest with the class map and the sha256 of every label file.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_synform2 import FIELDS

W, H = 900, 560
CLASSES = [f'value:{f}' for f in FIELDS] + [f'label:{f}' for f in FIELDS]


def boxes(fields, font):
    out = []
    for i, f in enumerate(FIELDS):
        y = 110 + 58 * i
        l, t, r, b = font.getbbox(str(fields[f]) if fields[f] else ' ')
        out.append((i, 290 + l, y + t, 290 + r, y + b))
        l2, t2, r2, b2 = font.getbbox(f + ':')
        out.append((7 + i, 60 + l2, y + t2, 60 + r2, y + b2))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--synform2', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    from PIL import ImageFont
    font = ImageFont.load_default(size=18)
    S = Path(a.synform2); out = Path(a.out)
    if out.exists():
        raise SystemExit('APPEND_ONLY_OUT_EXISTS')
    inputs = [json.loads(x) for x in (S / 'public/inputs.jsonl').read_text().splitlines() if x.strip()]
    oracle = {o['case_id']: o['gold_fields'] for o in map(json.loads, (S / '.private/oracle.jsonl').read_text().splitlines())}
    split_map = {'train': 'train', 'dev': 'val', 'test': 'test'}
    manifest = {'classes': CLASSES, 'images': {}, 'label_sha256': {}}
    for r in inputs:
        sp = split_map[r['split']]
        (out / 'images' / sp).mkdir(parents=True, exist_ok=True); (out / 'labels' / sp).mkdir(parents=True, exist_ok=True)
        name = Path(r['png_relative_path']).stem
        shutil.copyfile(S / 'public' / r['png_relative_path'], out / 'images' / sp / (name + '.png'))
        lines = []
        for cls, x1, y1, x2, y2 in boxes(oracle[r['case_id']], font):
            # scan variants are rotated ≤1.5°: boxes are approximate there; the detector learns the tolerance
            lines.append(f'{cls} {((x1 + x2) / 2) / W:.6f} {((y1 + y2) / 2) / H:.6f} {(x2 - x1) / W:.6f} {(y2 - y1) / H:.6f}')
        lab = '\n'.join(lines) + '\n'
        (out / 'labels' / sp / (name + '.txt')).write_text(lab)
        manifest['images'].setdefault(sp, 0); manifest['images'][sp] += 1
        manifest['label_sha256'][name] = hashlib.sha256(lab.encode()).hexdigest()
    (out / 'dataset.yaml').write_text(f"path: {out.resolve()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n" + ''.join(f'  {i}: "{c}"\n' for i, c in enumerate(CLASSES)))
    manifest['source_root'] = json.loads((S / 'public/manifest.json').read_text())['root']
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'images': manifest['images'], 'classes': len(CLASSES), 'source_root': manifest['source_root']}))


if __name__ == '__main__':
    main()
