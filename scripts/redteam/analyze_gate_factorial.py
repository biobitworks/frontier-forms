#!/usr/bin/env python3
"""Gate-factorial analysis over SYNFORM2-ERR: every combination of the four admission mechanisms, with McNemar,
stratified paired bootstrap and LOMO views, producing the heat-map matrix. Runs on the host that holds the private
planted key and salts (values never leave the host); emits aggregates only.

Mechanisms (each ON/OFF -> 16 configurations, the heat map axes):
  identity     printed "Synthetic case" == FCO case_id                                   (FCO leaf)
  rules        deterministic field rules (ISO date, gender ∈ {M,F}, non-missing, encounter ≥ birth)   (Lean-checked gate)
  commitment   sha256(salt|canon(extracted value)) == FCO field commitment                (FCG leaf, Merkle-bound)
  consistency  two independent extractors agree on the field (Apple Vision OCR vs qwen2.5vl)          (antigentic challenge)
Unit of analysis: (image, field). Outcomes per configuration:
  admitted, admitted_correct_vs_source (admitted AND value == source truth), false_admission (admitted AND value != source),
  planted_detected (planted field NOT admitted), coverage.
Statistics: per configuration vs the no-gate baseline on the per-image outcome "all admitted fields are source-correct and
at least one field admitted" -> exact McNemar + stratified (by variant) paired bootstrap (10,000, seed 20261102); Holm over
the 15 non-baseline configurations. LOMO rows = full minus exactly one mechanism.
"""
from __future__ import annotations
import argparse, hashlib, json, math, platform, sys, time
from itertools import product
from pathlib import Path
import numpy as np

FIELDS = ('Synthetic case', 'Patient first', 'Patient last', 'Birth date', 'Gender', 'Encounter date', 'Visit class')
MECHS = ('identity', 'rules', 'commitment', 'consistency')


def canon(o): return json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
def sha(b): return hashlib.sha256(b).hexdigest()
def jsonl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]


def norm(name, v):
    import re
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
        return {'f': 'female', 'female': 'female', 'm': 'male', 'male': 'male'}.get(v.lower(), v.lower())
    if name in ('Visit class', 'Synthetic case'):
        return v.lower()
    return v


def exact_mcnemar(b, c):
    n = b + c
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n) if n else 1.0


