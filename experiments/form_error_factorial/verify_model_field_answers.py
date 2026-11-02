#!/usr/bin/env python3
"""Independent offline verification of synthetic field-model answers and bbox receipts."""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path

def canon(x):return (json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n").encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def tree(leaves):
 nodes=[hashlib.sha256(b"FF_MODEL_FIELD_V1\x00"+canon(x)).digest() for x in leaves]
 if not nodes:raise ValueError("no leaves")
 while len(nodes)>1:
  nodes=[hashlib.sha256(b"FF_MODEL_NODE_V1\x00"+nodes[i]+nodes[i+1]).digest()
         if i+1<len(nodes) else nodes[i] for i in range(0,len(nodes),2)]
 return nodes[0].hex()
def verify(report_path,fixture_path,boxes_path,pdf_path,raster_path):
 report=json.loads(Path(report_path).read_bytes())
 gold=json.loads(Path(fixture_path).read_bytes())["fields"]
 assert report["schema"]=="frontier_forms.model_field_vision.v1"
 for f,expected in (("gold_fixture_sha256",fixture_path),("apple_ocr_sha256",boxes_path),
                    ("pdf_sha256",pdf_path),("raster_sha256",raster_path)):
  if report[f]!=sha(Path(expected).read_bytes()):raise ValueError("SOURCE_DRIFT:"+f)
 if tree(report["field_leaves"])!=report["field_leaf_root"]:raise ValueError("FIELD_TREE_MISMATCH")
 arms=report["arms"]
 if len({arm["model_id"] for arm in arms})!=len(arms):raise ValueError("DUPLICATE_MODEL")
 for arm in arms:
  if len(arm["per_field"])!=len(gold):raise ValueError("MISSING_FIELDS")
  if list(z["field_id"] for z in arm["per_field"])!=list(gold):raise ValueError("FIELD_ORDER")
  if sha(canon(arm["answer"]))!=arm["answer_sha256"]:raise ValueError("ANSWER_HASH")
  if arm["status"]=="EXECUTED":
   if not arm["weight_digest"] or len(arm["weight_digest"])!=64:raise ValueError("NO_WEIGHT_DIGEST")
   if arm["model_id"]!=arm["runtime_model_id"]:raise ValueError("MODEL_ID_DRIFT")
   if sha(arm["model_reply"].encode())!=arm["model_reply_sha256"]:raise ValueError("RAW_REPLY_HASH")
   if arm.get("elapsed_seconds") is None:raise ValueError("NO_LATENCY")
  for field in arm["per_field"]:
   f=field["field_id"]; gold_value=None if gold[f] is None else str(gold[f]).strip()
   actual=arm["answer"].get(f);actual=None if actual is None else str(actual).strip()
   if field["gold"]!=gold_value or field["answer"]!=actual or field["exact_match"]!=(gold_value==actual):
    raise ValueError("FIELD_MISMATCH:"+f)
   box=field.get("bbox")
   if box is not None:
    x,y,w,h=box["bbox_norm_bl"]
    if not (0<=x<=1 and 0<=y<=1 and 0<=w<=1 and 0<=h<=1 and x+w<=1.001 and y+h<=1.001):
     raise ValueError("BOUNDING_BOX_OUTSIDE_PAGE")
  if arm["status"] in ("EXECUTED","OBSERVED"):
   if sum(z["exact_match"] for z in arm["per_field"])!=arm["fields_exact"]:
    raise ValueError("CORRECT_FIELD_COUNT")
 return {"status":"PASS","model_arms":len(arms),"fields_per_arm":len(gold),
         "recorded_executed_models":sum(x["status"]=="EXECUTED" for x in arms),
         "field_leaf_root":report["field_leaf_root"],
         "report_sha256":sha(Path(report_path).read_bytes())}
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("root")
 a=p.parse_args();root=Path(a.root)
 print(json.dumps(verify(root/"model_field_answers.json",root/"fixture.json",root/"vision_boxes.json",
                         root/"synthetic_intake.pdf",root/"synthetic_intake.png"),sort_keys=True))
