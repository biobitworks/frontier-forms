#!/usr/bin/env python3
"""Claude red-team VLM lane over SYNFORM2 served by the local test server (same fetch/verify path as the OCR lane).

Arms per image: extract (single pass JSON), reread challenge (field-by-field), admission = agree ∧ valid ∧ FCO identity.
Uses the functions of redteam_forms_vlm.py so the scorer is byte-for-byte the one used on forms12.
"""
from __future__ import annotations
import argparse, json, platform, sys, tempfile, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from redteam_forms_vlm import FIELDS, norm, validate, draft_fhir, vlm, EXTRACT_PROMPT, FIELD_PROMPT, sha, jsonl, OLLAMA


def http_get(base, path):
    with urllib.request.urlopen(base + '/' + path, timeout=30) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--server', default='http://127.0.0.1:8765')
    ap.add_argument('--dataset-dir', required=True)
    ap.add_argument('--model', default='qwen2.5vl:3b')
    ap.add_argument('--split', default='test')
    ap.add_argument('--variants', default='clean,scan')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--tag', default='VLM')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--no-challenge', action='store_true')
    a = ap.parse_args()
    t_start = time.time()
    manifest = json.loads(http_get(a.server, 'manifest.json'))
    listing = http_get(a.server, 'inputs.jsonl')
    assert sha(listing) == manifest['public_input_listing_sha256'], 'SERVED_LISTING_SHA_MISMATCH'
    inputs = [json.loads(x) for x in listing.decode().splitlines() if x.strip()]
    variants = a.variants.split(',')
    sel = [r for r in inputs if r['split'] == a.split and r['variant'] in variants]
    if a.limit:
        sel = sel[:a.limit]
    oracle = {o['case_id']: o['gold_fields'] for o in jsonl(Path(a.dataset_dir) / '.private/oracle.jsonl')}
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{a.tag}_{a.model.replace(':', '_')}_synform2_{a.split}"
    lp, pp = out_dir / (stem + '_LOCAL.jsonl'), out_dir / (stem + '_PUBLIC.jsonl')
    if lp.exists() or pp.exists():
        raise SystemExit('APPEND_ONLY')
    with lp.open('x') as lf, pp.open('x') as pf:
        for i, r in enumerate(sel):
            png = http_get(a.server, r['png_relative_path'])
            if sha(png) != r['png_sha256']:
                raise SystemExit('SERVED_PNG_SHA_MISMATCH ' + r['case_id'])
            gold = oracle[r['case_id']]
            e1 = vlm(a.model, EXTRACT_PROMPT, png)
            f1 = {f: e1['parsed'].get(f) for f in FIELDS}
            reread = {}
            if not a.no_challenge:
                for f in FIELDS:
                    rr = vlm(a.model, FIELD_PROMPT.format(f=f), png, num_predict=60)
                    reread[f] = {'value': (rr['parsed'] or {}).get('value'), 'status': rr['status'], 'wall_seconds': rr['wall_seconds'],
                                 'tokens': (rr.get('prompt_tokens') or 0) + (rr.get('completion_tokens') or 0)}
            f3 = {f: (reread.get(f) or {}).get('value') for f in FIELDS}
            val = validate(f1, r['case_id'])
            agree = {f: norm(f, f1[f]) is not None and norm(f, f1[f]) == norm(f, f3[f]) for f in FIELDS}
            identity_ok = val['Synthetic case'] == 'OK'
            admitted = {f: bool((agree[f] if not a.no_challenge else True) and val[f] == 'OK' and identity_ok) for f in FIELDS}
            correct = {f: norm(f, f1[f]) == norm(f, gold.get(f)) for f in FIELDS}
            correct3 = {f: norm(f, f3[f]) == norm(f, gold.get(f)) for f in FIELDS}
            draft = draft_fhir({f: f1[f] if admitted[f] else None for f in FIELDS}, r['input_fco_id']); gold_draft = draft_fhir(gold, r['input_fco_id'])
            local = {'case_id': r['case_id'], 'variant': r['variant'], 'split': r['split'], 'input_fco_id': r['input_fco_id'], 'model': a.model, 'extract': e1, 'reread': reread,
                     'fields_extract': f1, 'fields_reread': f3, 'gold': gold, 'validation': val, 'agree': agree, 'admitted': admitted, 'correct_extract': correct, 'correct_reread': correct3}
            lf.write(json.dumps(local, sort_keys=True) + '\n'); lf.flush()
            pub = {'case_id': r['case_id'], 'variant': r['variant'], 'split': r['split'], 'input_fco_id': r['input_fco_id'], 'model': a.model, 'arm': 'vlm_extract',
                   'status': e1['status'], 'validation': val, 'agree': agree, 'admitted': admitted, 'correct_extract': correct, 'correct_reread': correct3,
                   'parsed': {f: f1[f] is not None for f in FIELDS}, 'identity_check': 'PASS' if identity_ok else 'ABSTAIN',
                   'false_admissions': sum(1 for f in FIELDS if admitted[f] and not correct[f]), 'admitted_count': sum(admitted.values()), 'correct_count': sum(correct.values()),
                   'tokens_extract': (e1.get('prompt_tokens') or 0) + (e1.get('completion_tokens') or 0), 'tokens_challenge': sum(v['tokens'] for v in reread.values()),
                   'wall_extract': e1['wall_seconds'], 'wall_challenge': round(sum(v['wall_seconds'] for v in reread.values()), 3),
                   'draft_patient_matches_gold': draft['entry'][0]['resource'] == gold_draft['entry'][0]['resource'],
                   'draft_encounter_matches_gold': draft['entry'][1]['resource'] == gold_draft['entry'][1]['resource']}
            pf.write(json.dumps(pub, sort_keys=True) + '\n'); pf.flush()
            print('VLM', i + 1, len(sel), r['case_id'][-8:], r['variant'], 'correct', pub['correct_count'], '/7 admitted', pub['admitted_count'], 'false_adm', pub['false_admissions'], flush=True)
    meta = {'schema': 'redteam.vlm_lane_run.v1', 'model': a.model, 'dataset': manifest['dataset'], 'form_root': manifest['root'], 'split': a.split, 'variants': variants, 'images': len(sel),
            'served_from': a.server, 'challenge': not a.no_challenge, 'host': platform.node(), 'python': sys.version.split()[0],
            'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t_start)), 'finished_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'wall_seconds': round(time.time() - t_start, 1), 'public_sha256': sha(pp.read_bytes()), 'local_sha256': sha(lp.read_bytes()), 'local_file_export': 'NOT_AUTHORIZED_CONTAINS_ORACLE'}
    try:
        tags = json.load(urllib.request.urlopen(OLLAMA + '/api/tags', timeout=5)).get('models', [])
        meta['model_digest'] = next((m.get('digest') for m in tags if m.get('name') == a.model), None)
    except Exception as ex:
        meta['model_digest'] = 'UNKNOWN ' + type(ex).__name__
    (out_dir / (stem + '_META.json')).write_text(json.dumps(meta, sort_keys=True, indent=2) + '\n')
    print('RUN_DONE', json.dumps(meta, sort_keys=True))


if __name__ == '__main__':
    main()
