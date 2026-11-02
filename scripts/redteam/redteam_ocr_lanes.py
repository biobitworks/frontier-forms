#!/usr/bin/env python3
"""Claude red-team OCR comparison lane over SYNFORM2 served by the local test server.

Flow: GET /manifest.json + /inputs.jsonl from http://127.0.0.1:<port> -> verify listing sha against the manifest ->
select split/variants -> GET each PNG -> verify png sha against its FCO -> run the Apple Vision OCR binary
(scripts/redteam/apple_vision_ocr.swift, compiled) -> deterministic label/value parser -> same normalize/validate
rules as the VLM lane -> score against the private oracle (local only) -> export per-field booleans.

Arms:
  vision_ocr          Apple Vision .accurate, no language correction, deterministic geometric parser
Negative control: parser run on an image whose labels are absent (blank page) must yield all MISSING.
Apple Vision is the same on-device recognizer Preview/Live Text use; Preview itself is not scriptable headlessly.
"""
from __future__ import annotations
import argparse, hashlib, json, platform, re, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from redteam_forms_vlm import FIELDS, norm, validate, draft_fhir, canon, sha, jsonl


def http_get(base, path):
    with urllib.request.urlopen(base + '/' + path, timeout=30) as r:
        return r.read()


def run_ocr(binary, paths, batch=16):
    out = []
    for i in range(0, len(paths), batch):
        chunk = paths[i:i + batch]
        p = subprocess.run([binary] + [str(x) for x in chunk], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        if p.returncode != 0:
            raise RuntimeError('OCR_BINARY_FAILED ' + p.stderr.decode()[-300:])
        out.extend(json.loads(p.stdout.decode()))
    return out


def parse_fields(lines):
    """Geometric parser: a label line is one whose text starts with a known label; its value is either the remainder
    after ':' on the same observation or the nearest observation to the right on the same row."""
    found = {}
    norm_lines = [dict(l, t=re.sub(r'\s+', ' ', l['text']).strip()) for l in lines]
    for f in FIELDS:
        lab = f.lower()
        cands = [l for l in norm_lines if l['t'].lower().startswith(lab)]
        if not cands:
            found[f] = None
            continue
        l = max(cands, key=lambda c: c['confidence'])
        # Vision sometimes reads the trailing colon as ® / • / . ; strip such label punctuation before deciding
        rest = l['t'][len(f):].strip().lstrip(':®•·.,;-_ ').strip()
        if rest:
            found[f] = rest
            continue
        cy = l['y'] + l['h'] / 2
        right = [m for m in norm_lines if m is not l and m['x'] > l['x'] + l['w'] * 0.8 and abs((m['y'] + m['h'] / 2) - cy) < max(l['h'], m['h']) * 0.8]
        found[f] = min(right, key=lambda m: m['x'])['t'] if right else None
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--server', default='http://127.0.0.1:8765')
    ap.add_argument('--dataset-dir', required=True, help='local SYNFORM2 dir (for .private oracle only)')
    ap.add_argument('--ocr-bin', required=True)
    ap.add_argument('--split', default='test')
    ap.add_argument('--variants', default='clean,scan')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--tag', default='OCR')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    t_start = time.time()
    manifest = json.loads(http_get(a.server, 'manifest.json'))
    listing = http_get(a.server, 'inputs.jsonl')
    assert sha(listing) == manifest['public_input_listing_sha256'], 'SERVED_LISTING_SHA_MISMATCH'
    inputs = [json.loads(x) for x in listing.decode().splitlines() if x.strip()]
    variants = a.variants.split(',')
    sel = [r for r in inputs if (a.split == 'all' or r.get('split') == a.split) and (a.variants == 'all' or r.get('variant') in variants)]
    for r in sel:
        r.setdefault('split', a.split); r.setdefault('variant', 'hidden')
    if a.limit:
        sel = sel[:a.limit]
    oracle = {o['case_id']: o['gold_fields'] for o in jsonl(Path(a.dataset_dir) / '.private/oracle.jsonl')}
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    stem = f'{a.tag}_apple-vision_synform2_{a.split}'
    lp, pp = out_dir / (stem + '_LOCAL.jsonl'), out_dir / (stem + '_PUBLIC.jsonl')
    if lp.exists() or pp.exists():
        raise SystemExit('APPEND_ONLY')
    with tempfile.TemporaryDirectory(prefix='synform2-ocr-') as td:
        paths, fetched = [], {}
        t_fetch = time.monotonic()
        for r in sel:
            b = http_get(a.server, r['png_relative_path'])
            if sha(b) != r['png_sha256']:
                raise SystemExit('SERVED_PNG_SHA_MISMATCH ' + r['case_id'])
            p = Path(td) / Path(r['png_relative_path']).name; p.write_bytes(b); paths.append(p); fetched[str(p)] = r
        fetch_s = round(time.monotonic() - t_fetch, 3)
        # negative control: blank image must parse to all MISSING
        from PIL import Image
        blank = Path(td) / 'blank.png'; Image.new('RGB', (900, 560), 'white').save(blank)
        t_ocr = time.monotonic()
        ocr = run_ocr(a.ocr_bin, paths + [blank])
        ocr_s = round(time.monotonic() - t_ocr, 3)
        blank_fields = parse_fields(ocr[-1]['lines'])
        control_ok = all(v is None for v in blank_fields.values())
        with lp.open('x') as lf, pp.open('x') as pf:
            for e in ocr[:-1]:
                r = fetched[e['path']]; gold = oracle[r.get('image_id', r['case_id'])]
                fields = parse_fields(e['lines']) if not e.get('error') else {f: None for f in FIELDS}
                val = validate(fields, r['case_id'])
                correct = {f: norm(f, fields[f]) == norm(f, gold.get(f)) for f in FIELDS}
                admitted = {f: val[f] == 'OK' and val['Synthetic case'] == 'OK' for f in FIELDS}
                draft = draft_fhir({f: fields[f] if admitted[f] else None for f in FIELDS}, r['input_fco_id'])
                gold_draft = draft_fhir(gold, r['input_fco_id'])
                local = {'case_id': r['case_id'], 'variant': r['variant'], 'split': r['split'], 'input_fco_id': r['input_fco_id'], 'arm': 'vision_ocr',
                         'ocr_lines': e['lines'], 'ocr_error': e.get('error'), 'ocr_seconds': e.get('seconds'), 'fields': fields, 'gold': gold,
                         'validation': val, 'correct': correct, 'admitted': admitted}
                lf.write(json.dumps(local, sort_keys=True) + '\n')
                pub = {'case_id': r['case_id'], 'variant': r['variant'], 'split': r['split'], 'input_fco_id': r['input_fco_id'], 'arm': 'vision_ocr',
                       'ocr_error': e.get('error'), 'ocr_seconds': e.get('seconds'), 'n_lines': len(e['lines']),
                       'mean_confidence': round(sum(l['confidence'] for l in e['lines']) / len(e['lines']), 4) if e['lines'] else None,
                       'validation': val, 'correct': correct, 'parsed': {f: fields[f] is not None for f in FIELDS}, 'admitted': admitted,
                       'false_admissions': sum(1 for f in FIELDS if admitted[f] and not correct[f]), 'correct_count': sum(correct.values()),
                       'draft_patient_matches_gold': draft['entry'][0]['resource'] == gold_draft['entry'][0]['resource'],
                       'draft_encounter_matches_gold': draft['entry'][1]['resource'] == gold_draft['entry'][1]['resource']}
                pf.write(json.dumps(pub, sort_keys=True) + '\n')
                print('OCR', r['case_id'][-8:], r['variant'], 'correct', pub['correct_count'], '/7 false_adm', pub['false_admissions'], flush=True)
    meta = {'schema': 'redteam.ocr_lane_run.v1', 'engine': 'Apple Vision VNRecognizeTextRequest .accurate, usesLanguageCorrection=false, en-US',
            'ocr_binary_sha256': sha(Path(a.ocr_bin).read_bytes()), 'dataset': manifest['dataset'], 'form_root': manifest['root'], 'split': a.split, 'variants': variants,
            'images': len(sel), 'served_from': a.server, 'fetch_seconds': fetch_s, 'ocr_seconds_total': ocr_s, 'blank_page_control_all_missing': control_ok,
            'host': platform.node(), 'macos': platform.mac_ver()[0], 'python': sys.version.split()[0], 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t_start)),
            'finished_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'wall_seconds': round(time.time() - t_start, 1),
            'public_sha256': sha(pp.read_bytes()), 'local_sha256': sha(lp.read_bytes()), 'local_file_export': 'NOT_AUTHORIZED_CONTAINS_ORACLE'}
    (out_dir / (stem + '_META.json')).write_text(json.dumps(meta, sort_keys=True, indent=2) + '\n')
    print('RUN_DONE', json.dumps(meta, sort_keys=True))


if __name__ == '__main__':
    main()
