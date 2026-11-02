#!/usr/bin/env python3
"""Stage-wise demo/evidence assets for the synthetic-form lane; each stage is committed and pushed by the caller.

Requires docs/demo/ann/*.json from make_demo_assets.py (v1). Adds per-model answers to every annotation and then:
  stage answers     ann/<id>.json gains answers{qwen2.5vl:3b, apple_vision_parser, qwen2.5:1.5b, qwen3:1.7b}
  stage chrome      screenshots/models/<id>__<model>__boxes|noboxes.png and .pdf via headless Chrome against the local
                    form server (one filled intake form per model, overlays on or off)
  stage preview     open pdf/<id>.pdf in macOS Preview, capture ONLY Preview's window (CGWindowID, no full-screen capture),
                    run Apple Vision OCR on that capture, parse + score → preview/<id>.png and preview/preview_ocr.json
  stage boxocr      Apple Vision OCR on the clean render vs the same render with bounding boxes drawn (overlay/<id>.png)
                    → ocr_boxes_vs_clean.json (does box clutter change OCR field fidelity?)
All data synthetic; values are the models' actual answers.
"""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys, time
from pathlib import Path

FIELDS = ('Synthetic case', 'Patient first', 'Patient last', 'Birth date', 'Gender', 'Encounter date', 'Visit class')
MODELS = ('qwen2.5vl:3b', 'apple_vision_parser', 'qwen2.5:1.5b', 'qwen3:1.7b')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
WINID_SWIFT = r'''
import Foundation
import CoreGraphics
let opts = CGWindowListOption(arrayLiteral: .optionOnScreenOnly, .excludeDesktopElements)
let list = CGWindowListCopyWindowInfo(opts, kCGNullWindowID) as? [[String: Any]] ?? []
let want = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : ""
for w in list {
  let owner = w[kCGWindowOwnerName as String] as? String ?? ""
  let name = w[kCGWindowName as String] as? String ?? ""
  let layer = w[kCGWindowLayer as String] as? Int ?? 99
  if owner == "Preview" && layer == 0 && (want.isEmpty || name.contains(want)) {
    print(w[kCGWindowNumber as String] as? Int ?? 0); exit(0)
  }
}
print(0)
'''


def jsonl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def norm(v): return None if v is None else ' '.join(str(v).split()).lower()


def parse_fields(lines):
    found = {}
    nl = [dict(l, t=re.sub(r'\s+', ' ', l['text']).strip()) for l in lines]
    for f in FIELDS:
        cands = [l for l in nl if l['t'].lower().startswith(f.lower())]
        if not cands:
            found[f] = None; continue
        l = max(cands, key=lambda c: c['confidence'])
        rest = l['t'][len(f):].strip().lstrip(':®•·.,;-_ ').strip()
        if rest:
            found[f] = rest; continue
        cy = l['y'] + l['h'] / 2
        right = [m for m in nl if m is not l and m['x'] > l['x'] + l['w'] * 0.8 and abs((m['y'] + m['h'] / 2) - cy) < max(l['h'], m['h']) * 0.8]
        found[f] = min(right, key=lambda m: m['x'])['t'] if right else None
    return found


def ocr(binary, paths):
    p = subprocess.run([binary] + [str(x) for x in paths], capture_output=True, timeout=600)
    if p.returncode:
        raise RuntimeError(p.stderr.decode()[-300:])
    return json.loads(p.stdout.decode())


