#!/usr/bin/env python3
"""SYNFORM2: frozen synthetic encounter-intake form dataset built deterministically from the frozen Synthea CSV archive.

Source: datasets/synthea_100_csv/synthea_sample_data_csv_latest.zip (sha256 990d5206…eda16, leaf 3 of the 15-leaf root).
Successor of SYNFORM-36d12313 (12 forms). Nothing in the predecessor directory is touched; output goes to --out.

Per patient (all patients in patients.csv): one encounter chosen by the smallest sha256(patient_id|encounter_id);
seven labelled fields identical to forms12 so the same deterministic scorer applies; two rendered variants per case:
  clean   900x560 PNG like forms12
  scan    seeded rotation (±1.5°), gaussian noise, slight blur, reduced contrast, JPEG(60) round-trip, saved as PNG
Patient-level split by sorted case hash: train 60% / dev 20% / test 20%. Private oracle (gold fields) is written to
<out>/.private/ and is never exported. Public: inputs.jsonl, manifest.json (Merkle root whose leaf 0 binds the leaf count).
Synthea data is synthetic; still no values appear in the public files.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, platform, sys, time, zipfile
from pathlib import Path

FIELDS = ('Synthetic case', 'Patient first', 'Patient last', 'Birth date', 'Gender', 'Encounter date', 'Visit class')
EXPECTED_ZIP_SHA = '990d52064037bbf83d10f13163da428964b56ae673b7f39bf549d78c1e7eda16'
PARENT_FORM_ROOT = '36d12313c179ec207af81cd24356ce5bc172b430b584bdef397f383292375fe6'
PARENT_PROJECT_ROOT = '9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a'


def canon(o): return json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
def sha(b): return hashlib.sha256(b).hexdigest()
def leaf(o): return hashlib.sha256(b'\x00' + canon(o)).digest()


def root(leaves):
    v = list(leaves)
    while len(v) > 1:
        if len(v) % 2:
            v.append(v[-1])
        v = [hashlib.sha256(b'\x01' + v[i] + v[i + 1]).digest() for i in range(0, len(v), 2)]
    return v[0].hex()


def render_clean(fields, font, font_small):
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (900, 560), 'white')
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 879, 539], outline=(40, 40, 40), width=2)
    d.text((55, 48), 'SYNTHETIC ENCOUNTER INTAKE - NOT CLINICAL', fill=(20, 20, 20), font=font_small)
    y = 110
    for f in FIELDS:
        d.text((60, y), f + ':', fill=(30, 30, 30), font=font)
        d.text((290, y), str(fields[f]), fill=(10, 10, 10), font=font)
        d.line([290, y + 24, 840, y + 24], fill=(120, 120, 120), width=1)
        y += 58
    return img


def render_scan(img, seed):
    import numpy as np
    from PIL import Image, ImageFilter, ImageEnhance
    rng = np.random.default_rng(seed)
    angle = float(rng.uniform(-1.5, 1.5))
    im = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor='white')
    im = ImageEnhance.Contrast(im).enhance(0.72)
    im = im.filter(ImageFilter.GaussianBlur(radius=0.6))
    arr = np.asarray(im).astype(np.int16)
    arr = np.clip(arr + rng.normal(0, 9, arr.shape), 0, 255).astype(np.uint8)
    im = Image.fromarray(arr)
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=60); buf.seek(0)
    return Image.open(buf).convert('RGB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    from PIL import ImageFont, __version__ as pil_version
    zb = Path(a.zip).read_bytes()
    zsha = sha(zb)
    if zsha != EXPECTED_ZIP_SHA:
        raise SystemExit('SOURCE_ZIP_SHA_MISMATCH ' + zsha)
    z = zipfile.ZipFile(io.BytesIO(zb))
    patients = list(csv.DictReader(io.TextIOWrapper(z.open('patients.csv'), encoding='utf-8')))
    encounters = list(csv.DictReader(io.TextIOWrapper(z.open('encounters.csv'), encoding='utf-8')))
    by_pat = {}
    for e in encounters:
        by_pat.setdefault(e['PATIENT'], []).append(e)
    out = Path(a.out); pub = out / 'public'; priv = out / '.private'
    if out.exists():
        raise SystemExit('APPEND_ONLY_OUT_EXISTS ' + str(out))
    (pub / 'forms').mkdir(parents=True); priv.mkdir(parents=True)
    font = ImageFont.load_default(size=18); font_small = ImageFont.load_default(size=16)
    cases = []
    for p in patients:
        encs = by_pat.get(p['Id'])
        if not encs:
            continue
        e = min(encs, key=lambda x: sha((p['Id'] + '|' + x['Id']).encode()))
        case_hash = sha(canon([zsha, p['Id'], e['Id']]))
        case_id = 'synform2-' + case_hash[:20]
        gold = {'Synthetic case': case_id, 'Patient first': p['FIRST'], 'Patient last': p['LAST'], 'Birth date': p['BIRTHDATE'],
                'Gender': p['GENDER'], 'Encounter date': e['START'][:10], 'Visit class': e['ENCOUNTERCLASS']}
        cases.append({'case_id': case_id, 'case_hash': case_hash, 'patient_sha256': sha(p['Id'].encode()), 'encounter_sha256': sha(e['Id'].encode()), 'gold': gold})
    cases.sort(key=lambda c: c['case_hash'])
    if a.limit:
        cases = cases[:a.limit]
    n = len(cases); n_train = int(n * 0.6); n_dev = int(n * 0.2)
    inputs, oracles, leaves_rows = [], [], []
    t0 = time.monotonic()
    for i, c in enumerate(cases):
        split = 'train' if i < n_train else ('dev' if i < n_train + n_dev else 'test')
        img = render_clean(c['gold'], font, font_small)
        variants = {'clean': img, 'scan': render_scan(img, int(c['case_hash'][:8], 16))}
        for vname, im in variants.items():
            rel = f"forms/{c['case_id']}_{vname}.png"
            buf = io.BytesIO(); im.save(buf, 'PNG', optimize=False); b = buf.getvalue()
            (pub / rel).write_bytes(b)
            atom = {'fco_kind': 'FormImageFCO', 'schema': 'fco.synform2.v1', 'case_id': c['case_id'], 'variant': vname, 'png_sha256': sha(b),
                    'source_zip_sha256': zsha, 'split': split, 'oracle_visibility': 'PRIVATE', 'model_access': 'IMAGE_ONLY'}
            rec = dict(atom, input_fco_id='fco:' + sha(canon(atom)), png_relative_path=rel, size_bytes=len(b))
            inputs.append(rec); leaves_rows.append({'type': 'FORM_IMAGE_FCO', 'case_id': c['case_id'], 'variant': vname, 'png_sha256': sha(b), 'input_fco_id': rec['input_fco_id'], 'split': split})
        oracles.append({'case_id': c['case_id'], 'split': split, 'gold_fields': c['gold'], 'patient_sha256': c['patient_sha256'], 'encounter_sha256': c['encounter_sha256']})
    context = {'type': 'FORM_RUN_CONTEXT', 'schema': 'fco.synform2.v1', 'source_zip_sha256': zsha, 'parent_form_root': PARENT_FORM_ROOT,
               'parent_project_root': PARENT_PROJECT_ROOT, 'leaf_count': len(leaves_rows) + 1, 'cases': n, 'variants': ['clean', 'scan'],
               'split_rule': 'sorted by case_hash; train first 60%, dev next 20%, test last 20%; patient-level (one case per patient)',
               'renderer': f'Pillow {pil_version}; default font 18/16; scan=rotate±1.5°,contrast0.72,blur0.6,noise σ9,JPEG60', 'python': sys.version.split()[0], 'host': platform.node()}
    rows = [context] + leaves_rows
    rt = root([leaf(x) for x in rows])
    (pub / 'inputs.jsonl').write_bytes(b''.join(canon(x) + b'\n' for x in inputs))
    (pub / 'leaves.jsonl').write_bytes(b''.join(canon(x) + b'\n' for x in rows))
    (priv / 'oracle.jsonl').write_bytes(b''.join(canon(x) + b'\n' for x in oracles))
    manifest = {'schema': 'asi.forms.merkle.v2', 'dataset': 'SYNFORM2-' + rt[:16], 'root': rt, 'leaf_count': len(rows), 'cases': n,
                'split_sizes': {'train': n_train, 'dev': n_dev, 'test': n - n_train - n_dev}, 'images': len(inputs),
                'public_input_listing_sha256': sha((pub / 'inputs.jsonl').read_bytes()), 'private_oracle_sha256': sha((priv / 'oracle.jsonl').read_bytes()),
                'source_sha256': zsha, 'source_state': 'SYNTHETIC_REPRODUCIBLE', 'parent_form_root': PARENT_FORM_ROOT, 'parent_project_root': PARENT_PROJECT_ROOT,
                'scheme': 'sha256(00||canonical_json); sha256(01||left||right); odd_duplicate; leaf0_binds_count', 'signed': 'NOT_SIGNED', 'MMR': 'NOT_COMPUTED',
                'public_export_of_oracle': 'NOT_AUTHORIZED_PENDING_RIGHTS_DECISION', 'ocr_state': 'NOT_TESTED', 'training_state': 'NOT_EXECUTED',
                'clinical_state': 'NOT_CLINICAL', 'built_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'render_seconds': round(time.monotonic() - t0, 1)}
    (pub / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k: manifest[k] for k in ('dataset', 'root', 'leaf_count', 'cases', 'split_sizes', 'images', 'public_input_listing_sha256')}, indent=2))


if __name__ == '__main__':
    main()
