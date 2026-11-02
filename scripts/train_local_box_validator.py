#!/usr/bin/env python3
"""Train a lightweight LOCAL pixel vision detector on three synthetic blank forms.

No model API, GPU, external network, real patient data or downloaded weights.
Training image labels are generated from DOM box annotations in GOLD_BOXES.
Evaluation: 54 different filled images from 18 held-out synthetic patients.
The model localizes rectangular input widgets only; it does NOT perform OCR
or validate patient answers. Same form templates occur in train and test.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import sklearn

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/forms_vision_v1"
OUT_DEFAULT = ROOT / "evidence/forms_box_validator/run_v3"
FEATURES = ("log_width","log_height","aspect_ratio","border_dark_fraction",
            "interior_dark_fraction","interior_gray_mean","border_gray_mean",
            "edge_pixels_fraction")
SCHEMA = "frontier-forms.local-box-vision.v1"
CANON = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode()
SHA = lambda x: hashlib.sha256(x).hexdigest()


def iou(a, b):
    x1,y1,x2,y2=max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])
    intersection=max(0,x2-x1)*max(0,y2-y1)
    aa=max(0,a[2]-a[0])*max(0,a[3]-a[1])
    ab=max(0,b[2]-b[0])*max(0,b[3]-b[1])
    return intersection/(aa+ab-intersection) if aa+ab>intersection else 0.0


def candidates(gray):
    bw=cv2.threshold(gray,190,255,cv2.THRESH_BINARY_INV)[1]
    contours,_=cv2.findContours(bw,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    boxes=set()
    for cnt in contours:
        x,y,w,h=cv2.boundingRect(cnt)
        if 15 <= w <= 820 and 10 <= h <= 110:
            boxes.add((x,y,x+w,y+h))
    return sorted(boxes,key=lambda b:(b[1],b[0],b[3],b[2]))


def feature(gray, box):
    x1,y1,x2,y2=box
    roi=gray[y1:y2,x1:x2]
    h,w=roi.shape
    if min(h,w)<3:raise ValueError("INVALID_BOX")
    border=np.concatenate((roi[:2,:].ravel(),roi[-2:,:].ravel(),roi[:, :2].ravel(),roi[:, -2:].ravel()))
    inner=roi[2:-2,2:-2] if h>4 and w>4 else roi
    ed=cv2.Canny(roi,80,180)
    return [float(math.log1p(w)),float(math.log1p(h)),float(w/h),
            float(np.mean(border<200)),float(np.mean(inner<200)),
            float(np.mean(inner)),float(np.mean(border)),float(np.mean(ed>0))]


def scored_boxes(gray, weights, threshold=0.5):
    X=np.array([feature(gray,b) for b in candidates(gray)],dtype=np.float64)
    boxes=candidates(gray)
    if not boxes:return []
    mu=np.array(weights["scaler_mean"],dtype=np.float64)
    scale=np.array(weights["scaler_scale"],dtype=np.float64)
    coef=np.array(weights["coef"],dtype=np.float64)
    bias=float(weights["intercept"])
    z=np.clip(((X-mu)/scale)@coef+bias,-50,50)
    probs=1/(1+np.exp(-z))
    ranked=sorted([(float(p),list(b)) for p,b in zip(probs,boxes) if p>=threshold],
                  key=lambda x:(-x[0],x[1][1],x[1][0]))
    result=[]
    for conf,b in ranked:
        if any(iou(b,prev["bbox"])>0.75 for prev in result):
            continue
        result.append({"bbox":b,"confidence":round(conf,8)})
    return sorted(result,key=lambda x:(x["bbox"][1],x["bbox"][0]))


def heuristic_boxes(gray):
    boxes=[list(b) for b in candidates(gray) if b[2]-b[0]>=80 and (b[2]-b[0])/(b[3]-b[1])>1.5]
    selected=[]
    for b in sorted(boxes,key=lambda b:-(b[2]-b[0])*(b[3]-b[1])):
        if any(iou(b,p)>0.75 for p in selected):continue
        selected.append(b)
    return sorted(selected,key=lambda b:(b[1],b[0]))


def score(pred, expected):
    matched=set()
    hits=[]
    for f in expected:
        scores=sorted(((iou(f["bbox"],p["bbox"] if isinstance(p,dict) else p),j)
                      for j,p in enumerate(pred) if j not in matched),reverse=True)
        if scores and scores[0][0]>=0.5:
            matched.add(scores[0][1])
            hits.append({"field_key":f["field_key"],"found":True,
                         "iou":round(scores[0][0],8),"proposal_index":scores[0][1]})
        else:
            hits.append({"field_key":f["field_key"],"found":False,"iou":0.0,"proposal_index":None})
    return {"n_gt":len(expected),"n_predictions":len(pred),"true_positive":len(matched),
            "false_positive":len(pred)-len(matched),"false_negative":len(expected)-len(matched),
            "field_hits":hits}


def exact_mcnemar(b,c):
    n=b+c
    if n==0:return 1.0
    return float(min(1.0,2*sum(math.comb(n,k) for k in range(min(b,c)+1))/(2**n)))


def root(leaves):
    level=[hashlib.sha256(b"\x00"+CANON(x)).digest() for x in leaves]
    if not level:return hashlib.sha256(b"\x00EMPTY").hexdigest()
    while len(level)>1:
        level=[hashlib.sha256(b"\x01"+level[i]+(level[i+1] if i+1<len(level) else level[i])).digest()
               for i in range(0,len(level),2)]
    return level[0].hex()


def run(out):
    source=json.loads((SOURCE/"GOLD_BOXES.json").read_text())
    blanks=sorted((k,v) for k,v in source.items() if v["patient_id"] is None)
    evals=sorted((k,v) for k,v in source.items() if v["patient_id"] is not None)
    if len(blanks)!=3 or len(evals)!=54:raise AssertionError("EXPECTED_SYNTHETIC_SOURCE_COUNTS")
    trainX=[];trainY=[]
    input_pins=[]
    for name,row in blanks+evals:
        p=SOURCE/row["image"]
        image=cv2.imread(str(p),cv2.IMREAD_GRAYSCALE)
        if image is None:raise AssertionError("MISSING_IMAGE "+str(p))
        input_pins.append({"image":row["image"],"sha256":SHA(p.read_bytes()),
                           "sample_group":"blank_train" if row["patient_id"] is None else "heldout_filled_eval",
                           "n_labels":len(row["fields"])})
        if row["patient_id"] is None:
            labels=[f["bbox"] for f in row["fields"]]
            for box in candidates(image):
                is_positive=max(iou(box,b) for b in labels)>=0.8
                trainX.append(feature(image,box))
                trainY.append(int(is_positive))
    if set(trainY)!={0,1}:raise AssertionError("TRAINING_CLASSES_ABSENT")
    scaler=StandardScaler().fit(np.array(trainX,dtype=np.float64))
    model=LogisticRegression(C=1.0,max_iter=2000,class_weight="balanced",
                             random_state=20261102,solver="lbfgs")
    model.fit(scaler.transform(np.array(trainX)),np.array(trainY))
    weights={"schema":SCHEMA+".weights","classifier":"sklearn.LogisticRegression",
             "classes":[0,1],"features":list(FEATURES),"scaler_mean":scaler.mean_.tolist(),
             "scaler_scale":scaler.scale_.tolist(),"coef":model.coef_[0].tolist(),
             "intercept":float(model.intercept_[0]),"threshold":0.5,
             "train_image_count":len(blanks),"train_candidates":len(trainY),
             "train_positive":sum(trainY),"train_negative":len(trainY)-sum(trainY),
             "seed":20261102,"provider":"LOCAL_CPU_ONLY","not_an_llm":True,
             "model_sha256":"TO_BE_COMPUTED"}
    raw_weights={k:v for k,v in weights.items() if k!="model_sha256"}
    weights["model_sha256"]=SHA(CANON(raw_weights))
    out.mkdir(parents=True,exist_ok=True)
    (out/"weights.json").write_bytes(json.dumps(weights,indent=2,sort_keys=True).encode()+b"\n")
    patient_records=[]
    by_patient=defaultdict(list)
    pred_rows=[]
    records=[]
    for name,row in evals:
        p=SOURCE/row["image"]
        im=cv2.imread(str(p),cv2.IMREAD_GRAYSCALE)
        preds=scored_boxes(im,weights)
        heur=heuristic_boxes(im)
        learned=score(preds,row["fields"])
        control=score(heur,row["fields"])
        pid=row["patient_id"]
        by_patient[pid].append((learned,control))
        record={"id":name,"image_sha256":SHA(p.read_bytes()),"form_family":row["template_key"],
                "synthetic_patient_digest":SHA(pid.encode()),"trained_detector":learned,
                "control_contour_detector":control,"box_predictions":preds,
                "decision":"DETECTION_ONLY_NOT_OCR"}
        pred_rows.append(record)
        records.append({"id":name,"image_sha256":record["image_sha256"],
                        "pred_box_sha256":SHA(CANON(preds)),"learned_hit":learned["true_positive"],
                        "control_hit":control["true_positive"]})
    if len(by_patient)!=18:raise AssertionError("EXPECTED_PATIENT_HOLDOUT")
    pairs=[]
    for row in pred_rows:
        l=row["trained_detector"]["field_hits"]
        c=row["control_contour_detector"]["field_hits"]
        assert len(l)==len(c)
        pairs.extend((int(x["found"]),int(y["found"])) for x,y in zip(l,c))
    n=len(pairs)
    minus=sum(c and not l for l,c in pairs)
    plus=sum(l and not c for l,c in pairs)
    rng=np.random.default_rng(20261102)
    pids=sorted(by_patient)
    differences=[]
    for _ in range(10000):
        sampled=rng.choice(len(pids),size=len(pids),replace=True)
        num=den=0
        for i in sampled:
            for a,b in by_patient[pids[int(i)]]:
                num+=a["true_positive"]-b["true_positive"]
                den+=a["n_gt"]
        differences.append(num/den if den else 0)
    full=[r for r in pred_rows]
    total=sum(r["trained_detector"]["n_gt"] for r in full)
    learned_hits=sum(r["trained_detector"]["true_positive"] for r in full)
    baseline_hits=sum(r["control_contour_detector"]["true_positive"] for r in full)
    summary={"schema":SCHEMA,"data_kind":"MITRE Synthea synthetic rendered HTML forms",
             "input_dataset":"data/forms_vision_v1/GOLD_BOXES.json",
             "source_metadata_sha256":SHA((SOURCE/"GOLD_BOXES.json").read_bytes()),
             "parent_frozen_cohort_root":"ee202dd8427bae0648624518797506422304976a5af43bb8b8dce79600d208df",
             "model":"LOCAL_SKLEARN_LOGISTIC_BBOX_v1","weights_sha256":weights["model_sha256"],
             "training":"3 blank forms, 0 patient records, no gradient from evaluation images",
             "evaluation":"54 filled forms, 18 synthetic held-out patient IDs, same 3 layouts",
             "critical_limitation":"Same template layouts in train and eval; measures rendered-widget localization, not general OCR accuracy, EHR content accuracy, patient-specific model gain, or layout generalization.",
             "train_class_distribution":{"negative":len(trainY)-sum(trainY),"positive":sum(trainY)},
             "model_weights_changed_vs_control":"YES; fitted coefficient vector vs no learned coefficients",
             "n_train_images":len(blanks),"n_test_images":len(evals),"n_test_patients":len(by_patient),
             "n_field_boxes":total,"learned_box_recall":learned_hits/total,"baseline_box_recall":baseline_hits/total,
             "learned_false_positives":sum(r["trained_detector"]["false_positive"] for r in full),
             "baseline_false_positives":sum(r["control_contour_detector"]["false_positive"] for r in full),
             "learned_minus_baseline_recall":(learned_hits-baseline_hits)/total,
             "matched_discordants":{"baseline_only":minus,"learned_only":plus},
             "mcnemar_exact_two_sided":exact_mcnemar(minus,plus),
             "paired_patient_bootstrap_95_ci":np.quantile(differences,[.025,.975]).tolist(),
             "patient_cluster_bootstrap_reps":10000,"root_scheme":"sha256_domain_separated_json_sorted_compact_duplicate_last",
             "prediction_root":root(records),"score_only":"IoU>=0.5 bounding box vs DOM box",
             "model_answer_correctness":"NOT_TESTED",
             "OCR_readback":"NOT_TESTED",
             "live_video":"NOT_TESTED",
             "external_inference":"NONE",
             "promotion":"DISCOVERY_ONLY_NOT_INDEPENDENT_LAYOUT_REPLICATION",
             "library_versions":{"python":platform.python_version(),"opencv":cv2.__version__,
                                  "numpy":np.__version__,"sklearn":sklearn.__version__}}
    (out/"input_manifest.json").write_text(json.dumps({"schema":SCHEMA+".inputs",
            "license":"Apache-2.0 MITRE Synthea v3.4.0 synthetic",
            "images":input_pins,
            "source_label_json_sha256":summary["source_metadata_sha256"],
            "train_keys":[k for k,_ in blanks],
            "heldout_eval_patient_ids_sha256":[SHA(x.encode()) for x in sorted(by_patient)]},indent=2,sort_keys=True)+"\n")
    (out/"predictions.jsonl").write_bytes(b"".join(CANON(x)+b"\n" for x in pred_rows))
    (out/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:summary[k] for k in ("n_train_images","n_test_images","n_field_boxes",
        "learned_box_recall","baseline_box_recall","learned_false_positives","baseline_false_positives",
        "mcnemar_exact_two_sided","paired_patient_bootstrap_95_ci","weights_sha256","prediction_root")},indent=2))


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,default=OUT_DEFAULT)
    args=ap.parse_args()
    run(args.out)
