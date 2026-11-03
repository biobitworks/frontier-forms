#!/usr/bin/env python3
"""Per-epoch Merkle breakpoint training for the local field-box detector (YOLOv8n) — vita/daisy-style epoch ledger.

After EVERY epoch (Ultralytics `on_model_save` callback, i.e. once last.pt for that epoch exists):
  1. hash the epoch weights (sha256 of last.pt) and copy them to epoch_<k>.pt (append-only);
  2. score the epoch model per image on the frozen DEV split only (test stays untouched until the end):
     image PASS = every one of the 7 value-field classes has a predicted box with IoU >= 0.5 against the renderer's GT box;
  3. pair the epoch against the previous epoch on the same dev images: exact two-sided McNemar on discordant images,
     stratified (clean/scan) paired bootstrap of the pass-rate delta (2,000 replicates per epoch, seed 20261102);
  4. label the epoch GAIN (p < 0.05, delta > 0, bootstrap lower CI > 0), LOSS (p < 0.05, delta < 0) or NEUTRAL;
  5. append a canonical leaf {epoch, weights_sha256, metrics, pairing, status, parent_root} and recompute the chain root
     (sha256(00||leaf); sha256(01||L||R); duplicate-last; leaf 0 binds the count and the SYNFORM2 root) — every epoch is
     committed whether it is a gain, a loss or neutral; nothing is overwritten.
LOMO at the training level is a separate run with one data mechanism removed (--lomo no_scan trains on clean renders only);
its ledger chains to the same parent so the two curves are comparable epoch by epoch.
At the end: final evaluation on the untouched TEST split with the best-by-dev checkpoint, and detections for the validator.
"""
from __future__ import annotations
import argparse, hashlib, json, math, platform, shutil, time, urllib.request
from pathlib import Path
import numpy as np

FIELDS = ('Synthetic case', 'Patient first', 'Patient last', 'Birth date', 'Gender', 'Encounter date', 'Visit class')
W, H = 900, 560


def canon(o): return json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(Path(p).read_bytes())
def leaf(o): return hashlib.sha256(b'\x00' + canon(o)).digest()


def root(leaves):
    v = list(leaves)
    while len(v) > 1:
        if len(v) % 2:
            v.append(v[-1])
        v = [hashlib.sha256(b'\x01' + v[i] + v[i + 1]).digest() for i in range(0, len(v), 2)]
    return v[0].hex()


def iou(a, b):
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def gt_for(label_path):
    out = {}
    for line in Path(label_path).read_text().splitlines():
        c, cx, cy, w, h = line.split(); c = int(c)
        if c < 7:
            out[c] = [(float(cx) - float(w) / 2) * W, (float(cy) - float(h) / 2) * H, (float(cx) + float(w) / 2) * W, (float(cy) + float(h) / 2) * H]
    return out


def exact_mcnemar(b, c):
    n = b + c
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n) if n else 1.0