def holm(p):
    items = sorted(p.items(), key=lambda kv: kv[1]); m = len(items); out = {}; run = 0.0
    for i, (k, v) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v)); out[k] = run
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--err-dir', required=True)
    ap.add_argument('--ocr-local', required=True)
    ap.add_argument('--vlm-local', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--reps', type=int, default=10000)
    a = ap.parse_args()
    E = Path(a.err_dir)
    man = json.loads((E / 'public/manifest.json').read_text())
    inputs = {r['image_id']: r for r in jsonl(E / 'public/inputs.jsonl')}
    planted = {p['image_id']: p for p in jsonl(E / '.private/planted.jsonl')}
    salts = json.loads((E / '.private/salts.json').read_text())
    ocr = {r['input_fco_id']: r for r in jsonl(a.ocr_local)}
    vlm = {r['input_fco_id']: r for r in jsonl(a.vlm_local)}
    images = [iid for iid in inputs if inputs[iid]['input_fco_id'] in ocr and inputs[iid]['input_fco_id'] in vlm]
    assert images, 'NO_OVERLAP_BETWEEN_OCR_AND_VLM'
    # per (image, field) mechanism verdicts for the PRIMARY extractor (VLM) with OCR as the independent challenger
    cells = []
    for iid in images:
        inp = inputs[iid]; pl = planted[iid]; fco = inp['input_fco_id']
        v_fields = vlm[fco]['fields_extract']; o_fields = ocr[fco]['fields']
        v_val = vlm[fco]['validation']
        salt = salts[pl['case_id']]
        for f in FIELDS:
            ev = norm(f, v_fields.get(f)); eo = norm(f, o_fields.get(f))
            src = norm(f, pl['source_fields'][f]); printed = norm(f, pl['printed_fields'][f])
            # commitment: hash equality after canonical normalisation (what the FCO owner hashes); values never leave the host
            src_commit = sha((salt + '|').encode() + canon(src))
            commit_ok = ev is not None and sha((salt + '|').encode() + canon(ev)) == src_commit
            cells.append({'image_id': iid, 'variant': pl['variant'], 'field': f, 'planted': f in pl['planted_fields'],
                          'extracted': ev is not None, 'extracted_eq_source': ev is not None and ev == src, 'extracted_eq_printed': ev is not None and ev == printed,
                          'identity_ok': v_val['Synthetic case'] == 'OK', 'rules_ok': v_val[f] in ('OK', 'CASE_ID_MISMATCH_WITH_FCO'),  # identity mismatch belongs to the identity mechanism
                          'commitment_ok': commit_ok, 'consistency_ok': ev is not None and ev == eo})
    # evaluate 16 configurations
    configs = {}
    for bits in product([False, True], repeat=4):
        cfg = dict(zip(MECHS, bits)); name = '+'.join(m for m in MECHS if cfg[m]) or 'none'
        per_image = {}
        agg = {'cells': 0, 'admitted': 0, 'admitted_correct': 0, 'false_admissions': 0, 'planted_cells': 0, 'planted_detected': 0, 'variance_cells': 0,
               'variance_false_admissions': 0, 'by_variant': {}}
        for c in cells:
            adm = c['extracted'] and all(c[m + '_ok'] for m in MECHS if cfg[m])
            agg['cells'] += 1; agg['admitted'] += adm; agg['admitted_correct'] += adm and c['extracted_eq_source']
            agg['false_admissions'] += adm and not c['extracted_eq_source']
            if c['planted']:
                agg['planted_cells'] += 1; agg['planted_detected'] += (not adm)
            if c['variant'].startswith('V'):
                agg['variance_cells'] += 1; agg['variance_false_admissions'] += adm and not c['extracted_eq_source']
            bv = agg['by_variant'].setdefault(c['variant'], {'cells': 0, 'admitted': 0, 'false_admissions': 0, 'planted_cells': 0, 'planted_detected': 0})
            bv['cells'] += 1; bv['admitted'] += adm; bv['false_admissions'] += adm and not c['extracted_eq_source']
            if c['planted']:
                bv['planted_cells'] += 1; bv['planted_detected'] += (not adm)
            pi = per_image.setdefault(c['image_id'], {'admitted': 0, 'wrong': 0})
            pi['admitted'] += adm; pi['wrong'] += adm and not c['extracted_eq_source']
        div = lambda x, y: (x / y) if y else None
        agg.update({'coverage': div(agg['admitted'], agg['cells']), 'selective_accuracy': div(agg['admitted_correct'], agg['admitted']),
                    'false_admission_rate_of_all': div(agg['false_admissions'], agg['cells']), 'planted_detection_rate': div(agg['planted_detected'], agg['planted_cells']),
                    'variance_false_admission_rate': div(agg['variance_false_admissions'], agg['variance_cells'])})
        # per-image success: at least one field admitted and no wrong admissions
        agg['image_success'] = {iid: (v['admitted'] > 0 and v['wrong'] == 0) for iid, v in per_image.items()}
        configs[name] = {'config': cfg, **agg}
    # statistics vs baseline 'none'
    base = configs['none']['image_success']; strata = {iid: planted[iid]['variant'] for iid in images}
    rng = np.random.default_rng(20261102)
    pvals = {}
    for name, cfg in configs.items():
        if name == 'none':
            continue
        chal = cfg['image_success']
        b = sum(1 for i in images if base[i] and not chal[i]); c = sum(1 for i in images if chal[i] and not base[i])
        p = exact_mcnemar(b, c); pvals[name] = p
        groups = {}
        for i in images:
            groups.setdefault(strata[i], []).append(int(chal[i]) - int(base[i]))
        sums = np.zeros(a.reps)
        for arr in groups.values():
            arr = np.array(arr); idx = rng.integers(0, len(arr), size=(a.reps, len(arr))); sums += arr[idx].sum(axis=1)
        d = np.sort(sums / len(images)); lo, hi = np.quantile(d, [0.025, 0.975])
        cfg['vs_none'] = {'n_images': len(images), 'baseline_success': sum(base.values()), 'config_success': sum(chal.values()), 'baseline_only': b, 'config_only': c,
                          'delta_success_rate': (sum(chal.values()) - sum(base.values())) / len(images), 'p_mcnemar_exact_two_sided': p,
                          'ci95_delta_stratified_bootstrap': [float(lo), float(hi)], 'bootstrap_gate': bool(lo > 0)}
    h = holm(pvals)
    for name in pvals:
        configs[name]['vs_none']['p_holm'] = h[name]; configs[name]['vs_none']['mcnemar_gate_holm'] = h[name] < 0.05 and configs[name]['vs_none']['delta_success_rate'] > 0
    full = configs['identity+rules+commitment+consistency']
    lomo = {}
    for m in MECHS:
        name = '+'.join(x for x in MECHS if x != m)
        c = configs[name]
        lomo['minus_' + m] = {'planted_detection_rate': c['planted_detection_rate'], 'false_admission_rate_of_all': c['false_admission_rate_of_all'], 'coverage': c['coverage'],
                              'delta_detection_vs_full': (c['planted_detection_rate'] or 0) - (full['planted_detection_rate'] or 0),
                              'delta_false_admissions_vs_full': c['false_admissions'] - full['false_admissions'],
                              'delta_coverage_vs_full': (c['coverage'] or 0) - (full['coverage'] or 0)}
    for cfg in configs.values():
        cfg.pop('image_success')
    out = {'schema': 'redteam.gate_factorial.v1', 'dataset': man['dataset'], 'form_root': man['root'], 'images_analyzed': len(images), 'cells': len(cells),
           'primary_extractor': 'qwen2.5vl:3b single pass', 'challenger_extractor': 'Apple Vision OCR + geometric parser', 'mechanisms': MECHS,
           'configurations': configs, 'lomo': lomo, 'host': platform.node(), 'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'note': 'commitment check = hash equality against the FCO commitment after canonical normalisation; values never exported'}
    Path(a.out).write_text(json.dumps(out, sort_keys=True, indent=2) + '\n')
    print(f"{'config':40s} cov  selacc falseadm det   p      holm   CI")
    for name, c in sorted(configs.items(), key=lambda kv: sum(kv[1]['config'].values())):
        v = c.get('vs_none', {})
        print(f"{name:40s} {c['coverage']:.2f} {c['selective_accuracy'] if c['selective_accuracy'] is not None else float('nan'):.2f} {c['false_admissions']:4d}    {c['planted_detection_rate']:.2f}  "
              f"{v.get('p_mcnemar_exact_two_sided', float('nan')):.4f} {v.get('p_holm', float('nan')):.4f} {v.get('ci95_delta_stratified_bootstrap', '')}")


if __name__ == '__main__':
    main()
