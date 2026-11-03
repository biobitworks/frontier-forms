#!/usr/bin/env python3
"""PREREGISTERED (written before any test-split result of these arms was seen, 2026-11-02 ~23:50 UTC):

Question: do locally TRAINED models improve field extraction over the untrained page-OCR baseline on the frozen,
untouched SYNFORM2 test split (46 images = 23 patients x clean + scan)?
Arms (all use the same Apple Vision OCR engine; only trained components differ):
  A0  page OCR + geometric rule parser                     (untrained baseline; numbers already in evidence)
  A1  A0 + learned post-correction                         (correction table fit on the TRAIN split OCR only)
  A2  trained YOLOv8n field detector -> crop each value box (x3 upscale) -> OCR the crop   (detector trained on TRAIN only)
  A3  A2 + learned post-correction
Primary endpoint: per-image all-7-fields-correct (vs the printed value). Secondary: field-level correct count.
Test: exact two-sided McNemar per arm vs A0, Holm over {A1, A2, A3}; stratified (clean/scan) paired bootstrap 10,000,
seed 20261102. PROMOTE only if Holm p < 0.05 AND bootstrap lower CI > 0; otherwise NULL (or NEGATIVE_WORSE if significantly
worse). Replication on a second cohort is NOT_TESTED, so the ceiling is OBSERVED/discovery-promotion, never SUPPORTED.
Learned correction (fit on train only): (1) per field, strip internal spaces if no train gold value of that field
contains a space; (2) per field, character substitutions OCR->gold learned from equal-length train pairs, applied only
when seen >= 2 times and never contradicted.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math, platform, subprocess, sys, tempfile, time
from pathlib import Path

FIELDS = ('Synthetic case', 'Patient first', 'Patient last', 'Birth date', 'Gender', 'Encounter date', 'Visit class')


def jsonl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def norm(f, v):
    import re
    if v is None:
        return None
    v = re.sub(r'\s+', ' ', str(v)).strip()
    if not v:
        return None
    if f in ('Birth date', 'Encounter date'):
        v = v.replace('/', '-').replace('.', '-')
        m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', v)
        return f'{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}' if m else v
    if f == 'Gender':
        return {'f': 'female', 'female': 'female', 'm': 'male', 'male': 'male'}.get(v.lower(), v.lower())
    if f in ('Visit class', 'Synthetic case'):
        return v.lower()
    return v


def fit_correction(train_rows, oracle):
    no_space = {}
    subs = {f: collections.Counter() for f in FIELDS}; contra = {f: set() for f in FIELDS}
    for f in FIELDS:
        golds = [oracle[r['case_id']][f] for r in train_rows]
        no_space[f] = not any(' ' in str(g) for g in golds)
    for r in train_rows:
        for f in FIELDS:
            o, g = r['fields'].get(f), oracle[r['case_id']][f]
            if o is None:
                continue
            o2 = o.replace(' ', '') if no_space[f] else o
            if len(o2) == len(str(g)):
                for a, b in zip(o2, str(g)):
                    if a != b:
                        subs[f][(a, b)] += 1
                    else:
                        contra[f].add(a)
    table = {f: {a: b for (a, b), n in subs[f].items() if n >= 2 and a not in contra[f]} for f in FIELDS}
    return {'strip_spaces': no_space, 'char_map': table}


def apply_correction(fields, model):
    out = {}
    for f in FIELDS:
        v = fields.get(f)
        if v is not None:
            if model['strip_spaces'][f]:
                v = v.replace(' ', '')
            v = ''.join(model['char_map'][f].get(c, c) for c in v)
        out[f] = v
    return out


def exact_mcnemar(b, c):
    n = b + c
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n) if n else 1.0


def holm(p):
    items = sorted(p.items(), key=lambda kv: kv[1]); m = len(items); out = {}; run = 0.0
    for i, (k, v) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v)); out[k] = run
    return out


def boot(base, chal, strata, reps=10000, seed=20261102):
    import random
    rng = random.Random(seed); groups = collections.defaultdict(list)
    for k in sorted(base):
        groups[strata[k]].append(int(chal[k]) - int(base[k]))
    n = len(base); d = sorted(sum(sum(rng.choice(v) for _ in v) for v in groups.values()) / n for _ in range(reps))
    q = lambda x: d[int((len(d) - 1) * x)]
    return [q(0.025), q(0.975)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--synform2', required=True)
    ap.add_argument('--ocr-train', required=True)
    ap.add_argument('--ocr-test', required=True)
    ap.add_argument('--detector', required=True, help='best.pt of the full-run detector')
    ap.add_argument('--ocr-bin', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    from ultralytics import YOLO
    from PIL import Image
    S = Path(a.synform2)
    oracle = {o['case_id']: o['gold_fields'] for o in jsonl(S / '.private/oracle.jsonl')}
    inputs = {r['input_fco_id']: r for r in jsonl(S / 'public/inputs.jsonl')}
    train = jsonl(a.ocr_train); test = jsonl(a.ocr_test)
    assert all(r['split'] == 'train' for r in train) and all(r['split'] == 'test' for r in test), 'SPLIT_LEAK'
    model = fit_correction(train, oracle)
    det = YOLO(a.detector)
    crops_dir = Path(tempfile.mkdtemp(prefix='ff-crops-'))
    crop_map = {}
    t0 = time.time()
    for r in test:
        img_p = S / 'public' / inputs[r['input_fco_id']]['png_relative_path']
        im = Image.open(img_p).convert('RGB')
        res = det.predict(str(img_p), device='mps', verbose=False, conf=0.25)[0]
        best = {}
        for c, s, b in zip(res.boxes.cls.tolist(), res.boxes.conf.tolist(), res.boxes.xyxy.tolist()):
            name = det.names[int(c)]
            if name.startswith('value:') and (name[6:] not in best or s > best[name[6:]][0]):
                best[name[6:]] = (s, b)
        for f, (s, b) in best.items():
            x1, y1, x2, y2 = b; pad = 6
            crop = im.crop((max(0, x1 - pad), max(0, y1 - pad), min(im.width, x2 + pad), min(im.height, y2 + pad)))
            crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
            canvas = Image.new('RGB', (crop.width + 60, crop.height + 60), 'white'); canvas.paste(crop, (30, 30))
            cp = crops_dir / f"{r['input_fco_id'][4:20]}_{FIELDS.index(f)}.png"; canvas.save(cp)
            crop_map[(r['input_fco_id'], f)] = (str(cp), s)
    paths = sorted({v[0] for v in crop_map.values()})
    ocr_out = {}
    for i in range(0, len(paths), 64):
        p = subprocess.run([a.ocr_bin] + paths[i:i + 64], capture_output=True, timeout=900)
        for e in json.loads(p.stdout.decode()):
            ocr_out[e['path']] = ' '.join(l['text'] for l in sorted(e['lines'], key=lambda l: l['x']))
    rows, field_counts = [], collections.Counter()
    for r in test:
        gold = oracle[r['case_id']]
        a0 = {f: r['fields'].get(f) for f in FIELDS}
        a1 = apply_correction(a0, model)
        a2 = {f: (ocr_out.get(crop_map[(r['input_fco_id'], f)][0]) or None) if (r['input_fco_id'], f) in crop_map else a0[f] for f in FIELDS}
        a3 = apply_correction(a2, model)
        row = {'input_fco_id': r['input_fco_id'], 'case_id': r['case_id'], 'variant': r['variant'], 'arms': {}}
        for arm, vals in (('A0', a0), ('A1', a1), ('A2', a2), ('A3', a3)):
            ok = {f: norm(f, vals[f]) == norm(f, gold[f]) for f in FIELDS}
            row['arms'][arm] = {'values': vals, 'correct': ok, 'all7': all(ok.values()), 'fields_correct': sum(ok.values())}
            for f in FIELDS:
                field_counts[(arm, f)] += ok[f]
        row['printed'] = gold
        rows.append(row)
    strata = {r['input_fco_id']: r['variant'] for r in rows}
    base = {r['input_fco_id']: r['arms']['A0']['all7'] for r in rows}
    comps, pv = {}, {}
    for arm in ('A1', 'A2', 'A3'):
        chal = {r['input_fco_id']: r['arms'][arm]['all7'] for r in rows}
        b = sum(1 for k in base if base[k] and not chal[k]); c = sum(1 for k in base if chal[k] and not base[k])
        p = exact_mcnemar(b, c); pv[arm] = p
        comps[arm] = {'baseline_all7': sum(base.values()), 'arm_all7': sum(chal.values()), 'n': len(base), 'baseline_only': b, 'arm_only': c,
                      'delta_all7_rate': (sum(chal.values()) - sum(base.values())) / len(base), 'p_mcnemar_exact_two_sided': p,
                      'ci95_bootstrap_stratified': boot(base, chal, strata),
                      'fields_correct': sum(r['arms'][arm]['fields_correct'] for r in rows), 'baseline_fields_correct': sum(r['arms']['A0']['fields_correct'] for r in rows), 'fields_total': 7 * len(rows)}
    h = holm(pv)
    for arm in comps:
        c = comps[arm]; c['p_holm'] = h[arm]
        c['decision'] = ('PROMOTE_DISCOVERY (replication NOT_TESTED)' if (h[arm] < 0.05 and c['delta_all7_rate'] > 0 and c['ci95_bootstrap_stratified'][0] > 0)
                         else 'NEGATIVE_WORSE' if (h[arm] < 0.05 and c['delta_all7_rate'] < 0) else 'NULL')
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    summary = {'schema': 'redteam.trained_gain.v1', 'preregistered_in': 'scripts/redteam/trained_gain_eval.py docstring', 'split_evaluated': 'test (46 images), touched once',
               'trained_components': {'yolov8n_detector_best_sha256': sha(a.detector), 'trained_on': 'SYNFORM2 train split (132 images)',
                                      'post_correction': {'fit_on': 'SYNFORM2 train split Apple OCR (132 images)', 'strip_spaces': model['strip_spaces'],
                                                          'char_map': {f: {f'{k}->{v}': 1 for k, v in m.items()} for f, m in model['char_map'].items()}}},
               'arms': {'A0': 'page OCR + rule parser (untrained)', 'A1': 'A0 + learned correction', 'A2': 'trained detector crops + OCR', 'A3': 'A2 + learned correction'},
               'comparisons_vs_A0': comps, 'field_level': {f'{arm}:{f}': n for (arm, f), n in sorted(field_counts.items())},
               'host': platform.node(), 'wall_seconds': round(time.time() - t0, 1), 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'ceiling': 'discovery promotion only; replication cohort NOT_TESTED; synthetic renders only'}
    (out / 'trained_gain_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    (out / 'trained_gain_rows.json').write_text(json.dumps(rows, indent=1, sort_keys=True) + '\n')
    for arm, c in comps.items():
        print(arm, c['arm_all7'], '/', c['n'], 'vs A0', c['baseline_all7'], 'fields', c['fields_correct'], '/', c['fields_total'], 'p', round(c['p_mcnemar_exact_two_sided'], 6), 'holm', round(c['p_holm'], 6), 'CI', c['ci95_bootstrap_stratified'], c['decision'])


if __name__ == '__main__':
    main()
