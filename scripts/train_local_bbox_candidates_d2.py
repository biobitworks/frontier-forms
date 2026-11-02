#!/usr/bin/env python3
"""POST-HOC D2: locally train a proposal classifier on synthetic form borders.

No hosted service, no image/prompt upload. All training is local. This
successor DOES NOT overwrite D1's failed trained U-Net experiment.
Candidate boxes are proposed from horizontal pixel borders, then a trained
binary classifier scores each proposed box using its visual features.
Uses only blank templates for training; all filled patient images held out.
"""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def emit(o):
    return (json.dumps(o,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()

def iou(a,b):
    c=[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
    inter=max(0,c[2]-c[0])*max(0,c[3]-c[1])
    union=max(0,a[2]-a[0])*max(0,a[3]-a[1])+max(0,b[2]-b[0])*max(0,b[3]-b[1])-inter
    return inter/union if union else 0.

def evaluate_truth(truth,guess):
    pairs=sorted(((iou(t,p["bbox"]),i,j) for i,t in enumerate(truth) for j,p in enumerate(guess)),reverse=True)
    gt,pr,m=set(),set(),[]
    for overlap,i,j in pairs:
        if overlap>=.5 and i not in gt and j not in pr:
            gt.add(i);pr.add(j);m.append(overlap)
    return {"tp":len(m),"fp":len(guess)-len(m),"fn":len(truth)-len(m),
            "matched_iou":[round(v,5) for v in m]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",default="data/forms_vision_v1")
    ap.add_argument("--out",default="runs/local_bbox_d2")
    ap.add_argument("--seed",type=int,default=20261102)
    ap.add_argument("--min-line-width",type=int,default=450)
    ap.add_argument("--conf",type=float,default=.5)
    args=ap.parse_args()
    import numpy as np
    from PIL import Image
    import torch
    from torch import nn
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    start=time.monotonic()
    root=Path(args.data);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    goldfile=root/"GOLD_BOXES.json"
    gold=json.loads(goldfile.read_text())
    train_ids=sorted(k for k,v in gold.items() if v["patient_id"] is None)
    patients=sorted({v["patient_id"] for v in gold.values() if v["patient_id"]})
    patients=sorted(patients,key=lambda p:hashlib.sha256((str(args.seed)+p).encode()).hexdigest())
    val=set(patients[:6]);test=set(patients[6:])
    assert val.isdisjoint(test) and len(train_ids)==3
    val_ids=sorted(k for k,v in gold.items() if v["patient_id"] in val)
    test_ids=sorted(k for k,v in gold.items() if v["patient_id"] in test)
    def candidates(k):
        row=gold[k]
        path=root/row["image"]
        gray=np.asarray(Image.open(path).convert("L"))
        h,w=gray.shape
        mask=(gray<180)
        bars=[]
        for y in np.nonzero(mask.sum(axis=1)>args.min_line_width)[0]:
            xs=np.nonzero(mask[y])[0]
            if len(xs)<args.min_line_width:continue
            # Outer rule bars can be wider; field bars expected 480..740 px.
            cuts=np.where(np.diff(xs)>2)[0]+1
            seqs=np.split(xs,cuts)
            for s in seqs:
                if len(s)<args.min_line_width or len(s)>800:continue
                if s[0]>max(100,w//7):continue
                bars.append((int(y),int(s[0]),int(s[-1])))
        # Pair candidate horizontal borders; no gold boxes consulted.
        cand=[]
        for i,(a,al,ar) in enumerate(bars):
            for b,bl,br in bars[i+1:]:
                H=b-a
                if H<16:continue
                if H>100:break
                if abs(al-bl)>8 or abs(ar-br)>8:continue
                x1=max(0,min(al,bl)-1)
                x2=min(w,max(ar,br)+2)
                box=[x1,a,x2,b+1]
                # Visual features: edge continuity, geometry, interior density.
                left=float(mask[a+2:b-1,x1:min(w,x1+3)].mean())
                right=float(mask[a+2:b-1,max(0,x2-3):x2].mean())
                center=float(mask[a+2:b-1,x1+4:x2-4].mean())
                features=[H/110.,(x2-x1)/900.,left,right,center,
                          abs(al-bl)/10.,abs(ar-br)/10.]
                cand.append((box,features))
        return path,(w,h),cand
    train_x=[];train_y=[]
    train_candidate_counts={}
    for key in train_ids:
        _,_,cand=candidates(key)
        true=[f["bbox"] for f in gold[key]["fields"]]
        train_candidate_counts[key]={"candidates":len(cand),"positive":0}
        for box,features in cand:
            label=float(max((iou(box,t) for t in true),default=0)>=.8)
            train_x.append(features);train_y.append(label)
            train_candidate_counts[key]["positive"]+=int(label)
    if not train_y or not (0<sum(train_y)<len(train_y)):
        raise RuntimeError("No balanced candidate training labels; abort")
    X=torch.tensor(train_x,dtype=torch.float32)
    Y=torch.tensor(train_y,dtype=torch.float32).view(-1,1)
    net=nn.Sequential(nn.Linear(7,8),nn.Tanh(),nn.Linear(8,1))
    opt=torch.optim.Adam(net.parameters(),lr=.03)
    positive=(len(Y)-sum(train_y))/sum(train_y)
    criterion=nn.BCEWithLogitsLoss(pos_weight=torch.tensor([positive]))
    history=[]
    for step in range(251):
        opt.zero_grad(); loss=criterion(net(X),Y);loss.backward();opt.step()
        if step%50==0:
            history.append({"step":step,"loss":round(float(loss.item()),6)})
    weights=out/"candidate_classifier_state.pt"
    torch.save(net.state_dict(),weights)
    net.load_state_dict(torch.load(weights,map_location="cpu",weights_only=True))
    net.eval()
    def score(ids,include_predictions):
        totals={"tp":0,"fp":0,"fn":0}
        ious=[];preds=[]
        with torch.no_grad():
            for key in ids:
                path,(w,h),cand=candidates(key)
                fields=[]
                if cand:
                    p=net(torch.tensor([v for _,v in cand],dtype=torch.float32)).sigmoid().flatten().tolist()
                    for (b,_),conf in zip(cand,p):
                        if conf>=args.conf:
                            fields.append({"bbox":b,"confidence":round(conf,6),"bbox_normalized":[
                                round(b[0]/w,6),round(b[1]/h,6),round(b[2]/w,6),round(b[3]/h,6)]})
                true=[f["bbox"] for f in gold[key]["fields"]]
                result=evaluate_truth(true,fields)
                for c in totals:totals[c]+=result[c]
                ious.extend(result["matched_iou"])
                if include_predictions:
                    preds.append({"image_id":key,"image_sha256":digest(path),
                                  "template_key":gold[key]["template_key"],
                                  "image_dimensions":[w,h],
                                  "predictions":fields,
                                  "score":{"tp":result["tp"],"fp":result["fp"],"fn":result["fn"]}})
        recall=totals["tp"]/max(1,totals["tp"]+totals["fn"])
        precision=totals["tp"]/max(1,totals["tp"]+totals["fp"])
        totals.update({"images":len(ids),"precision_iou50":round(precision,5),
                       "recall_iou50":round(recall,5),
                       "f1_iou50":round(2*recall*precision/max(1e-10,recall+precision),5),
                       "mean_matched_iou":round(sum(ious)/len(ious),5) if ious else None})
        return totals,preds
    val_result,_=score(val_ids,False)
    test_result,preds=score(test_ids,True)
    (out/"predictions.jsonl").write_bytes(b"".join(emit(v) for v in preds))
    receipt={
        "schema":"frontier-local-bbox-d2-20261102",
        "status":"EXECUTED", "protocol":"POST_HOC_EXPLORATORY_SUCCESSOR_TO_D1",
        "method":"pixel-line proposals + locally trained neural binary candidate classifier",
        "training_samples":len(Y),"train_positive":int(sum(train_y)),
        "train_negative":len(Y)-int(sum(train_y)),"train_blank_templates":len(train_ids),
        "patient_training_overlap":0,"validation_patients":len(val),
        "test_patients":len(test),"validation":val_result,"test":test_result,
        "weights_sha256":digest(weights),"data_gold_sha256":digest(goldfile),
        "predictions_sha256":digest(out/"predictions.jsonl"),
        "training_image_sha256":{k:digest(root/gold[k]["image"]) for k in train_ids},
        "train_candidate_counts":train_candidate_counts,"train_loss_history":history,
        "hyperparameters":{"seed":args.seed,"confidence":args.conf,"line_min_width":args.min_line_width,
                           "lr":.03,"steps":251,"optimizer":"Adam","model":"Linear(7,8)->Tanh->Linear(8,1)"},
        "device":"local CPU","torch_version":torch.__version__,
        "elapsed_seconds":round(time.monotonic()-start,3),
        "hosted_inference":"NONE","published_pixels":"NONE",
        "generalization":"SAME THREE SYNTHETIC LAYOUTS; NEW LAYOUTS NOT_TESTED",
        "clinical_value_validation":"NOT_TESTED",
        "root":"NOT_COMPUTED",
    }
    (out/"TRAIN_RECEIPT.json").write_bytes(emit(receipt))
    print(json.dumps({"validation":val_result,"test":test_result,
                      "weights_sha256":receipt["weights_sha256"],"receipt":str(out/"TRAIN_RECEIPT.json")}),flush=True)
if __name__=="__main__": main()
