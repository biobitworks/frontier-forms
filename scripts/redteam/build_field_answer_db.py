#!/usr/bin/env python3
"""Build the local JSON "databases" (no credentials, no server) that other agents and teammates read:

  evidence/redteam/db/models.json         weights registry: every checkpoint used, with its digest (Ollama manifest digest,
                                           safetensors sha256, Apple Vision = macOS build) and the lanes it ran in
  evidence/redteam/db/field_answers.jsonl  one row per (image, field): printed value, source value, every model's actual
                                           answer (OCR, VLM, OCR->Qwen mappers, VLM grounding + bbox) and gate verdicts
  evidence/redteam/db/ledger.jsonl         attribution ledger with the three separated quantities:
                                           weights {name, digest} / mechanism {enabled, disabled} / outcome {metric, baseline, challenger, delta}
Runs on the host (values are synthetic Synthea renders; export authorised by the owner). Everything is derived from the
lane files; nothing is typed in by hand.
"""
from __future__ import annotations
import argparse, glob, json, platform, time, urllib.request
from pathlib import Path

FIELDS = ('Synthetic case', 'Patient first', 'Patient last', 'Birth date', 'Gender', 'Encounter date', 'Visit class')


def jsonl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lanes', required=True)
    ap.add_argument('--synform2', required=True)
    ap.add_argument('--err', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--gate-factorial', default='')
    a = ap.parse_args()
    L = Path(a.lanes); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    # ---- models registry
    try:
        tags = {m['name']: m for m in json.load(urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=5)).get('models', [])}
    except Exception:
        tags = {}
    models = {}
    for meta in sorted(L.glob('*_META.json')):
        m = json.loads(meta.read_text()); name = m.get('model') or m.get('engine')
        if not name:
            continue
        ent = models.setdefault(name, {'name': name, 'family': ('qwen' if 'qwen' in name.lower() else 'liquid' if 'lfm' in name.lower() else 'apple-vision' if 'Vision' in name else 'other'),
                                       'weights_digest': m.get('model_digest') or m.get('weights_sha256') or ('macOS ' + platform.mac_ver()[0] + ' Vision.framework' if 'Vision' in name else 'UNKNOWN'),
                                       'ollama_size_bytes': (tags.get(name) or {}).get('size'), 'quantization': ((tags.get(name) or {}).get('details') or {}).get('quantization_level'),
                                       'parameter_size': ((tags.get(name) or {}).get('details') or {}).get('parameter_size'), 'runs': []})
        ent['runs'].append({'meta_file': meta.name, 'split': m.get('split'), 'dataset': m.get('dataset'), 'images_or_cases': m.get('images') or m.get('cases'), 'wall_seconds': m.get('wall_seconds'), 'public_sha256': m.get('public_sha256')})
    (out / 'models.json').write_text(json.dumps({'schema': 'redteam.models_registry.v1', 'host': platform.node(), 'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                                 'models': models, 'blocked': {'Qwen/Qwen3.8-27B via Fireworks': 'BLOCKED_NO_CREDENTIAL', 'Mistral OCR': 'BLOCKED_NO_CREDENTIAL', 'YOLO': 'NOT_USED_NO_TRAINED_FIELD_DETECTOR'}}, indent=2, sort_keys=True) + '\n')
    # ---- field answers
    def load_private(d):
        D = Path(d); inputs = {r['input_fco_id']: r for r in jsonl(D / 'public/inputs.jsonl')}
        planted = {p['image_id']: p for p in jsonl(D / '.private/planted.jsonl')} if (D / '.private/planted.jsonl').exists() else {}
        oracle = {o['case_id']: o for o in jsonl(D / '.private/oracle.jsonl')}
        return inputs, planted, oracle
    sets = {'synform2': load_private(a.synform2), 'synform2_err': load_private(a.err)}
    answers = {}
    def key(rec, ds): return (ds, rec['input_fco_id'])
    def ensure(rec, ds):
        inputs, planted, oracle = sets[ds]; r = inputs[rec['input_fco_id']]
        k = key(rec, ds)
        if k not in answers:
            pl = planted.get(r.get('image_id'))
            answers[k] = {'dataset': ds, 'case_id': r['case_id'], 'image_id': r.get('image_id'), 'variant': (pl or {}).get('variant') or r.get('variant'), 'split': r.get('split') or (pl or {}).get('split'),
                          'input_fco_id': r['input_fco_id'], 'png_sha256': r['png_sha256'], 'fields': {f: {'printed': oracle[r.get('image_id', r['case_id'])]['gold_fields'][f],
                          'source': (pl['source_fields'][f] if pl else oracle[r['case_id']]['gold_fields'][f]), 'planted': (f in pl['planted_fields']) if pl else False, 'answers': {}} for f in FIELDS}}
        return answers[k]
    for p in sorted(L.glob('*_LOCAL.jsonl')) + sorted(L.glob('BBOX_*_PUBLIC.jsonl')):
        ds = 'synform2_err' if ('ERR' in p.name or 'synform2_err' in p.name) else ('synform2' if 'synform2' in p.name else None)
        if ds is None:
            continue
        for rec in jsonl(p):
            if 'input_fco_id' not in rec or rec['input_fco_id'] not in sets[ds][0]:
                continue
            row = ensure(rec, ds)
            if p.name.startswith('OCR'):
                for f in FIELDS:
                    row['fields'][f]['answers']['apple_vision_ocr'] = {'value': rec['fields'].get(f), 'correct_vs_printed': rec['correct'][f], 'validation': rec['validation'][f]}
            elif p.name.startswith('VLM'):
                for f in FIELDS:
                    row['fields'][f]['answers'][rec['model'] + ':extract'] = {'value': rec['fields_extract'].get(f), 'correct_vs_printed': rec['correct_extract'][f], 'validation': rec['validation'][f],
                                                                            'reread_value': rec.get('fields_reread', {}).get(f), 'agree_with_reread': rec.get('agree', {}).get(f), 'admitted': rec['admitted'][f]}
            elif p.name.startswith('MAP'):
                for f in FIELDS:
                    row['fields'][f]['answers'][rec['model'] + ':ocr_mapper'] = {'value': rec['fields'].get(f), 'correct_vs_printed': rec['correct'][f], 'validation': rec['validation'][f]}
            elif p.name.startswith('BBOX'):
                for f in FIELDS:
                    pf = rec['fields'][f]
                    row['fields'][f]['answers'][rec['model'] + ':grounding'] = {'value': pf['vlm_value'], 'bbox': pf['vlm_bbox'], 'iou_vs_gt': pf['vlm_iou'], 'correct_vs_printed': pf['vlm_value_correct']}
                    row['fields'][f]['answers']['apple_vision_ocr'] = dict(row['fields'][f]['answers'].get('apple_vision_ocr', {}), bbox=pf['vision_bbox'], iou_vs_gt=pf['vision_iou'], gt_bbox=pf['gt_bbox'])
    with (out / 'field_answers.jsonl').open('w') as f:
        for k in sorted(answers):
            f.write(json.dumps(answers[k], sort_keys=True) + '\n')
    # ---- ledger: weights / mechanism / outcome, from the gate factorial + per-model fidelity
    ledger = []
    if a.gate_factorial and Path(a.gate_factorial).exists():
        g = json.loads(Path(a.gate_factorial).read_text()); none = g['configurations']['none']
        primary = models.get('qwen2.5vl:3b', {}); chall = next((v for k, v in models.items() if 'Vision' in k), {})
        for name, c in g['configurations'].items():
            if name == 'none':
                continue
            v = c.get('vs_none', {})
            ledger.append({'ledger_id': 'GF-' + name, 'dataset': g['dataset'], 'form_root': g['form_root'],
                           'weights': {'primary': {'name': 'qwen2.5vl:3b', 'digest': primary.get('weights_digest')}, 'challenger': {'name': 'Apple Vision OCR', 'digest': chall.get('weights_digest')}},
                           'mechanism': {'enabled': [m for m in g['mechanisms'] if c['config'][m]], 'disabled': [m for m in g['mechanisms'] if not c['config'][m]]},
                           'outcome': {'metric': 'planted_detection_rate / false_admission_rate_of_all / coverage', 'baseline(none)': [none['planted_detection_rate'], none['false_admission_rate_of_all'], none['coverage']],
                                       'challenger': [c['planted_detection_rate'], c['false_admission_rate_of_all'], c['coverage']],
                                       'delta': [(c['planted_detection_rate'] or 0) - (none['planted_detection_rate'] or 0), (c['false_admission_rate_of_all'] or 0) - (none['false_admission_rate_of_all'] or 0), (c['coverage'] or 0) - (none['coverage'] or 0)],
                                       'per_image_success_delta': v.get('delta_success_rate'), 'mcnemar_p': v.get('p_mcnemar_exact_two_sided'), 'holm_p': v.get('p_holm'), 'bootstrap_ci95': v.get('ci95_delta_stratified_bootstrap'),
                                       'status': 'PASS' if (v.get('mcnemar_gate_holm') and v.get('bootstrap_gate')) else 'NULL'}})
    # per-model single-pass fidelity on synform2 test (no mechanism), weights only
    for p in sorted(L.glob('*_synform2_test_PUBLIC.jsonl')) + sorted(L.glob('MAP_*_synform2_PUBLIC.jsonl')):
        rows = jsonl(p); name = rows[0].get('model') or 'Apple Vision OCR' if rows else None
        if not rows:
            continue
        ck = 'correct' if 'correct' in rows[0] else 'correct_extract'
        if ck not in rows[0]:
            continue
        ledger.append({'ledger_id': 'FID-' + p.stem, 'dataset': 'SYNFORM2 test', 'weights': {'primary': {'name': name, 'digest': models.get(name, {}).get('weights_digest')}},
                       'mechanism': {'enabled': [], 'disabled': ['identity', 'rules', 'commitment', 'consistency']},
                       'outcome': {'metric': 'field_fidelity_vs_printed', 'images': len(rows), 'fields_correct': sum(sum(r[ck].values()) for r in rows), 'fields_total': 7 * len(rows),
                                   'all7_images': sum(1 for r in rows if all(r[ck].values())), 'status': 'OBSERVED'}})
    with (out / 'ledger.jsonl').open('w') as f:
        for e in ledger:
            f.write(json.dumps(e, sort_keys=True) + '\n')
    print('DB', 'models', len(models), 'field_answer_rows', len(answers), 'ledger', len(ledger))


if __name__ == '__main__':
    main()