def score(fields, printed):
    return {f: norm(fields.get(f)) == norm(printed.get(f)) for f in FIELDS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--demo', required=True)
    ap.add_argument('--lanes', required=True)
    ap.add_argument('--stage', required=True, choices=['answers', 'chrome', 'preview', 'boxocr'])
    ap.add_argument('--ocr-bin', default='')
    ap.add_argument('--port', type=int, default=8768)
    ap.add_argument('--server-script', default='')
    ap.add_argument('--inputs', nargs='*', default=[], help='public inputs.jsonl files (SYNFORM2, SYNFORM2-ERR) to map png sha -> input FCO')
    a = ap.parse_args()
    D, L = Path(a.demo), Path(a.lanes)
    anns = {p.stem: json.loads(p.read_text()) for p in sorted((D / 'ann').glob('*.json'))}
    if a.stage == 'answers':
        src = {'qwen2.5vl:3b': [L / 'VLM_qwen2.5vl_3b_synform2_test_LOCAL.jsonl', L / 'VLMERR_qwen2.5vl_3b_synform2_all_LOCAL.jsonl'],
               'apple_vision_parser': [L / 'OCR_apple-vision_synform2_test_LOCAL.jsonl', L / 'OCRERR_apple-vision_synform2_all_LOCAL.jsonl'],
               'qwen2.5:1.5b': [L / 'MAP_qwen2.5_1.5b_synform2_test_LOCAL.jsonl'], 'qwen3:1.7b': [L / 'MAP_qwen3_1.7b_synform2_test_LOCAL.jsonl']}
        by = {m: {r['input_fco_id']: r for p in ps if p.exists() for r in jsonl(p)} for m, ps in src.items()}
        # NOTE: SYNFORM2-ERR 'clean' controls are byte-identical to SYNFORM2 clean renders, so the png sha alone is
        # ambiguous; resolve within the annotation's own dataset (inputs given in order SYNFORM2, SYNFORM2-ERR).
        import hashlib
        by_png = {ds: {r['png_sha256']: r['input_fco_id'] for r in jsonl(p)} for ds, p in zip(('synform2', 'synform2_err'), a.inputs)}
        for ident, ann in anns.items():
            fco = by_png[ann['dataset']].get(hashlib.sha256((D / ann['image']).read_bytes()).hexdigest())
            ann['input_fco_id'] = fco
            ann['answers'] = {}
            for m_, rows in by.items():
                r = rows.get(fco) if fco else None
                if r is None:
                    ann['answers'][m_] = None; continue
                vals = r.get('fields_extract') or r.get('fields')
                ann['answers'][m_] = {f: vals.get(f) for f in FIELDS}
            (D / 'ann' / f'{ident}.json').write_text(json.dumps(ann, indent=1, sort_keys=True) + '\n')
        summary = {ident: {m: (None if v is None else sum(score(v, {f: ann['fields'][f]['printed'] for f in FIELDS}).values())) for m, v in ann['answers'].items()} for ident, ann in anns.items()}
        (D / 'answers_by_model.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
        print('ANSWERS', json.dumps(summary))
    elif a.stage == 'chrome':
        out = D / 'screenshots' / 'models'; out.mkdir(parents=True, exist_ok=True)
        srv = subprocess.Popen([sys.executable, a.server_script, '--root', str(D), '--port', str(a.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5); n = 0
        try:
            for ident in anns:
                for m in MODELS:
                    for bx in ('1', '0'):
                        url = f'http://127.0.0.1:{a.port}/viewer.html?id={ident}&model={m}&boxes={bx}'
                        stem = f"{ident}__{m.replace(':', '_')}__{'boxes' if bx == '1' else 'noboxes'}"
                        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--window-size=1440,820', f'--screenshot={out / (stem + ".png")}', url], check=True, timeout=60, capture_output=True)
                        if bx == '1':
                            subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', f'--print-to-pdf={out / (stem + ".pdf")}', url], check=True, timeout=60, capture_output=True)
                        n += 1
            subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--window-size=1200,700', f'--screenshot={D / "screenshots" / "index_models.png"}', f'http://127.0.0.1:{a.port}/'], check=True, timeout=60, capture_output=True)
        finally:
            srv.terminate()
        print('CHROME_SCREENSHOTS', n)
    elif a.stage == 'preview':
        out = D / 'preview'; out.mkdir(parents=True, exist_ok=True)
        winid = out / 'winid'
        (out / 'winid.swift').write_text(WINID_SWIFT)
        subprocess.run(['swiftc', '-O', '-o', str(winid), str(out / 'winid.swift')], check=True, capture_output=True, timeout=300)
        (out / 'winid.swift').unlink()
        results = {}
        for ident, ann in anns.items():
            pdf = (D / 'pdf' / f'{ident}.pdf').resolve()
            subprocess.run(['open', '-a', 'Preview', str(pdf)], check=True)
            wid = 0
            for _ in range(20):
                time.sleep(0.5)
                wid = int(subprocess.run([str(winid), pdf.name], capture_output=True, text=True).stdout.strip() or 0)
                if wid:
                    break
            shot = out / f'{ident}.png'
            status = 'NO_WINDOW'
            if wid:
                time.sleep(0.8)
                r = subprocess.run(['screencapture', '-x', '-o', f'-l{wid}', str(shot)], capture_output=True)
                status = 'CAPTURED' if r.returncode == 0 and shot.exists() and shot.stat().st_size > 0 else f'CAPTURE_FAILED:{r.stderr.decode()[:120]}'
            subprocess.run(['osascript', '-e', f'tell application "Preview" to close (every window whose name contains "{pdf.name}")'], capture_output=True)
            res = {'window_id': wid, 'status': status}
            if status == 'CAPTURED':
                o = ocr(a.ocr_bin, [shot])[0]
                f = parse_fields(o['lines'])
                sc = score(f, {k: ann['fields'][k]['printed'] for k in FIELDS})
                res.update({'fields': f, 'correct': sc, 'correct_count': sum(sc.values()), 'ocr_lines': len(o['lines']), 'ocr_seconds': o.get('seconds')})
            results[ident] = res
            print('PREVIEW', ident, res.get('status'), res.get('correct_count'), flush=True)
        (out / 'preview_ocr.json').write_text(json.dumps({'schema': 'redteam.preview_ocr.v1', 'pipeline': 'PNG render -> one-page PDF -> macOS Preview window -> screencapture -l<window> -> Apple Vision OCR -> geometric parser',
                                                         'results': results, 'images': len(results), 'captured': sum(1 for r in results.values() if r['status'] == 'CAPTURED'),
                                                         'fields_correct': sum(r.get('correct_count', 0) for r in results.values()), 'fields_total': 7 * len(results)}, indent=1, sort_keys=True) + '\n')
    elif a.stage == 'boxocr':
        ids = list(anns)
        clean = ocr(a.ocr_bin, [D / 'img' / f'{i}.png' for i in ids]); boxed = ocr(a.ocr_bin, [D / 'overlay' / f'{i}.png' for i in ids])
        rows = {}
        for i, c, b in zip(ids, clean, boxed):
            printed = {k: anns[i]['fields'][k]['printed'] for k in FIELDS}
            fc, fb = parse_fields(c['lines']), parse_fields(b['lines'])
            sc, sb = score(fc, printed), score(fb, printed)
            rows[i] = {'clean': {'fields': fc, 'correct_count': sum(sc.values()), 'lines': len(c['lines'])}, 'with_boxes': {'fields': fb, 'correct_count': sum(sb.values()), 'lines': len(b['lines'])},
                       'fields_changed_by_boxes': [k for k in FIELDS if sc[k] != sb[k]]}
            print('BOXOCR', i, rows[i]['clean']['correct_count'], rows[i]['with_boxes']['correct_count'], flush=True)
        (D / 'ocr_boxes_vs_clean.json').write_text(json.dumps({'schema': 'redteam.ocr_boxes_vs_clean.v1', 'engine': 'Apple Vision .accurate', 'images': len(ids),
                                                              'clean_fields_correct': sum(r['clean']['correct_count'] for r in rows.values()),
                                                              'boxes_fields_correct': sum(r['with_boxes']['correct_count'] for r in rows.values()), 'fields_total': 7 * len(ids), 'rows': rows}, indent=1, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
