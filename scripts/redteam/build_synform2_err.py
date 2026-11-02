#!/usr/bin/env python3
"""SYNFORM2-ERR: prebuilt synthetic forms with PLANTED errors and VARIANCE, for the gate-factorial heat map.

Built from the SYNFORM2 test split (private oracle = source truth). For every test case the following images are rendered:
  clean            printed == source (control)
  E1_enc_before_birth   encounter date printed earlier than birth date        (rule-detectable; Lean rule)
  E2_invalid_gender     gender printed as 'X'                                 (rule-detectable)
  E3_case_id_swap       another test case's case id printed (cross-patient)   (FCO identity-detectable)
  E4_missing_field      patient last name left blank                          (rule-detectable: MISSING)
  E5_bad_date_format    birth date printed as DD/MM/YYYY                      (rule-detectable: INVALID_DATE)
  E6_name_swap          first and last names swapped                          (only commitment/source-detectable)
  E7_digit_flip         one digit of the birth date changed, still a valid date (only commitment/source-detectable)
  V1_scan_sigma9        clean content, scan-like noise σ9 (variance, no planted error)
  V2_scan_sigma25       clean content, heavier noise σ25 + rotation            (variance, no planted error)
Each image's FCO carries per-field COMMITMENTS sha256(salt || canon(source_value)); the salt lives in .private/ and is
available to the harness (it owns the FCO), never to the extractor. Commitments let a verifier reject an extracted value
that differs from the committed source value without the extractor ever seeing the oracle. Public files contain no
values and no planted-error labels; .private/planted.jsonl is the key for scoring only.
"""
from __future__ import annotations
import argparse, hashlib, io, json, platform, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_synform2 import FIELDS, canon, sha, leaf, root, render_clean, render_scan, PARENT_PROJECT_ROOT

ERRORS = ['clean', 'E1_enc_before_birth', 'E2_invalid_gender', 'E3_case_id_swap', 'E4_missing_field', 'E5_bad_date_format', 'E6_name_swap', 'E7_digit_flip', 'V1_scan_sigma9', 'V2_scan_sigma25']


def plant(source, variant, other_case_id):
    f = dict(source)
    if variant == 'E1_enc_before_birth':
        y = int(f['Birth date'][:4]) - 3
        f['Encounter date'] = f'{y:04d}' + f['Birth date'][4:]
    elif variant == 'E2_invalid_gender':
        f['Gender'] = 'X'
    elif variant == 'E3_case_id_swap':
        f['Synthetic case'] = other_case_id
    elif variant == 'E4_missing_field':
        f['Patient last'] = ''
    elif variant == 'E5_bad_date_format':
        y, m, d = f['Birth date'].split('-'); f['Birth date'] = f'{d}/{m}/{y}'
    elif variant == 'E6_name_swap':
        f['Patient first'], f['Patient last'] = f['Patient last'], f['Patient first']
    elif variant == 'E7_digit_flip':
        bd = f['Birth date']; day = int(bd[8:10]); day = day + 1 if day < 28 else day - 1
        f['Birth date'] = bd[:8] + f'{day:02d}'
    return f