def score_split(model, images, labels_dir, device):
    res = {}
    for img in images:
        gt = gt_for(labels_dir / (img.stem + '.txt'))
        r = model.predict(str(img), device=device, verbose=False, conf=0.25)[0]
        preds = list(zip(r.boxes.cls.tolist(), r.boxes.xyxy.tolist()))
        per = {}
        for c in range(7):
            best = max((iou(b, gt[c]) for cl, b in preds if int(cl) == c), default=0.0)
            per[c] = best >= 0.5
        res[img.stem] = {'pass': all(per.values()), 'fields_ok': sum(per.values()), 'variant': 'scan' if img.stem.endswith('_scan') else 'clean'}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--epochs', type=int, default=30)
    ap.add_argument('--imgsz', type=int, default=640)
    ap.add_argument('--device', default='mps')
    ap.add_argument('--out', required=True)
    ap.add_argument('--lomo', default='full', choices=['full', 'no_scan'])
    ap.add_argument('--err-server', default='http://127.0.0.1:8766')
    ap.add_argument('--err-dir', default='')
    ap.add_argument('--parent-root', required=True, help='SYNFORM2 root the dataset was built from')
    a = ap.parse_args()
    from ultralytics import YOLO
    import ultralytics, torch
    D = Path(a.dataset); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / 'epochs').mkdir(exist_ok=True)
    data_yaml = D / 'dataset.yaml'
    if a.lomo == 'no_scan':
        # LOMO: remove the scan-variant mechanism from TRAINING only (dev/test unchanged) via a filtered train list
        lst = out / 'train_no_scan.txt'
        lst.write_text('\n'.join(str(p) for p in sorted((D / 'images/train').glob('*_clean.png'))) + '\n')
        data_yaml = out / 'dataset_no_scan.yaml'
        data_yaml.write_text((D / 'dataset.yaml').read_text().replace('train: images/train', f'train: {lst.resolve()}'))
    val_images = sorted((D / 'images/val').glob('*.png')); labels_val = D / 'labels/val'
    ledger_path = out / 'epoch_ledger.jsonl'; chain_path = out / 'chain_manifest.json'
    if ledger_path.exists():
        raise SystemExit('APPEND_ONLY_LEDGER_EXISTS')
    state = {'prev': None, 'leaves': [], 'rows': [], 'context': None}
    rng = np.random.default_rng(20261102)
    context = {'type': 'EPOCH_CHAIN_CONTEXT', 'schema': 'fco.detector_epoch_chain.v1', 'parent_synform2_root': a.parent_root, 'lomo': a.lomo, 'epochs_planned': a.epochs,
               'start_weights_sha256': sha_file('yolov8n.pt'), 'framework': f'ultralytics {ultralytics.__version__} torch {torch.__version__}', 'device': a.device,
               'dev_images': len(val_images), 'pass_rule': 'all 7 value classes IoU>=0.5 vs renderer GT', 'alpha': 0.05, 'bootstrap_reps': 2000, 'seed': 20261102, 'host': platform.node()}
    state['context'] = context
    state['leaves'] = [leaf(context)]

    def on_model_save(trainer):
        ep = int(trainer.epoch) + 1
        wpath = Path(trainer.last)
        if not wpath.exists():
            return
        snap = out / 'epochs' / f'epoch_{ep:03d}.pt'
        if not snap.exists():
            shutil.copyfile(wpath, snap)
        wsha = sha_file(snap)
        m = YOLO(str(snap))
        cur = score_split(m, val_images, labels_val, a.device)
        n = len(cur); passes = sum(1 for v in cur.values() if v['pass']); fields = sum(v['fields_ok'] for v in cur.values())
        pairing = {'previous_epoch': None, 'baseline_only': None, 'epoch_only': None, 'p_mcnemar_exact_two_sided': None, 'delta_pass_rate': None, 'ci95': None}
        status = 'FIRST_EPOCH'
        prev = state['prev']
        if prev is not None:
            b = sum(1 for k in cur if prev[k]['pass'] and not cur[k]['pass']); c = sum(1 for k in cur if cur[k]['pass'] and not prev[k]['pass'])
            p = exact_mcnemar(b, c); delta = (passes - sum(1 for v in prev.values() if v['pass'])) / n
            groups = {}
            for k in cur:
                groups.setdefault(cur[k]['variant'], []).append(int(cur[k]['pass']) - int(prev[k]['pass']))
            sums = np.zeros(2000)
            for arr in groups.values():
                arr = np.array(arr); idx = rng.integers(0, len(arr), size=(2000, len(arr))); sums += arr[idx].sum(axis=1)
            d = np.sort(sums / n); lo, hi = float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))
            pairing = {'previous_epoch': ep - 1, 'baseline_only': b, 'epoch_only': c, 'p_mcnemar_exact_two_sided': p, 'delta_pass_rate': delta, 'ci95': [lo, hi]}
            status = 'GAIN' if (p < 0.05 and delta > 0 and lo > 0) else ('LOSS' if (p < 0.05 and delta < 0) else 'NEUTRAL')
        metrics = {k: float(v) for k, v in (trainer.metrics or {}).items() if isinstance(v, (int, float))}
        row = {'epoch': ep, 'weights_sha256': wsha, 'weights_file': snap.name, 'dev_images': n, 'dev_pass': passes, 'dev_pass_rate': passes / n, 'dev_fields_ok': fields, 'dev_fields_total': 7 * n,
               'trainer_metrics': metrics, 'pairing': pairing, 'status': status, 'parent_root': (chain_root_current() if state['rows'] else a.parent_root),
               'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        state['leaves'].append(leaf(row)); state['rows'].append(row); state['prev'] = cur
        with ledger_path.open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
        write_chain()
        print(f"EPOCH {ep} status={status} dev_pass={passes}/{n} fields={fields}/{7*n} p={pairing['p_mcnemar_exact_two_sided']} delta={pairing['delta_pass_rate']} root={chain_root_current()[:16]}", flush=True)

    def chain_root_current():
        return root(state['leaves'])

    def write_chain():
        ctx = dict(state['context'], leaf_count=len(state['leaves']))
        leaves = [leaf(ctx)] + state['leaves'][1:]
        chain_path.write_text(json.dumps({'schema': 'fco.detector_epoch_chain.v1', 'root': root(leaves), 'leaf_count': len(leaves), 'context': ctx,
                                          'epochs_committed': len(state['rows']), 'statuses': [r['status'] for r in state['rows']], 'signed': 'NOT_SIGNED', 'MMR': 'NOT_COMPUTED'}, indent=2, sort_keys=True) + '\n')
        state['leaves'][0] = leaf(ctx)

    model = YOLO('yolov8n.pt')
    model.add_callback('on_model_save', on_model_save)
    t0 = time.time()
    res = model.train(data=str(data_yaml), epochs=a.epochs, imgsz=a.imgsz, device=a.device, project=str(out), name='run', exist_ok=True, seed=20261102, deterministic=True,
                      verbose=False, plots=False, workers=2, save_period=1)
    best = Path(res.save_dir) / 'weights' / 'best.pt'
    trained = YOLO(str(best))
    test_images = sorted((D / 'images/test').glob('*.png')); test_scores = score_split(trained, test_images, D / 'labels/test', a.device)
    testval = trained.val(data=str(D / 'dataset.yaml'), split='test', device=a.device, verbose=False, plots=False)
    dets = {img.stem: [{'class': trained.names[int(c)], 'conf': float(s), 'box': [float(v) for v in b]} for c, s, b in zip(*(lambda r: (r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist()))(trained.predict(str(img), device=a.device, verbose=False, conf=0.25)[0]))] for img in test_images}
    err_dets = {}
    if a.err_dir:
        E = Path(a.err_dir); tmp = out / 'tmp_err.png'
        for rec in map(json.loads, (E / 'public/inputs.jsonl').read_text().splitlines()):
            with urllib.request.urlopen(a.err_server + '/' + rec['png_relative_path'], timeout=30) as resp:
                b = resp.read()
            if sha_bytes(b) != rec['png_sha256']:
                raise SystemExit('SERVED_PNG_SHA_MISMATCH')
            tmp.write_bytes(b); r = trained.predict(str(tmp), device=a.device, verbose=False, conf=0.25)[0]
            err_dets[rec['image_id']] = [{'class': trained.names[int(c)], 'conf': float(s), 'box': [float(v) for v in bb]} for c, s, bb in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist())]
        tmp.unlink(missing_ok=True)
    final = {'schema': 'redteam.detector_training.v2', 'lomo': a.lomo, 'best_weights_sha256': sha_file(best), 'best_selected_by': 'dev (val) fitness, never test',
             'test': {'mAP50': float(testval.box.map50), 'mAP50_95': float(testval.box.map), 'images': len(test_images), 'image_pass': sum(1 for v in test_scores.values() if v['pass']),
                      'fields_ok': sum(v['fields_ok'] for v in test_scores.values()), 'fields_total': 7 * len(test_images)},
             'epochs_committed': len(state['rows']), 'statuses': [r['status'] for r in state['rows']], 'chain_root': json.loads(chain_path.read_text())['root'] if chain_path.exists() else None,
             'wall_seconds': round(time.time() - t0, 1), 'detections_test_images': len(dets), 'detections_err_images': len(err_dets), 'energy': 'NOT_OBSERVED', 'framework': context['framework'], 'device': a.device}
    (out / 'final_receipt.json').write_text(json.dumps(final, indent=2, sort_keys=True) + '\n')
    (out / 'detections_test.json').write_text(json.dumps(dets, sort_keys=True) + '\n')
    (out / 'detections_err.json').write_text(json.dumps(err_dets, sort_keys=True) + '\n')
    (out / 'test_scores.json').write_text(json.dumps(test_scores, sort_keys=True) + '\n')
    print('TRAIN_DONE', json.dumps({k: final[k] for k in ('lomo', 'test', 'epochs_committed', 'statuses', 'chain_root', 'wall_seconds')}))


if __name__ == '__main__':
    main()
