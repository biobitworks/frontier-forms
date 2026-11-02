#!/usr/bin/env python3
"""Bounding-box lane: Qwen2.5-VL grounding (value text + bbox per field) scored against the renderer's exact field geometry,
plus Apple Vision boxes from the OCR lane. Ground truth boxes are computed from the same Pillow font the renderer used, so
IoU is exact on clean renders and approximate on rotated scan variants (reported per variant).

One model call per image: the model returns a JSON list of {field, value, bbox_2d:[x1,y1,x2,y2]} in pixel coordinates
(900x560). Outputs the actual answers, boxes and IoU per field. YOLO is NOT used: no trained form-field detector exists
locally; the GT boxes produced here are the labels such a detector would be trained on (see TRAINING_READINESS.md).
"""
from __future__ import annotations
import argparse, base64, json, platform, sys, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from redteam_forms_vlm import FIELDS, norm, sha, jsonl, OLLAMA

W, H = 900, 560
PROMPT = ('This is a SYNTHETIC (not real) encounter intake form, 900x560 pixels. For each of these labels: ' + ', '.join(f'"{f}"' for f in FIELDS) +
          ' return the printed VALUE and the bounding box of that value text as bbox_2d [x1, y1, x2, y2] in pixel coordinates. '
          'Return only JSON: {"fields": [{"field": "...", "value": "...", "bbox_2d": [x1, y1, x2, y2]}, ...]}')


def gt_boxes(fields):
    from PIL import ImageFont
    font = ImageFont.load_default(size=18)
    out = {}
    for i, f in enumerate(FIELDS):
        y = 110 + 58 * i
        l, t, r, b = font.getbbox(str(fields[f]) if fields[f] else ' ')
        out[f] = [290 + l, y + t, 290 + r, y + b]
    return out


def iou(a, b):
    if not a or not b or len(a) != 4 or len(b) != 4:
        return None
    try:
        ax1, ay1, ax2, ay2 = [float(v) for v in a]; bx1, by1, bx2, by2 = [float(v) for v in b]
    except Exception:
        return None
    ix1, iy1, ix2, iy2 = max(ax1, bx1), max(ay1, by1), min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / ua if ua > 0 else 0.0


