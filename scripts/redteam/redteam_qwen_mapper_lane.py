#!/usr/bin/env python3
"""Two-stage pipeline lane: Apple Vision OCR lines (text + boxes) -> Qwen text model field mapper (structured JSON).

This is the project spec's architecture ("OCR/DOM -> Qwen field mapper with structured output") run with the Qwen
checkpoints that exist locally (qwen2.5:0.5b, qwen2.5:1.5b, qwen3:1.7b, qwen2.5-coder:1.5b via Ollama). The 27B Fireworks
model in the spec is BLOCKED (no credential). Weights are identified by the Ollama manifest digest in META.
Input per image: the OCR lines recorded in the OCR lane's LOCAL file (same host), never the image itself.
Output: the model's actual per-field answers (synthetic data; export authorised by the owner) + verdicts.
"""
from __future__ import annotations
import argparse, json, platform, re, sys, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from redteam_forms_vlm import FIELDS, norm, validate, draft_fhir, sha, jsonl, OLLAMA, canon

PROMPT = ('You are a form field mapper. Below are OCR text lines from a SYNTHETIC (not real) encounter intake form, each with a '
          'normalized box [x, y, w, h] (origin bottom-left). Map them to a JSON object with exactly these keys: ' + ', '.join(f'"{f}"' for f in FIELDS) +
          '. Copy values exactly as they appear in the OCR text; use null when a field has no value. Return only JSON.\n\nOCR LINES:\n')


def chat(model, prompt, think_off, num_predict=200, seed=20261102):
    payload = {'model': model, 'stream': False, 'format': 'json', 'messages': [{'role': 'user', 'content': prompt}],
               'options': {'temperature': 0, 'seed': seed, 'num_predict': num_predict, 'num_ctx': 4096}}
    if think_off:
        payload['think'] = False
    req = urllib.request.Request(OLLAMA + '/api/chat', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    t0 = time.monotonic()
    try:
        res = json.load(urllib.request.urlopen(req, timeout=300))
        content = (res.get('message') or {}).get('content', '')
        try:
            parsed = json.loads(content); parsed = parsed if isinstance(parsed, dict) else {}
        except Exception:
            parsed = {}
        return {'status': 'EXECUTED', 'parsed': parsed, 'raw': content[:600], 'prompt_tokens': res.get('prompt_eval_count'), 'completion_tokens': res.get('eval_count'),
                'wall_seconds': round(time.monotonic() - t0, 3), 'eval_duration_ns': res.get('eval_duration')}
    except Exception as e:
        return {'status': 'FAILED', 'error': type(e).__name__ + ': ' + str(e)[:200], 'parsed': {}, 'raw': '', 'wall_seconds': round(time.monotonic() - t0, 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset-dir', required=True)
    ap.add_argument('--ocr-local', required=True)
    ap.add_argument('--model', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--tag', default='MAP')
    ap.add_argument('--label', default='synform2')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--think-off', action='store_true')
    a = ap.parse_args()
    t_start = time.time()
    D = Path(a.dataset_dir); man = json.loads((D / 'public/manifest.json').read_text())
    inputs = {r['input_fco_id']: r for r in jsonl(D / 'public/inputs.jsonl')}
    oracle = {o['case_id']: o['gold_fields'] for o in jsonl(D / '.private/oracle.jsonl')}
    ocr_rows = jsonl(a.ocr_local)
    if a.limit:
        ocr_rows = ocr_rows[:a.limit]
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{a.tag}_{a.model.replace(':', '_')}_{a.label}"
    lp, pp = out_dir / (stem + '_LOCAL.jsonl'), out_dir / (stem + '_PUBLIC.jsonl')
    if lp.exists() or pp.exists():
        raise SystemExit('APPEND_ONLY')
    with lp.open('x') as lf, pp.open('x') as pf:
        for i, o in enumerate(ocr_rows):
            r = inputs[o['input_fco_id']]; gold = oracle[r.get('image_id', r['case_id'])]
            lines = '\n'.join(f"[{l['x']:.3f}, {l['y']:.3f}, {l['w']:.3f}, {l['h']:.3f}] {l['text']}" for l in sorted(o['ocr_lines'], key=lambda l: (-l['y'], l['x'])))
            res = chat(a.model, PROMPT + lines, a.think_off)
            fields = {f: (res['parsed'].get(f) if isinstance(res['parsed'].get(f), (str, type(None))) else str(res['parsed'].get(f))) for f in FIELDS}
            val = validate(fields, r['case_id'])
            correct = {f: norm(f, fields[f]) == norm(f, gold.get(f)) for f in FIELDS}
            admitted = {f: val[f] == 'OK' and val['Synthetic case'] == 'OK' for f in FIELDS}
            rec = {'case_id': r['case_id'], 'image_id': r.get('image_id'), 'variant': o.get('variant', 'hidden'), 'split': o.get('split'), 'input_fco_id': r['input_fco_id'],
                   'model': a.model, 'arm': 'ocr_to_qwen_mapper', 'status': res['status'], 'fields': fields, 'printed': gold, 'validation': val, 'correct': correct, 'admitted': admitted,
                   'false_admissions': sum(1 for f in FIELDS if admitted[f] and not correct[f]), 'correct_count': sum(correct.values()),
                   'prompt_tokens': res.get('prompt_tokens'), 'completion_tokens': res.get('completion_tokens'), 'wall_seconds': res['wall_seconds'], 'raw': res['raw']}
            lf.write(json.dumps(rec, sort_keys=True) + '\n'); lf.flush()
            pf.write(json.dumps(rec, sort_keys=True) + '\n'); pf.flush()   # synthetic values; export authorised
            print('MAP', i + 1, len(ocr_rows), a.model, r['case_id'][-8:], rec['variant'], 'correct', rec['correct_count'], '/7', flush=True)
    meta = {'schema': 'redteam.mapper_lane_run.v1', 'model': a.model, 'stage1': 'Apple Vision OCR lines from ' + Path(a.ocr_local).name, 'dataset': man['dataset'], 'form_root': man['root'],
            'images': len(ocr_rows), 'host': platform.node(), 'python': sys.version.split()[0], 'think_off': a.think_off,
            'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t_start)), 'finished_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'wall_seconds': round(time.time() - t_start, 1), 'public_sha256': sha(pp.read_bytes()), 'values_exported': 'YES_SYNTHETIC_OWNER_AUTHORISED'}
    try:
        tags = json.load(urllib.request.urlopen(OLLAMA + '/api/tags', timeout=5)).get('models', [])
        meta['model_digest'] = next((m.get('digest') for m in tags if m.get('name') == a.model), None)
        meta['ollama_version'] = json.load(urllib.request.urlopen(OLLAMA + '/api/version', timeout=5)).get('version')
    except Exception as ex:
        meta['model_digest'] = 'UNKNOWN ' + type(ex).__name__
    (out_dir / (stem + '_META.json')).write_text(json.dumps(meta, sort_keys=True, indent=2) + '\n')
    print('RUN_DONE', json.dumps(meta, sort_keys=True))


if __name__ == '__main__':
    main()
