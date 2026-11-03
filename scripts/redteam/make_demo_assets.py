#!/usr/bin/env python3
"""Build presentation assets for the synthetic-form lane (runs on the host that holds the frozen renders).

For a small fixed selection (first 3 SYNFORM2 test cases × clean/scan, plus planted-error variants E3/E6/E7/V2 of the
first case from SYNFORM2-ERR) it writes, under --out:
  img/<id>.png            the frozen render (byte-identical copy; sha256 recorded)
  ann/<id>.json           per-image annotation: renderer GT boxes, Apple Vision OCR line boxes, YOLOv8n detector boxes,
                          and per-field printed / Apple Vision / qwen2.5vl values with validation verdicts
  overlay/<id>.png        the render with GT (green dashed), Apple Vision (blue) and detector (orange) boxes drawn on it
  pdf/<id>.pdf            the render as a one-page PDF (what a scanned/faxed page would look like)
  pdf/demo_overlays.pdf   all overlays in one multi-page PDF
  screenshots/<id>.png    headless-Chrome screenshot of the local form server viewer page (/viewer.html?id=<id>)
  screenshots/<id>.pdf    headless-Chrome print-to-PDF of the same page
  manifest.json           sha256 of every asset + source roots + model weights digests
All data is synthetic (MITRE Synthea sample). Values shown are the models' actual answers.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

FIELDS = ('Synthetic case', 'Patient first', 'Patient last', 'Birth date', 'Gender', 'Encounter date', 'Visit class')
W, H = 900, 560
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jsonl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]


def gt_boxes(fields):
    from PIL import ImageFont
    font = ImageFont.load_default(size=18); out = {}
    for i, f in enumerate(FIELDS):
        y = 110 + 58 * i
        l, t, r, b = font.getbbox(str(fields[f]) if fields[f] else ' ')
        out[f] = [290 + l, y + t, 290 + r, y + b]
    return out


def vision_px(l):
    return [l['x'] * W, (1 - l['y'] - l['h']) * H, (l['x'] + l['w']) * W, (1 - l['y']) * H]


def norm(v):
    return None if v is None else ' '.join(str(v).split()).lower()


def overlay(src, a, dst):
    from PIL import Image, ImageDraw
    im = Image.open(src).convert('RGB'); d = ImageDraw.Draw(im)
    for f, b in a['gt_boxes'].items():
        for k in range(int(b[0]), int(b[2]), 6):
            d.line([k, b[1], min(k + 3, b[2]), b[1]], fill=(21, 128, 61), width=2); d.line([k, b[3], min(k + 3, b[2]), b[3]], fill=(21, 128, 61), width=2)
        d.line([b[0], b[1], b[0], b[3]], fill=(21, 128, 61), width=2); d.line([b[2], b[1], b[2], b[3]], fill=(21, 128, 61), width=2)
    for l in a['ocr_boxes']:
        d.rectangle(l['box'], outline=(28, 92, 171), width=1)
    for det in a['detector_boxes']:
        d.rectangle(det['box'], outline=(194, 65, 12), width=2); d.text((det['box'][2] + 3, det['box'][1]), f"{det['conf']:.2f}", fill=(194, 65, 12))
    d.text((24, 540), 'green dashed = renderer GT   blue = Apple Vision OCR   orange = YOLOv8n detector (conf)', fill=(55, 65, 81))
    im.save(dst)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--synform2', required=True)
    ap.add_argument('--err', required=True)
    ap.add_argument('--lanes', required=True)
    ap.add_argument('--detector', required=True, help='dir with detections_test.json / detections_err.json')
    ap.add_argument('--out', required=True)
    ap.add_argument('--port', type=int, default=8767)
    ap.add_argument('--server-script', required=True)
    a = ap.parse_args()
    S2, E, L, Dt, out = Path(a.synform2), Path(a.err), Path(a.lanes), Path(a.detector), Path(a.out)
    for sub in ('img', 'ann', 'overlay', 'pdf', 'screenshots'):
        (out / sub).mkdir(parents=True, exist_ok=True)
    s2_in = {r['input_fco_id']: r for r in jsonl(S2 / 'public/inputs.jsonl')}
    e_in = {r['input_fco_id']: r for r in jsonl(E / 'public/inputs.jsonl')}
    s2_or = {o['case_id']: o for o in jsonl(S2 / '.private/oracle.jsonl')}
    e_or = {o['case_id']: o for o in jsonl(E / '.private/oracle.jsonl')}
    planted = {p['image_id']: p for p in jsonl(E / '.private/planted.jsonl')}
    ocr = {r['input_fco_id']: r for p in [L / 'OCR_apple-vision_synform2_test_LOCAL.jsonl', L / 'OCRERR_apple-vision_synform2_all_LOCAL.jsonl'] for r in jsonl(p)}
    vlm = {r['input_fco_id']: r for p in [L / 'VLM_qwen2.5vl_3b_synform2_test_LOCAL.jsonl', L / 'VLMERR_qwen2.5vl_3b_synform2_all_LOCAL.jsonl'] if p.exists() for r in jsonl(p)}
    det_t = json.loads((Dt / 'detections_test.json').read_text()); det_e = json.loads((Dt / 'detections_err.json').read_text())
    test_cases = sorted({r['case_id'] for r in s2_in.values() if r['split'] == 'test'})[:3]
    picks = []
    for c in test_cases:
        for v in ('clean', 'scan'):
            r = next(x for x in s2_in.values() if x['case_id'] == c and x['variant'] == v)
            picks.append(('synform2', r, f"{c}_{v}", s2_or[c]['gold_fields'], f'SYNFORM2 test · {v}', det_t.get(Path(r['png_relative_path']).stem, [])))
    first = test_cases[0]
    for var in ('E3_case_id_swap', 'E6_name_swap', 'E7_digit_flip', 'V2_scan_sigma25'):
        pl = next(p for p in planted.values() if p['case_id'] == first and p['variant'] == var)
        r = next(x for x in e_in.values() if x['image_id'] == pl['image_id'])
        picks.append(('synform2_err', r, f"{first}_{var}", e_or[pl['image_id']]['gold_fields'], f'SYNFORM2-ERR · planted {var} (fields changed: {", ".join(pl["planted_fields"]) or "none"})', det_e.get(pl['image_id'], [])))
    manifest = {'schema': 'redteam.demo_assets.v1', 'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'data': 'SYNTHETIC (MITRE Synthea sample renders)',
                'sources': {'synform2_root': json.loads((S2 / 'public/manifest.json').read_text())['root'], 'synform2_err_root': json.loads((E / 'public/manifest.json').read_text())['root']},
                'models': {'apple_vision': 'VNRecognizeTextRequest .accurate', 'qwen2.5vl:3b': 'Ollama digest fb90415cde1e', 'yolov8n_field_detector': json.loads((Dt / 'final_receipt.json').read_text()).get('best_weights_sha256')},
                'assets': {}}
    overlays = []
    for ds, r, ident, printed, title, dets in picks:
        root = S2 if ds == 'synform2' else E
        src = root / 'public' / r['png_relative_path']
        assert sha(src) == r['png_sha256'], 'PNG_SHA_MISMATCH'
        shutil.copyfile(src, out / 'img' / f'{ident}.png')
        o = ocr.get(r['input_fco_id']); v = vlm.get(r['input_fco_id'])
        fields = {}
        for f in FIELDS:
            vv = (v or {}).get('fields_extract', {}).get(f) if v else None
            fields[f] = {'printed': printed[f], 'ocr': (o or {}).get('fields', {}).get(f), 'vlm': vv, 'vlm_correct_vs_printed': v is not None and norm(vv) == norm(printed[f]),
                         'validation': (v or {}).get('validation', {}).get(f, 'NOT_RUN') if v else 'NOT_RUN'}
        ann = {'id': ident, 'title': title, 'subtitle': f'case {r["case_id"]} · input FCO {r["input_fco_id"][:20]}… · png sha256 {r["png_sha256"][:16]}…', 'image': f'img/{ident}.png',
               'dataset': ds, 'gt_boxes': gt_boxes(printed), 'ocr_boxes': [{'text': l['text'], 'conf': l['confidence'], 'box': vision_px(l)} for l in (o or {}).get('ocr_lines', [])],
               'detector_boxes': [d for d in dets if d['class'].startswith('value:')], 'fields': fields, 'vlm_available': v is not None}
        (out / 'ann' / f'{ident}.json').write_text(json.dumps(ann, indent=1, sort_keys=True) + '\n')
        overlays.append(overlay(src, ann, out / 'overlay' / f'{ident}.png'))
        from PIL import Image
        Image.open(src).convert('RGB').save(out / 'pdf' / f'{ident}.pdf', 'PDF', resolution=100.0)
    overlays[0].save(out / 'pdf' / 'demo_overlays.pdf', 'PDF', resolution=100.0, save_all=True, append_images=overlays[1:])
    srv = subprocess.Popen([sys.executable, a.server_script, '--root', str(out), '--port', str(a.port)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(1.5)
    try:
        for _, _, ident, *_ in picks:
            url = f'http://127.0.0.1:{a.port}/viewer.html?id={ident}'
            subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--window-size=1440,820', f'--screenshot={out / "screenshots" / (ident + ".png")}', url], check=True, timeout=60, capture_output=True)
            subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', f'--print-to-pdf={out / "screenshots" / (ident + ".pdf")}', url], check=True, timeout=60, capture_output=True)
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--window-size=900,500', f'--screenshot={out / "screenshots" / "index.png"}', f'http://127.0.0.1:{a.port}/'], check=True, timeout=60, capture_output=True)
    finally:
        srv.terminate()
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name != 'manifest.json':
            manifest['assets'][p.relative_to(out).as_posix()] = {'sha256': sha(p), 'bytes': p.stat().st_size}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print('DEMO_ASSETS', len(manifest['assets']), 'images', len(picks))


if __name__ == '__main__':
    main()
