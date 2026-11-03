#!/usr/bin/env python3
"""Build docs/judges/present_v2.html (successor of the frozen present.html): one self-contained presentation page for judges, drawn only from committed evidence.

Reads the discovery admission ledger, gate factorial, detector epoch ledgers, OCR-vs-boxes receipt and two demo
screenshots (embedded as small JPEG data URIs). No network, no external data. Synthetic data only.
  python3 scripts/redteam/build_present_page.py
"""
from __future__ import annotations
import base64, hashlib, io, json, subprocess
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
# docs/judges/present.html is frozen: docs/judges/FINAL_PUBLIC_DATA_COVERAGE_20261102_V1.json pins its exact bytes.
# Later versions are append-only successors.
OUT = R / 'docs/judges/present_v2.html'


def j(rel): return json.loads((R / rel).read_text())
def jl(rel): return [json.loads(x) for x in (R / rel).read_text().splitlines() if x.strip()]
def sha(rel): return hashlib.sha256((R / rel).read_bytes()).hexdigest()


def thumb(rel, w=960):
    from PIL import Image
    im = Image.open(R / rel).convert('RGB')
    if im.width > w:
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=78, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


def data():
    adm = j('evidence/admission/REDTEAM_DISCOVERY_ADMISSION_V1.json')
    gf = j('evidence/redteam/gate_factorial.json')['configurations']
    gates = [{'config': k, 'detection': v['planted_detection_rate'], 'false_admissions': v['false_admissions'], 'coverage': v['coverage'],
              'planted': v['planted_cells'], 'cells': v['cells']} for k, v in gf.items()]
    epochs = {}
    for run in ('full', 'no_scan'):
        epochs[run] = [{'epoch': e['epoch'], 'dev_pass_rate': e['dev_pass_rate'], 'dev_pass': e['dev_pass'], 'dev_images': e['dev_images'],
                        'map50': e['trainer_metrics'].get('metrics/mAP50(B)'), 'status': e['status'],
                        'p': e['pairing'].get('p_mcnemar_exact_two_sided')} for e in jl(f'evidence/redteam/detector/{run}/epoch_ledger.jsonl')]
    bo = j('docs/demo/ocr_boxes_vs_clean.json')
    try:
        commit = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=R, capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = 'unknown'
    keys = ['evidence/admission/REDTEAM_DISCOVERY_ADMISSION_V1.json', 'evidence/redteam/trained_gain/trained_gain_rows.json',
            'evidence/redteam/gate_factorial.json', 'evidence/redteam/db/field_answers.jsonl',
            'evidence/redteam/detector/full/epoch_ledger.jsonl', 'evidence/redteam/detector/no_scan/epoch_ledger.jsonl', 'docs/demo/ocr_boxes_vs_clean.json']
    return {'admission': adm, 'gates': gates, 'epochs': epochs,
            'boxes': {'clean': bo['clean_fields_correct'], 'boxed': bo['boxes_fields_correct'], 'total': bo['fields_total'], 'images': bo['images']},
            'sources': [{'path': k, 'sha256': sha(k)} for k in keys], 'built_from_commit': commit,
            'images': {'overlay': thumb('docs/demo/overlay/synform2-ce08cff8d07665997ab7_clean.png'),
                       'qwen3': thumb('docs/demo/screenshots/models/synform2-ce08cff8d07665997ab7_scan__qwen3_1.7b__boxes.png'),
                       'qwen25vl': thumb('docs/demo/screenshots/models/synform2-ce08cff8d07665997ab7_scan__qwen2.5vl_3b__boxes.png')}}


def main():
    tpl = (R / 'scripts/redteam/present_page_template.html').read_text()
    OUT.write_text(tpl.replace('__DATA__', json.dumps(data(), separators=(',', ':')).replace('</', '<\\/')))
    print('WROTE', OUT.relative_to(R), round(OUT.stat().st_size / 1024), 'KB')


if __name__ == '__main__':
    main()
