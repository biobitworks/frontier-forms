#!/usr/bin/env python3
"""Train a LOCAL, small field-region segmenter and convert its predictions to
bounding boxes. No network calls. No uploads. NOT a clinical-value validator.

Train: blank synthetic form images with locally randomized visual augmentations.
Validation: six disjoint synthetic patients; final test: remaining 12 patients.
All 18 patients are excluded from training. Labels are DOM gold boxes, not
clinician annotations. Data/images/checkpoints remain local; receipts are JSON.

python3 scripts/train_local_bbox_validator.py \
    --data data/forms_vision_v1 --out runs/local_bbox_v1 --epochs 8
"""
import argparse
import hashlib
import json
import platform
import random
import time
from pathlib import Path

def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()

def intersection_over_union(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union else 0.0

def score_boxes(true_boxes, predicted, threshold=0.5):
    """One-to-one greedy IoU matching, no duplicated credit."""
    pairs = sorted(
        ((intersection_over_union(t, p), i, j)
         for i, t in enumerate(true_boxes) for j, p in enumerate(predicted)),
        reverse=True)
    ti, pi, matches = set(), set(), []
    for iou, i, j in pairs:
        if iou >= threshold and i not in ti and j not in pi:
            matches.append((i, j, iou))
            ti.add(i); pi.add(j)
    return {
        "tp": len(matches), "fn": len(true_boxes)-len(matches),
        "fp": len(predicted)-len(matches),
        "matched_iou": [round(x[2], 5) for x in matches],
        "matched_indices": [[x[0], x[1]] for x in matches],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/forms_vision_v1")
    ap.add_argument("--out", default="runs/local_bbox_v1")
    ap.add_argument("--seed", type=int, default=20261102)
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--steps-per-epoch", type=int, default=20)
    ap.add_argument("--batch", type=int, default=3)
    ap.add_argument("--width", type=int, default=224)
    ap.add_argument("--height", type=int, default=288)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--max-threads", type=int, default=4)
    args = ap.parse_args()

    # Imports are local dependencies; they must already exist on the host.
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    import torch
    from torch import nn
    from torch.nn import functional as F

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.max_threads)
    dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    data_dir, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    gold_path = data_dir / "GOLD_BOXES.json"
    gold = json.loads(gold_path.read_text())
    blank_ids = sorted(k for k, g in gold.items() if g["patient_id"] is None)
    all_patients = sorted({g["patient_id"] for g in gold.values() if g["patient_id"]})
    # Frozen seed-keyed split, no names/values inspected when assigning.
    shuffled = sorted(all_patients, key=lambda x: hashlib.sha256((str(args.seed)+x).encode()).hexdigest())
    val_patients = set(shuffled[:6]); test_patients = set(shuffled[6:])
    if len(blank_ids) < 2 or not val_patients or not test_patients:
        raise RuntimeError("Need blank forms plus disjoint synthetic validation and test patients")
    val_ids = sorted(k for k,g in gold.items() if g["patient_id"] in val_patients)
    test_ids = sorted(k for k,g in gold.items() if g["patient_id"] in test_patients)
    assert len(set(gold[k]["patient_id"] for k in val_ids) & set(gold[k]["patient_id"] for k in test_ids)) == 0
    assert not set(gold[k]["patient_id"] for k in blank_ids) - {None}

    def make_data(k):
        row = gold[k]
        path = data_dir / row["image"]
        im = Image.open(path).convert("L")
        W, H = im.size
        x = 1 - np.asarray(im.resize((args.width,args.height), Image.Resampling.BILINEAR), dtype=np.float32)/255.
        y = np.zeros((args.height,args.width), dtype=np.float32)
        for field in row["fields"]:
            x1,y1,x2,y2 = field["bbox"]
            l = max(0, min(args.width, round(x1*args.width/W)))
            r = max(0, min(args.width, round(x2*args.width/W)))
            t = max(0, min(args.height, round(y1*args.height/H)))
            b = max(0, min(args.height, round(y2*args.height/H)))
            y[t:b,l:r] = 1.
        return torch.from_numpy(x)[None], torch.from_numpy(y)[None], (W,H), path

    blank = [make_data(k) for k in blank_ids]
    val = [(k, make_data(k)) for k in val_ids]
    test = [(k, make_data(k)) for k in test_ids]

    class SmallUNet(nn.Module):
        def __init__(self):
            super().__init__()
            def block(i,o):
                return nn.Sequential(nn.Conv2d(i,o,3,padding=1),nn.ReLU(),
                                     nn.Conv2d(o,o,3,padding=1),nn.ReLU())
            self.e1 = block(1,8)
            self.e2 = block(8,16)
            self.mid = block(16,24)
            self.d2 = block(24+16,16)
            self.d1 = block(16+8,8)
            self.head = nn.Conv2d(8,1,1)
        def forward(self,x):
            a = self.e1(x)
            b = self.e2(F.avg_pool2d(a,2))
            m = self.mid(F.avg_pool2d(b,2))
            d = self.d2(torch.cat([F.interpolate(m,size=b.shape[-2:],mode="nearest"),b],1))
            return self.head(self.d1(torch.cat([F.interpolate(d,size=a.shape[-2:],mode="nearest"),a],1)))

    model = SmallUNet().to(dev)
    opt = torch.optim.AdamW(model.parameters(),lr=0.002)
    weight = torch.tensor(3.,device=dev)
    rng = np.random.default_rng(args.seed)
    history = []

    def augment(x, y):
        # Paired geometric jitter and input-only photometric variations;
        # intentionally NO generated clinical text or test patient pixels.
        dy = int(rng.integers(-9,10)); dx = int(rng.integers(-7,8))
        x = torch.roll(x,(dy,dx),dims=(-2,-1))
        y = torch.roll(y,(dy,dx),dims=(-2,-1))
        x = (x * float(rng.uniform(.78,1.18)) + float(rng.uniform(-.07,.07))
             + torch.randn(x.shape)*float(rng.uniform(0,.035))).clamp(0,1)
        return x, y

    def loss_fn(logits, target):
        bce = F.binary_cross_entropy_with_logits(logits,target,pos_weight=weight)
        p = logits.sigmoid()
        dice = 1 - (2*(p*target).sum()+1)/((p+target).sum()+1)
        return bce+dice

    def predicted_boxes(image, dimensions):
        # This is a MODEL pixel prediction, never a lookup of gold geometry.
        with torch.no_grad():
            prob = model(image[None].to(dev)).sigmoid()[0,0].cpu().numpy()
        mask = ndimage.binary_opening(prob >= args.threshold, structure=np.ones((3,3)))
        labels, n = ndimage.label(mask)
        boxes=[]
        W,H=dimensions
        for i in range(1,n+1):
            ys,xs=np.nonzero(labels==i)
            if len(xs) < 25: continue
            box=[int(round(xs.min()*W/args.width)),int(round(ys.min()*H/args.height)),
                 int(round((xs.max()+1)*W/args.width)),int(round((ys.max()+1)*H/args.height))]
            if (box[2]-box[0]) < 10 or (box[3]-box[1]) < 8: continue
            boxes.append({"bbox":box,"confidence":round(float(prob[labels==i].mean()),5),
                          "bbox_normalized":[round(box[0]/W,6),round(box[1]/H,6),
                                             round(box[2]/W,6),round(box[3]/H,6)]})
        return sorted(boxes,key=lambda x:(x["bbox"][1],x["bbox"][0]))

    def evaluate(cases, include_predictions=False):
        model.eval()
        counts = {"tp":0,"fp":0,"fn":0}
        ious=[]; rows=[]
        with torch.no_grad():
            for key,(image, y, (W,H), path) in cases:
                guesses = predicted_boxes(image,(W,H))
                truth = [f["bbox"] for f in gold[key]["fields"]]
                s = score_boxes(truth,[p["bbox"] for p in guesses])
                for k in counts: counts[k] += s[k]
                ious += s["matched_iou"]
                if include_predictions:
                    rows.append({"image_id":key, "image_sha256":sha256(path),
                                 "template_key":gold[key]["template_key"],
                                 "patient_id":gold[key]["patient_id"],
                                 "image_dimensions":[W,H],"predictions":guesses,
                                 "score":{"tp":s["tp"],"fp":s["fp"],"fn":s["fn"],
                                          "matched_iou":s["matched_iou"]}})
        precision = counts["tp"]/max(1,counts["tp"]+counts["fp"])
        recall = counts["tp"]/max(1,counts["tp"]+counts["fn"])
        counts.update({"precision_iou50":round(precision,5),
                       "recall_iou50":round(recall,5),
                       "f1_iou50":round(2*precision*recall/max(.0000001,precision+recall),5),
                       "mean_matched_iou":round(sum(ious)/len(ious),5) if ious else None,
                       "images":len(cases)})
        return counts, rows

    start=time.monotonic()
    best=-1
    checkpoint=out/"bbox_detector_state.pt"
    for epoch in range(1,args.epochs+1):
        model.train()
        losses=[]
        for _ in range(args.steps_per_epoch):
            b=[augment(*blank[int(rng.integers(0,len(blank)))][:2]) for _ in range(args.batch)]
            x=torch.stack([v[0] for v in b]).to(dev)
            y=torch.stack([v[1] for v in b]).to(dev)
            opt.zero_grad()
            loss=loss_fn(model(x),y)
            loss.backward()
            opt.step()
            losses.append(float(loss.detach().cpu()))
        valid,_=evaluate(val)
        row={"epoch":epoch,"train_loss":round(sum(losses)/len(losses),6),"validation":valid}
        history.append(row)
        print(json.dumps(row,sort_keys=True),flush=True)
        if valid["f1_iou50"] > best:
            best=valid["f1_iou50"]
            torch.save(model.state_dict(),checkpoint)

    # Verify metrics against saved, selected checkpoint rather than final memory.
    model.load_state_dict(torch.load(checkpoint,map_location=dev,weights_only=True))
    valid,_=evaluate(val)
    test_scores, predictions=evaluate(test,include_predictions=True)
    raw=b"".join(canonical(row) for row in predictions)
    (out/"predictions.jsonl").write_bytes(raw)
    manifest={
        "schema":"frontier-forms-local-bbox-v1","task":"bbox-location-only; NOT clinical correctness",
        "train_labels":"DOM rectangles on 3 blank synthetic templates",
        "training_patients":0,"training_blank_images":len(blank_ids),
        "validation_patients":len(val_patients),"test_patients":len(test_patients),
        "validation_images":len(val_ids),"test_images":len(test_ids),
        "split_rule":"seed-keyed SHA256(patient_id); first 6 validate; remainder test",
        "seed":args.seed,"dataset_gold_sha256":sha256(gold_path),
        "train_image_sha256":{k:sha256(data_dir/gold[k]["image"]) for k in blank_ids},
        "validation_ids_sha256":hashlib.sha256(canonical(val_ids)).hexdigest(),
        "test_ids_sha256":hashlib.sha256(canonical(test_ids)).hexdigest(),
        "network":"SmallUNet: 1->8->16->24->16->8->1; segmentation-to-components",
        "weights_sha256":sha256(checkpoint),"predictions_sha256":sha256(out/"predictions.jsonl"),
        "epochs":args.epochs,"steps_per_epoch":args.steps_per_epoch,
        "batch":args.batch,"width":args.width,"height":args.height,
        "box_threshold":args.threshold,"selected_validation_f1":best,
        "validation":valid,"test":test_scores,"history":history,
        "elapsed_seconds":round(time.monotonic()-start,2),
        "device":dev,"torch_version":torch.__version__,
        "host":platform.node(),"hosted_inference":"NONE",
        "weights_publication":"LOCAL_ONLY","pixels_publication":"LOCAL_ONLY",
        "model_generalization":"SAME_3_TEMPLATES_ONLY; external forms NOT_TESTED",
        "clinical_value_validation":"NOT_TESTED","ocr_value_validation":"NOT_TESTED",
    }
    (out/"TRAIN_RECEIPT.json").write_bytes(canonical(manifest))
    print("COMPLETE",json.dumps({"test":test_scores,"weights_sha256":manifest["weights_sha256"],
                                  "receipt":str(out/"TRAIN_RECEIPT.json")}),flush=True)

if __name__=="__main__":
    main()
