#!/usr/bin/env python3
"""Train a small local field-box detector (Ultralytics YOLOv8n) on the SYNFORM2 YOLO dataset and evaluate it on the frozen
test split, then export detections for the validator role. Everything stays on the host; the only download is the
yolov8n.pt starting weights from Ultralytics' GitHub release (recorded with its sha256). Writes a receipt with the trained
weights' sha256, epochs, device, mAP50/mAP50-95 on val and test, and per-image detections (class, conf, box) for the test
split and for SYNFORM2-ERR images (served from the local test server).
"""
from __future__ import annotations
import argparse, hashlib, json, platform, time, urllib.request
from pathlib import Path


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--epochs', type=int, default=30)
    ap.add_argument('--imgsz', type=int, default=640)
    ap.add_argument('--device', default='mps')
    ap.add_argument('--out', required=True)
    ap.add_argument('--err-server', default='http://127.0.0.1:8766')
    ap.add_argument('--err-dir', default='')
    a = ap.parse_args()
    from ultralytics import YOLO
    import ultralytics, torch
    t0 = time.time()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    model = YOLO('yolov8n.pt')
    start_sha = sha('yolov8n.pt')
    res = model.train(data=str(Path(a.dataset) / 'dataset.yaml'), epochs=a.epochs, imgsz=a.imgsz, device=a.device, project=str(out), name='field_detector', exist_ok=True,
                      seed=20261102, deterministic=True, verbose=False, plots=False, workers=2)
    best = Path(res.save_dir) / 'weights' / 'best.pt'
    trained = YOLO(str(best))
    val = trained.val(data=str(Path(a.dataset) / 'dataset.yaml'), split='val', device=a.device, verbose=False, plots=False)
    test = trained.val(data=str(Path(a.dataset) / 'dataset.yaml'), split='test', device=a.device, verbose=False, plots=False)
    names = trained.names
    dets = {}
    for img in sorted((Path(a.dataset) / 'images' / 'test').glob('*.png')):
        r = trained.predict(str(img), device=a.device, verbose=False, conf=0.25)[0]
        dets[img.stem] = [{'class': names[int(c)], 'conf': float(s), 'box': [float(v) for v in b]} for c, s, b in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist())]
    err_dets = {}
    if a.err_dir:
        E = Path(a.err_dir)
        for rec in map(json.loads, (E / 'public/inputs.jsonl').read_text().splitlines()):
            with urllib.request.urlopen(a.err_server + '/' + rec['png_relative_path'], timeout=30) as resp:
                b = resp.read()
            if hashlib.sha256(b).hexdigest() != rec['png_sha256']:
                raise SystemExit('SERVED_PNG_SHA_MISMATCH')
            tmp = out / 'tmp_err.png'; tmp.write_bytes(b)
            r = trained.predict(str(tmp), device=a.device, verbose=False, conf=0.25)[0]
            err_dets[rec['image_id']] = [{'class': names[int(c)], 'conf': float(s), 'box': [float(v) for v in bb]} for c, s, bb in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist())]
        tmp.unlink(missing_ok=True)
    receipt = {'schema': 'redteam.detector_training.v1', 'framework': f'ultralytics {ultralytics.__version__}, torch {torch.__version__}', 'device': a.device, 'host': platform.node(),
               'start_weights': {'file': 'yolov8n.pt', 'sha256': start_sha, 'source': 'Ultralytics GitHub release download'}, 'trained_weights_sha256': sha(best), 'trained_weights_path': str(best),
               'epochs': a.epochs, 'imgsz': a.imgsz, 'seed': 20261102, 'dataset_manifest': json.loads((Path(a.dataset) / 'manifest.json').read_text()),
               'val': {'mAP50': float(val.box.map50), 'mAP50_95': float(val.box.map)}, 'test': {'mAP50': float(test.box.map50), 'mAP50_95': float(test.box.map)},
               'wall_seconds': round(time.time() - t0, 1), 'detections_test_images': len(dets), 'detections_err_images': len(err_dets), 'energy': 'NOT_OBSERVED'}
    (out / 'detector_receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    (out / 'detections_test.json').write_text(json.dumps(dets, sort_keys=True) + '\n')
    (out / 'detections_err.json').write_text(json.dumps(err_dets, sort_keys=True) + '\n')
    print('TRAIN_DONE', json.dumps({k: receipt[k] for k in ('val', 'test', 'epochs', 'wall_seconds', 'trained_weights_sha256')}))


if __name__ == '__main__':
    main()
