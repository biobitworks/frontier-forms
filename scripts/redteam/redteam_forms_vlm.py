#!/usr/bin/env python3
"""Claude red-team EHR lane: VLM extraction over the 12 frozen synthetic intake forms (derived/forms12).

Pipeline tested here (synthetic only, no EHR, no write-back):
  Synthea-derived synthetic record -> rendered PNG (frozen SYNFORM root) -> VLM extraction (qwen2.5vl:3b via
  Ollama) -> deterministic validation + FCO identity cross-check -> consistency challenge -> draft FHIR -> scorer.

Arms:
  extract          single-pass JSON extraction, no FCO context
  extract_fco      same, with the FCO context (case_id, png sha) in the prompt
  challenge        second independent field-by-field re-read; a field is admitted only if both passes agree,
                   passes format validation, and the extracted "Synthetic case" equals the FCO case_id
  cross_patient    image of case i presented with the FCO context of case j: the identity check must ABSTAIN
Gold fields are read from the private oracle only for local scoring. Public export: per-field booleans.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, platform, re, sys, time, urllib.request
from pathlib import Path

OLLAMA = 'http://127.0.0.1:11434'
FIELDS = ('Synthetic case', 'Patient first', 'Patient last', 'Birth date', 'Gender', 'Encounter date', 'Visit class')
GENDER_MAP = {'f': 'female', 'female': 'female', 'm': 'male', 'male': 'male'}
VISIT_CLASS_MAP = {'wellness': 'AMB', 'ambulatory': 'AMB', 'outpatient': 'AMB', 'emergency': 'EMER', 'inpatient': 'IMP', 'urgentcare': 'AMB'}
ISO = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def canon(o): return json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
def sha(b): return hashlib.sha256(b).hexdigest()
def jsonl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]


def norm(name, v):
    if v is None:
        return None
    v = re.sub(r'\s+', ' ', str(v)).strip()
    if not v:
        return None
    if name in ('Birth date', 'Encounter date'):
        v = v.replace('/', '-').replace('.', '-')
        m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', v)
        return f'{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}' if m else v
    if name == 'Gender':
        return GENDER_MAP.get(v.lower(), v.lower())
    if name in ('Visit class', 'Synthetic case'):
        return v.lower()
    return v


def validate(fields, expected_case_id):
    out = {}
    for f in FIELDS:
        v = norm(f, fields.get(f))
        if v is None:
            out[f] = 'MISSING'
        elif f in ('Birth date', 'Encounter date') and not ISO.match(v):
            out[f] = 'INVALID_DATE'
        elif f == 'Gender' and v not in ('male', 'female'):
            out[f] = 'INVALID_GENDER'
        elif f == 'Synthetic case' and v != expected_case_id.lower():
            out[f] = 'CASE_ID_MISMATCH_WITH_FCO'
        else:
            out[f] = 'OK'
    if out['Birth date'] == 'OK' and out['Encounter date'] == 'OK' and norm('Encounter date', fields['Encounter date']) < norm('Birth date', fields['Birth date']):
        out['Encounter date'] = 'ENCOUNTER_BEFORE_BIRTH'
    return out


def draft_fhir(fields, source_fco_id):
    n = {f: norm(f, fields.get(f)) for f in FIELDS}
    pid = 'synthetic-' + sha(canon([source_fco_id, 'patient']))[:16]
    eid = 'synthetic-' + sha(canon([source_fco_id, 'encounter']))[:16]
    patient = {'resourceType': 'Patient', 'id': pid, 'meta': {'tag': [{'system': 'urn:frontier-forms:synthetic', 'code': 'SYNTHETIC_NOT_CLINICAL'}]},
               'identifier': [{'system': 'urn:frontier-forms:fco', 'value': source_fco_id}],
               'name': [{'given': [n['Patient first']] if n['Patient first'] else [], 'family': n['Patient last']}],
               'gender': n['Gender'] if n['Gender'] in ('male', 'female') else 'unknown',
               'birthDate': n['Birth date'] if n['Birth date'] and ISO.match(n['Birth date']) else None}
    enc = {'resourceType': 'Encounter', 'id': eid, 'status': 'finished',
           'class': {'system': 'http://terminology.hl7.org/CodeSystem/v3-ActCode', 'code': VISIT_CLASS_MAP.get(n['Visit class'] or '', 'AMB')},
           'subject': {'reference': 'Patient/' + pid}, 'period': {'start': n['Encounter date']} if n['Encounter date'] else {}}
    return {'resourceType': 'Bundle', 'type': 'collection', 'entry': [{'resource': patient}, {'resource': enc}],
            'meta': {'tag': [{'system': 'urn:frontier-forms:writeback', 'code': 'PROHIBITED'}]}}


def vlm(model, prompt, png_bytes, num_predict=200, seed=20261102):
    payload = {'model': model, 'stream': False, 'format': 'json',
               'messages': [{'role': 'user', 'content': prompt, 'images': [base64.b64encode(png_bytes).decode()]}],
               'options': {'temperature': 0, 'seed': seed, 'num_predict': num_predict}}
    req = urllib.request.Request(OLLAMA + '/api/chat', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    t0 = time.monotonic()
    try:
        res = json.load(urllib.request.urlopen(req, timeout=600))
        content = (res.get('message') or {}).get('content', '')
        try:
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                parsed = {}
        except Exception:
            parsed = {}
        return {'status': 'EXECUTED', 'parsed': parsed, 'raw_len': len(content), 'prompt_tokens': res.get('prompt_eval_count'),
                'completion_tokens': res.get('eval_count'), 'wall_seconds': round(time.monotonic() - t0, 3), 'eval_duration_ns': res.get('eval_duration')}
    except Exception as e:
        return {'status': 'FAILED', 'error': type(e).__name__ + ': ' + str(e)[:200], 'parsed': {}, 'wall_seconds': round(time.monotonic() - t0, 3)}


EXTRACT_PROMPT = ('This is a SYNTHETIC (not real) encounter intake form. Read it and return a JSON object with exactly these keys: '
                  + ', '.join(f'"{f}"' for f in FIELDS) + '. Copy each value exactly as printed. Use null if a field is absent.')
FIELD_PROMPT = 'This is a SYNTHETIC form. What is the printed value of the field labelled "{f}"? Return JSON {{"value": "<exact printed text>"}}.'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--model', default='qwen2.5vl:3b')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--tag', default='EHR')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    source = Path(a.source); forms = source / 'derived/forms12'
    inputs = jsonl(forms / 'inputs.jsonl')
    oracle = {o['case_id']: o['gold_fields'] for o in jsonl(forms / '.private/oracle.jsonl')}
    freeze = json.loads((source / 'custody/form_freezes/SYNFORM-36d12313c179ec20/manifest.json').read_text())
    assert sha((forms / 'inputs.jsonl').read_bytes()) == freeze['public_input_listing_sha256'], 'INPUT_LISTING_SHA_MISMATCH'
    if a.limit:
        inputs = inputs[:a.limit]
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{a.tag}_{re.sub(r'[^A-Za-z0-9_.-]+', '_', a.model)}_forms12"
    lp, pp = out_dir / (stem + '_LOCAL.jsonl'), out_dir / (stem + '_PUBLIC.jsonl')
    if lp.exists() or pp.exists():
        raise SystemExit('APPEND_ONLY')
    t_start = time.time()
    with lp.open('x') as lf, pp.open('x') as pf:
        for i, rec in enumerate(inputs):
            png = (forms / rec['png_relative_path']).read_bytes()
            if sha(png) != rec['png_sha256']:
                raise SystemExit('PNG_SHA_MISMATCH ' + rec['case_id'])
            gold = oracle[rec['case_id']]
            fco_ctx = f"\nFCO CONTEXT (metadata only): case_id={rec['case_id']} input_fco={rec['input_fco_id']} png_sha256={rec['png_sha256'][:16]}..."
            e1 = vlm(a.model, EXTRACT_PROMPT, png)
            e2 = vlm(a.model, EXTRACT_PROMPT + fco_ctx, png)
            # independent field-by-field re-read (challenge pass)
            reread = {}
            for f in FIELDS:
                r = vlm(a.model, FIELD_PROMPT.format(f=f), png, num_predict=60)
                reread[f] = {'value': (r['parsed'] or {}).get('value'), 'status': r['status'], 'wall_seconds': r['wall_seconds'],
                             'tokens': (r.get('prompt_tokens') or 0) + (r.get('completion_tokens') or 0)}
            f1 = {f: e1['parsed'].get(f) for f in FIELDS}; f2 = {f: e2['parsed'].get(f) for f in FIELDS}
            f3 = {f: reread[f]['value'] for f in FIELDS}
            val = validate(f1, rec['case_id'])
            agree = {f: norm(f, f1[f]) is not None and norm(f, f1[f]) == norm(f, f3[f]) for f in FIELDS}
            identity_ok = val['Synthetic case'] == 'OK'
            admitted = {f: bool(agree[f] and val[f] == 'OK' and identity_ok) for f in FIELDS}
            correct1 = {f: norm(f, f1[f]) == norm(f, gold.get(f)) for f in FIELDS}
            correct2 = {f: norm(f, f2[f]) == norm(f, gold.get(f)) for f in FIELDS}
            correct3 = {f: norm(f, f3[f]) == norm(f, gold.get(f)) for f in FIELDS}
            # cross-patient: same image, FCO context of the NEXT case; identity check must abstain
            other = inputs[(i + 1) % len(inputs)]
            xval = validate(f1, other['case_id'])
            draft = draft_fhir({f: f1[f] if admitted[f] else None for f in FIELDS}, rec['input_fco_id'])
            gold_draft = draft_fhir(gold, rec['input_fco_id'])
            local = {'case_id': rec['case_id'], 'input_fco_id': rec['input_fco_id'], 'model': a.model, 'extract': e1, 'extract_fco': e2, 'reread': reread,
                     'fields_extract': f1, 'fields_fco': f2, 'fields_reread': f3, 'gold': gold, 'validation': val, 'agree': agree, 'admitted': admitted,
                     'correct_extract': correct1, 'correct_fco': correct2, 'correct_reread': correct3, 'cross_patient_validation': xval,
                     'draft_fhir_sha256': sha(canon(draft)), 'gold_draft_fhir_sha256': sha(canon(gold_draft)),
                     'draft_patient_matches_gold': draft['entry'][0]['resource'] == gold_draft['entry'][0]['resource'],
                     'draft_encounter_matches_gold': draft['entry'][1]['resource'] == gold_draft['entry'][1]['resource']}
            lf.write(json.dumps(local, sort_keys=True) + '\n'); lf.flush()
            pub = {k: local[k] for k in ('case_id', 'input_fco_id', 'model', 'validation', 'agree', 'admitted', 'correct_extract', 'correct_fco', 'correct_reread',
                                         'draft_fhir_sha256', 'draft_patient_matches_gold', 'draft_encounter_matches_gold')}
            pub['identity_check'] = 'PASS' if identity_ok else 'ABSTAIN'
            pub['cross_patient_identity_check'] = 'ABSTAIN' if xval['Synthetic case'] == 'CASE_ID_MISMATCH_WITH_FCO' else 'FALSE_ACCEPT'
            pub['false_admissions'] = sum(1 for f in FIELDS if admitted[f] and not correct1[f])
            pub['admitted_count'] = sum(admitted.values()); pub['correct_extract_count'] = sum(correct1.values())
            pub['tokens_extract'] = (e1.get('prompt_tokens') or 0) + (e1.get('completion_tokens') or 0)
            pub['tokens_challenge'] = sum(reread[f]['tokens'] for f in FIELDS)
            pub['wall_extract'] = e1['wall_seconds']; pub['wall_challenge'] = round(sum(reread[f]['wall_seconds'] for f in FIELDS), 3)
            pf.write(json.dumps(pub, sort_keys=True) + '\n'); pf.flush()
            print('FORM', i + 1, len(inputs), rec['case_id'], 'correct', pub['correct_extract_count'], 'admitted', pub['admitted_count'],
                  'false_adm', pub['false_admissions'], 'xpatient', pub['cross_patient_identity_check'], flush=True)
    meta = {'schema': 'redteam.forms_vlm_run.v1', 'model': a.model, 'cases': len(inputs), 'form_root': freeze['root'], 'host': platform.node(),
            'python': sys.version.split()[0], 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t_start)),
            'finished_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'wall_seconds': round(time.time() - t_start, 1),
            'public_sha256': sha(pp.read_bytes()), 'local_sha256': sha(lp.read_bytes()), 'local_file_export': 'NOT_AUTHORIZED_CONTAINS_ORACLE',
            'ehr_write': 'PROHIBITED_NOT_ATTEMPTED', 'epic': 'NOT_CONTACTED'}
    try:
        tags = json.load(urllib.request.urlopen(OLLAMA + '/api/tags', timeout=5)).get('models', [])
        meta['model_digest'] = next((m.get('digest') for m in tags if m.get('name') == a.model), None)
        meta['ollama_version'] = json.load(urllib.request.urlopen(OLLAMA + '/api/version', timeout=5)).get('version')
    except Exception as e:
        meta['ollama_version'] = 'UNKNOWN ' + type(e).__name__
    (out_dir / (stem + '_META.json')).write_text(json.dumps(meta, sort_keys=True, indent=2) + '\n')
    print('RUN_DONE', json.dumps(meta, sort_keys=True))


if __name__ == '__main__':
    main()