def vision_box_px(line):
    """Vision normalized box (origin bottom-left) -> pixel box (origin top-left)."""
    return [line['x'] * W, (1 - line['y'] - line['h']) * H, (line['x'] + line['w']) * W, (1 - line['y']) * H]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--server', required=True)
    ap.add_argument('--dataset-dir', required=True)
    ap.add_argument('--ocr-local', required=True)
    ap.add_argument('--model', default='qwen2.5vl:3b')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--tag', default='BBOX')
    ap.add_argument('--label', default='synform2')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    t_start = time.time()
    D = Path(a.dataset_dir); man = json.loads((D / 'public/manifest.json').read_text())
    inputs = {r['input_fco_id']: r for r in jsonl(D / 'public/inputs.jsonl')}
    oracle = {o['case_id']: o['gold_fields'] for o in jsonl(D / '.private/oracle.jsonl')}
    ocr = {r['input_fco_id']: r for r in jsonl(a.ocr_local)}
    rows = [ocr[k] for k in ocr]
    if a.limit:
        rows = rows[:a.limit]
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{a.tag}_{a.model.replace(':', '_')}_{a.label}"
    pp = out_dir / (stem + '_PUBLIC.jsonl')
    if pp.exists():
        raise SystemExit('APPEND_ONLY')
    with pp.open('x') as pf:
        for i, o in enumerate(rows):
            r = inputs[o['input_fco_id']]; gold = oracle[r.get('image_id', r['case_id'])]
            with urllib.request.urlopen(a.server + '/' + r['png_relative_path'], timeout=30) as resp:
                png = resp.read()
            if sha(png) != r['png_sha256']:
                raise SystemExit('SERVED_PNG_SHA_MISMATCH')
            payload = {'model': a.model, 'stream': False, 'format': 'json', 'messages': [{'role': 'user', 'content': PROMPT, 'images': [base64.b64encode(png).decode()]}],
                       'options': {'temperature': 0, 'seed': 20261102, 'num_predict': 700}}
            t0 = time.monotonic()
            try:
                res = json.load(urllib.request.urlopen(urllib.request.Request(OLLAMA + '/api/chat', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}), timeout=600))
                content = (res.get('message') or {}).get('content', ''); status = 'EXECUTED'
                try:
                    parsed = json.loads(content)
                except Exception:
                    parsed = {}
            except Exception as e:
                content, parsed, status, res = '', {}, 'FAILED:' + type(e).__name__, {}
            items = parsed.get('fields') if isinstance(parsed, dict) else None
            vlm = {}
            for it in (items or []):
                if isinstance(it, dict) and it.get('field') in FIELDS:
                    vlm[it['field']] = {'value': it.get('value'), 'bbox': it.get('bbox_2d')}
            gt = gt_boxes(gold)
            # Apple Vision box for the value: the OCR line whose text equals the parsed value for this field (geometric parser output)
            per = {}
            for f in FIELDS:
                v = vlm.get(f, {}); ocr_val = o['fields'].get(f)
                vis_line = next((l for l in o['ocr_lines'] if ocr_val is not None and l['text'].strip() == str(ocr_val).strip()), None)
                per[f] = {'printed': gold[f], 'vlm_value': v.get('value'), 'vlm_bbox': v.get('bbox'), 'vlm_value_correct': norm(f, v.get('value')) == norm(f, gold[f]),
                          'vlm_iou': iou(v.get('bbox'), gt[f]), 'vision_value': ocr_val, 'vision_value_correct': norm(f, ocr_val) == norm(f, gold[f]),
                          'vision_bbox': vision_box_px(vis_line) if vis_line else None, 'vision_iou': iou(vision_box_px(vis_line), gt[f]) if vis_line else None, 'gt_bbox': gt[f]}
            rec = {'case_id': r['case_id'], 'image_id': r.get('image_id'), 'variant': o.get('variant', 'hidden'), 'split': o.get('split'), 'input_fco_id': r['input_fco_id'],
                   'model': a.model, 'arm': 'vlm_grounding', 'status': status, 'fields': per,
                   'vlm_values_correct': sum(1 for f in FIELDS if per[f]['vlm_value_correct']), 'vision_values_correct': sum(1 for f in FIELDS if per[f]['vision_value_correct']),
                   'vlm_mean_iou': (sum(per[f]['vlm_iou'] or 0 for f in FIELDS) / 7), 'vision_mean_iou': (sum(per[f]['vision_iou'] or 0 for f in FIELDS) / 7),
                   'vlm_iou_ge_0.5': sum(1 for f in FIELDS if (per[f]['vlm_iou'] or 0) >= 0.5), 'vision_iou_ge_0.5': sum(1 for f in FIELDS if (per[f]['vision_iou'] or 0) >= 0.5),
                   'prompt_tokens': res.get('prompt_eval_count'), 'completion_tokens': res.get('eval_count'), 'wall_seconds': round(time.monotonic() - t0, 3), 'raw': content[:800]}
            pf.write(json.dumps(rec, sort_keys=True) + '\n'); pf.flush()
            print('BBOX', i + 1, len(rows), r['case_id'][-8:], rec['variant'], 'vlm_vals', rec['vlm_values_correct'], 'vlm_iou>=.5', rec['vlm_iou_ge_0.5'], 'vision_iou>=.5', rec['vision_iou_ge_0.5'], flush=True)
    meta = {'schema': 'redteam.bbox_lane_run.v1', 'model': a.model, 'dataset': man['dataset'], 'form_root': man['root'], 'images': len(rows), 'host': platform.node(),
            'python': sys.version.split()[0], 'gt_geometry': 'renderer: value text at x=290, y=110+58*i, Pillow default font size 18; GT bbox = font.getbbox offset',
            'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t_start)), 'finished_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'wall_seconds': round(time.time() - t_start, 1), 'public_sha256': sha(pp.read_bytes()), 'values_exported': 'YES_SYNTHETIC_OWNER_AUTHORISED', 'yolo': 'NOT_USED_NO_TRAINED_FIELD_DETECTOR'}
    try:
        tags = json.load(urllib.request.urlopen(OLLAMA + '/api/tags', timeout=5)).get('models', [])
        meta['model_digest'] = next((m.get('digest') for m in tags if m.get('name') == a.model), None)
    except Exception as ex:
        meta['model_digest'] = 'UNKNOWN ' + type(ex).__name__
    (out_dir / (stem + '_META.json')).write_text(json.dumps(meta, sort_keys=True, indent=2) + '\n')
    print('RUN_DONE', json.dumps(meta, sort_keys=True))


if __name__ == '__main__':
    main()
