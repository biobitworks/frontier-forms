#!/usr/bin/env python3
"""Independent, stdlib-only audit of local bbox training receipts.

Recomputes exact SHA256 of local (non-published) pixels, trained weights and
predictions; independently scores test boxes from synthetic DOM gold; checks
seed-keyed patient-disjoint holdout. Does not infer causality from hashes.
"""
import argparse
import hashlib
import json
from pathlib import Path

def hashfile(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def iou(a,b):
    l=max(a[0],b[0]);t=max(a[1],b[1]);r=min(a[2],b[2]);bot=min(a[3],b[3])
    inter=max(0,r-l)*max(0,bot-t)
    area_a=max(0,a[2]-a[0])*max(0,a[3]-a[1])
    area_b=max(0,b[2]-b[0])*max(0,b[3]-b[1])
    return inter/max(1,area_a+area_b-inter)

def score(truth,pred):
    edges=sorted(((iou(a,b),i,j) for i,a in enumerate(truth) for j,b in enumerate(pred)),reverse=True)
    taken_truth=set();taken_pred=set();matched=[]
    for overlap,i,j in edges:
        if overlap>=.5 and i not in taken_truth and j not in taken_pred:
            taken_truth.add(i);taken_pred.add(j);matched.append(overlap)
    return len(matched),len(pred)-len(matched),len(truth)-len(matched),matched

def audit(data_dir,run):
    goldpath=data_dir/"GOLD_BOXES.json"
    gold=json.loads(goldpath.read_text())
    receipt=json.loads((run/"TRAIN_RECEIPT.json").read_text())
    expected_gold=receipt.get("data_gold_sha256",receipt.get("dataset_gold_sha256"))
    assert hashfile(goldpath)==expected_gold, "GOLD_SHA256_MISMATCH"
    assert hashfile(run/"predictions.jsonl")==receipt["predictions_sha256"], "PREDICTIONS_SHA256_MISMATCH"
    weights=next(p for p in (run/"candidate_classifier_state.pt",run/"bbox_detector_state.pt") if p.exists())
    assert hashfile(weights)==receipt["weights_sha256"], "WEIGHTS_SHA256_MISMATCH"
    for key,s in receipt.get("training_image_sha256",receipt.get("train_image_sha256",{})).items():
        assert gold[key]["patient_id"] is None,"PATIENT_IMAGE_IN_TRAINING"
        assert hashfile(data_dir/gold[key]["image"])==s,"TRAIN_PIXEL_SHA256_MISMATCH"
    all_patients={g["patient_id"] for g in gold.values() if g["patient_id"]}
    seed=receipt.get("seed",receipt.get("hyperparameters",{}).get("seed"))
    ordered=sorted(all_patients,key=lambda p: hashlib.sha256((str(seed)+p).encode()).hexdigest())
    val=set(ordered[:6]);test=set(ordered[6:])
    assert val and test and val.isdisjoint(test)
    expected_keys={k for k,g in gold.items() if g["patient_id"] in test}
    rows=[json.loads(s) for s in (run/"predictions.jsonl").read_text().splitlines() if s.strip()]
    assert len(rows)==len(expected_keys) and {r["image_id"] for r in rows}==expected_keys,"TEST_SPLIT_MISMATCH"
    tp=fp=fn=0;ious=[]
    for row in rows:
        key=row["image_id"];g=gold[key]
        assert row["image_sha256"]==hashfile(data_dir/g["image"]),"TEST_PIXEL_MISMATCH"
        truth=[x["bbox"] for x in g["fields"]]
        preds=[x["bbox"] for x in row["predictions"]]
        this_tp,this_fp,this_fn,matched=score(truth,preds)
        if "score" in row:
            assert (this_tp,this_fp,this_fn)==tuple(row["score"][v] for v in ("tp","fp","fn")),"ROW_SCORE_MISMATCH"
        tp+=this_tp;fp+=this_fp;fn+=this_fn;ious+=matched
    prior=receipt["test"]
    assert (tp,fp,fn)==(prior["tp"],prior["fp"],prior["fn"]),"AGGREGATE_SCORE_MISMATCH"
    precision=tp/max(1,tp+fp); recall=tp/max(1,tp+fn)
    f1=2*precision*recall/max(.0000001,precision+recall)
    assert abs(f1-prior["f1_iou50"])<1e-4,"F1_MISMATCH"
    return {"status":"PASS","model_weights_sha256":receipt["weights_sha256"],
            "gold_sha256":hashfile(goldpath),"predictions_sha256":hashfile(run/"predictions.jsonl"),
            "test_images":len(rows),"train_patient_count":0,"validation_patients":len(val),
            "test_patients":len(test),"metrics":{"tp":tp,"fp":fp,"fn":fn,
            "precision_iou50":round(precision,5),"recall_iou50":round(recall,5),
            "f1_iou50":round(f1,5),"mean_iou_matched":round(sum(ious)/len(ious),5) if ious else None},
            "identity_vs_truth":"Hashes attest identity only; controlled DOM synthetic metrics do not establish clinical utility",
            "new_template_generalization":"NOT_TESTED"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="data/forms_vision_v1")
    p.add_argument("--run",required=True)
    a=p.parse_args()
    print(json.dumps(audit(Path(a.data),Path(a.run)),sort_keys=True,indent=2))
if __name__=="__main__":main()