def render_scan_sigma(img, seed, sigma, max_angle):
    import numpy as np
    from PIL import Image, ImageFilter, ImageEnhance
    rng = np.random.default_rng(seed)
    im = img.rotate(float(rng.uniform(-max_angle, max_angle)), resample=Image.BICUBIC, expand=False, fillcolor='white')
    im = ImageEnhance.Contrast(im).enhance(0.7).filter(ImageFilter.GaussianBlur(radius=0.7))
    arr = np.clip(np.asarray(im).astype(np.int16) + rng.normal(0, sigma, np.asarray(im).shape), 0, 255).astype(np.uint8)
    buf = io.BytesIO(); Image.fromarray(arr).save(buf, 'JPEG', quality=55); buf.seek(0)
    return Image.open(buf).convert('RGB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--synform2', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--split', default='test')
    a = ap.parse_args()
    from PIL import ImageFont, __version__ as pil_version
    s2 = Path(a.synform2); man2 = json.loads((s2 / 'public/manifest.json').read_text())
    oracle = [json.loads(x) for x in (s2 / '.private/oracle.jsonl').read_text().splitlines() if x.strip()]
    cases = [o for o in oracle if o['split'] == a.split]
    out = Path(a.out); pub = out / 'public'; priv = out / '.private'
    if out.exists():
        raise SystemExit('APPEND_ONLY_OUT_EXISTS')
    (pub / 'forms').mkdir(parents=True); priv.mkdir(parents=True)
    font = ImageFont.load_default(size=18); font_small = ImageFont.load_default(size=16)
    inputs, leaves_rows, planted, salts, oracle_rows = [], [], [], {}, []
    t0 = time.monotonic()
    for i, c in enumerate(cases):
        src = c['gold_fields']; other = cases[(i + 1) % len(cases)]['case_id']
        salt = sha(canon(['synform2-err-salt', man2['root'], c['case_id']]))
        salts[c['case_id']] = salt
        commitments = {f: sha((salt + '|').encode() + canon(src[f])) for f in FIELDS}
        for variant in ERRORS:
            printed = plant(src, variant, other) if variant.startswith('E') else dict(src)
            img = render_clean(printed, font, font_small)
            seed = int(sha(canon([c['case_id'], variant]))[:8], 16)
            if variant == 'V1_scan_sigma9':
                img = render_scan(img, seed)
            elif variant == 'V2_scan_sigma25':
                img = render_scan_sigma(img, seed, 25, 2.5)
            image_id = sha(canon([c['case_id'], variant]))[:16]
            rel = f"forms/{image_id}.png"
            buf = io.BytesIO(); img.save(buf, 'PNG', optimize=False); b = buf.getvalue(); (pub / rel).write_bytes(b)
            atom = {'fco_kind': 'FormImageFCO', 'schema': 'fco.synform2_err.v1', 'case_id': c['case_id'], 'image_id': image_id,
                    'png_sha256': sha(b), 'parent_synform2_root': man2['root'], 'field_commitments': commitments, 'commitment_scheme': 'sha256(salt|canonical_json(value)); salt private to FCO owner',
                    'oracle_visibility': 'PRIVATE', 'model_access': 'IMAGE_ONLY'}
            rec = dict(atom, input_fco_id='fco:' + sha(canon(atom)), png_relative_path=rel, size_bytes=len(b))
            inputs.append(rec)
            leaves_rows.append({'type': 'FORM_IMAGE_FCO', 'case_id': c['case_id'], 'image_id': atom['image_id'], 'png_sha256': sha(b), 'input_fco_id': rec['input_fco_id']})
            oracle_rows.append({'case_id': atom['image_id'], 'gold_fields': printed, 'note': 'PRINTED fields (extraction-fidelity target); source truth is in planted.jsonl'})
            planted.append({'case_id': c['case_id'], 'image_id': atom['image_id'], 'variant': variant, 'printed_fields': printed, 'source_fields': src,
                            'planted_fields': [f for f in FIELDS if printed[f] != src[f]], 'detectable_by': {
                                'identity': variant == 'E3_case_id_swap', 'rules': variant in ('E1_enc_before_birth', 'E2_invalid_gender', 'E4_missing_field', 'E5_bad_date_format'),
                                'commitment': variant.startswith('E'), 'consistency': variant.startswith('V')}})
    context = {'type': 'FORM_RUN_CONTEXT', 'schema': 'fco.synform2_err.v1', 'parent_synform2_root': man2['root'], 'parent_project_root': PARENT_PROJECT_ROOT,
               'leaf_count': len(leaves_rows) + 1, 'cases': len(cases), 'variants': ERRORS, 'split_source': a.split, 'renderer': f'Pillow {pil_version}',
               'python': sys.version.split()[0], 'host': platform.node()}
    rows = [context] + leaves_rows
    rt = root([leaf(x) for x in rows])
    (pub / 'inputs.jsonl').write_bytes(b''.join(canon(x) + b'\n' for x in inputs))
    (pub / 'leaves.jsonl').write_bytes(b''.join(canon(x) + b'\n' for x in rows))
    (priv / 'planted.jsonl').write_bytes(b''.join(canon(x) + b'\n' for x in planted))
    (priv / 'oracle.jsonl').write_bytes(b''.join(canon(x) + b'\n' for x in oracle_rows))
    (priv / 'salts.json').write_text(json.dumps(salts, sort_keys=True, indent=1) + '\n')
    manifest = {'schema': 'asi.forms.merkle.v2', 'dataset': 'SYNFORM2ERR-' + rt[:16], 'root': rt, 'leaf_count': len(rows), 'cases': len(cases), 'images': len(inputs),
                'variants': ERRORS, 'public_input_listing_sha256': sha((pub / 'inputs.jsonl').read_bytes()), 'private_planted_sha256': sha((priv / 'planted.jsonl').read_bytes()),
                'parent_synform2_root': man2['root'], 'parent_project_root': PARENT_PROJECT_ROOT, 'scheme': 'sha256(00||canonical_json); sha256(01||left||right); odd_duplicate; leaf0_binds_count',
                'signed': 'NOT_SIGNED', 'MMR': 'NOT_COMPUTED', 'public_export_of_planted_key': 'NOT_AUTHORIZED', 'built_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'render_seconds': round(time.monotonic() - t0, 1)}
    (pub / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k: manifest[k] for k in ('dataset', 'root', 'leaf_count', 'cases', 'images')}, indent=2))


if __name__ == '__main__':
    main()
