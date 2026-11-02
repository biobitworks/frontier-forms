#!/usr/bin/env python3
"""On-device synthetic-form box classifier: 3-block factorial LOMO, tiny/small/medium.

Image pixels produce contour candidates; an actual scikit-learn RandomForest is fitted
to synthetic training renders (no training on test-patient screenshots).
Outputs public-safe JSON only. Native screenshots and pickle weights stay LOCAL.
"""
from __future__ import annotations
import argparse,collections,hashlib,itertools,json,math,os,pickle,random,time
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageEnhance,ImageFilter
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

SEED=20261102
SIZES={"tiny":10,"small":30,"medium":63}
BLOCKS={"geometry":(0,1),"shape":(2,3,4),"pixels":(5,6,7,8)}
FORM_ALLOW=("medication_allergy_intake_v1","new_patient_registration_v1")
def canonical(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def filehash(x):return sha(Path(x).read_bytes())
def iou(a,b):
 ix=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
 area=lambda z:max(0,z[2]-z[0])*max(0,z[3]-z[1])
 return ix/max(1,area(a)+area(b)-ix)
def candidates(rgb):
 """Pixel-derived, no DOM access: classify all large and small dark contour regions."""
 im=np.array(rgb.convert("RGB"))
 gray=cv2.cvtColor(im,cv2.COLOR_RGB2GRAY)
 mask=np.uint8(gray<212)*255
 contours,_=cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
 h,w=gray.shape
 boxes=[]
 for c in contours:
  x,y,bw,bh=cv2.boundingRect(c)
  if bw<11 or bh<9 or bw>w*.95 or bh>h*.65:continue
  b=(x,y,x+bw,y+bh)
  if any(iou(b,old)>.91 for old in boxes):continue
  boxes.append(b)
 boxes.sort(key=lambda b:(b[1],b[0],b[2],b[3]))
 return gray,boxes
def features(gray,b):
 h,w=gray.shape; x,y,x2,y2=b;bw=x2-x;bh=y2-y
 crop=gray[y:y2,x:x2]
 dark=float((crop<212).mean()) if crop.size else 0.
 if bh>4 and bw>4:
  inner=gray[y+2:y2-2,x+2:x2-2]
  inner_dark=float((inner<212).mean()) if inner.size else 0.
 else:inner_dark=0.
 edge=np.concatenate((crop[:1,:].ravel(),crop[-1:,:].ravel(),crop[:,0].ravel(),crop[:,-1].ravel()))
 border=float((edge<212).mean()) if edge.size else 0.
 return [x/w,y/h,bw/w,bh/h,bw/max(1,bh),dark,inner_dark,border,
         float(gray[max(0,y-8):y,:].mean())/255. if y>0 else 1.]
def render_augmented(blank_img,gold,patient,seed,facts=None):
 """Train on MITRE Synthea source values from train/validation patient IDs only.
 Test-split patient input and labels are never used to synthesize training images."""
 facts=facts or {}
 rng=random.Random(seed);base=Image.open(blank_img).convert("RGB")
 draw=ImageDraw.Draw(base)
 try:font=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf",13)
 except OSError:font=ImageFont.load_default()
 for f in gold["fields"]:
  x,y,x2,y2=f["bbox"]; key=f["field_key"]
  token=hashlib.sha256((patient+"|"+key).encode()).hexdigest()[:7].upper()
  fallback=("FAKE"+token[:3]+str(int(token[3:5],16)%100).zfill(2))
  value=str(facts.get(key) or fallback)
  draw.text((x+8,y+6),value[:55],font=font,fill=(45,48,54))
 # deterministic perturbation in pixels: do not mix identities across train/validation/test
 w,h=base.size; scale=rng.uniform(.965,1.035);dx=rng.randint(-8,8);dy=rng.randint(-10,10)
 sw,sh=round(w*scale),round(h*scale)
 base=base.resize((sw,sh),Image.Resampling.BICUBIC)
 canvas=Image.new("RGB",(w,h),(255,255,255));canvas.paste(base,(dx,dy))
 if rng.random()<.25:canvas=canvas.filter(ImageFilter.GaussianBlur(radius=.25))
 canvas=ImageEnhance.Contrast(canvas).enhance(rng.uniform(.92,1.08))
 gt=[]
 for f in gold["fields"]:
  x,y,x2,y2=f["bbox"]
  gt.append((max(0,round(x*scale)+dx),max(0,round(y*scale)+dy),
             min(w,round(x2*scale)+dx),min(h,round(y2*scale)+dy)))
 return canvas,gt
def examples(rgb,truth):
 gray,boxes=candidates(rgb)
 X=[features(gray,b) for b in boxes]
 Y=[int(max([iou(b,gt) for gt in truth],default=0)>=.78) for b in boxes]
 return boxes,X,Y
def match(proposals,gold,confidences=None,threshold=.50):
 """Greedy one-to-one IoU matching, independent of image labels during inference."""
 if confidences is None:confidences=[1.]*len(proposals)
 selected=[i for i,s in enumerate(confidences) if s>=threshold]
 possible=sorted(((iou(proposals[i],g),i,j) for i in selected for j,g in enumerate(gold)),reverse=True)
 used_p=set();used_g=set();paired=[]
 for score,i,j in possible:
  if score<.5:break
  if i not in used_p and j not in used_g:
   used_p.add(i);used_g.add(j);paired.append((i,j,score))
 return {"tp":len(paired),"fp":len(selected)-len(paired),"fn":len(gold)-len(paired),
         "all_fields_recovered":len(paired)==len(gold) and len(selected)==len(gold),
         "matched":paired,"selected":selected}
def exact_mcnemar(b,c):
 n=b+c
 return 1. if n==0 else min(1.,2*sum(math.comb(n,i) for i in range(min(b,c)+1))/2**n)
def patient_bootstrap(a,b,ids):
 """Paired bootstrap of patient-level form successes; retain all templates per patient."""
 patients=sorted(set(ids))
 inds=collections.defaultdict(list)
 for i,pid in enumerate(ids):inds[pid].append(i)
 rng=random.Random(SEED);vals=[]
 for _ in range(2000):
  idx=[i for _ in patients for i in inds[rng.choice(patients)]]
  vals.append(sum(int(b[i])-int(a[i]) for i in idx)/len(idx))
 vals.sort()
 return [vals[49],vals[1949]]
def effective_feats(mask):
 return tuple(i for block in mask for i in BLOCKS[block])
def fit_model(X,Y,mask):
 chosen=effective_feats(mask)
 if not chosen:raise ValueError("no features")
 xx=np.asarray(X,dtype="float32")[:,chosen]
 model=RandomForestClassifier(n_estimators=24,max_depth=10,min_samples_leaf=2,
                              n_jobs=1,random_state=SEED,class_weight="balanced_subsample")
 model.fit(xx,Y)
 return model
def labeled_sources(root):
 src=Path(root);g=json.loads((src/"GOLD_BOXES.json").read_bytes())
 return {k:v for k,v in g.items() if k.startswith("blank__")},        {k:v for k,v in g.items() if k.startswith("filled__")},g
def source_facts(manifest_path,patient_ids):
 """Read MITRE synthetic FHIR only for train/validation; verify occurrence SHA."""
 m=json.loads(Path(manifest_path).read_bytes());by_id={x["patient_id"]:x for x in m["members"]}
 out={};used=[]
 for pid in patient_ids:
  member=by_id[pid]
  path=Path(manifest_path).parent/member["subset_file"]
  raw=path.read_bytes()
  if sha(raw)!=member["subset_sha256"]:raise ValueError("FHIR_OCCURRENCE_HASH_FAIL")
  doc=json.loads(raw);patient=next(e["resource"] for e in doc["entry"] if e["resource"].get("resourceType")=="Patient")
  if patient.get("id")!=pid:raise ValueError("FHIR_PATIENT_ID_FAIL")
  name=(patient.get("name") or [{}])[0];addr=(patient.get("address") or [{}])[0]
  given=str((name.get("given") or [""])[0]);surname=str(name.get("family") or "")
  telecom=next((t.get("value") for t in patient.get("telecom",[]) if t.get("system")=="phone"),"")
  values={"full_name":given+" "+surname,"patient_name":given+" "+surname,
      "first":given,"surname":surname,"date_of_birth":patient.get("birthDate"),
      "dob":patient.get("birthDate"),"phone":telecom,"street":" ".join(addr.get("line") or []),
      "city":addr.get("city"),"state":addr.get("state"),"zip":addr.get("postalCode")}
  out[pid]=values;used.append({"patient_id":pid,"bundle_sha256":member["subset_sha256"]})
 return out,sha(canonical(used))
def run(args):
 root=Path(args.source);frozen=Path(args.cohort_manifest);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 manifest=json.loads(frozen.read_bytes());blank,filled,_=labeled_sources(root)
 train=sorted(x["patient_id"] for x in manifest["members"] if x["split"]=="train")
 val=sorted(x["patient_id"] for x in manifest["members"] if x["split"]=="validation")
 test=sorted(x["patient_id"] for x in manifest["members"] if x["split"]=="test")
 if len(train)!=63 or len(val)!=19 or len(test)!=18:raise ValueError("UNEXPECTED_SPLIT")
 size=SIZES[args.size];assigned_train=train[:size]
 fhir_facts,fhir_train_val_sha256=source_facts(frozen,assigned_train+val)
 X=[];Y=[];counts=collections.Counter()
 for pid in assigned_train:
  for template in FORM_ALLOW:
   k="blank__"+template;source=blank[k]
   rgb,boxes=render_augmented(root/source["image"],source,pid,SEED+int(sha((pid+template).encode())[:6],16),fhir_facts[pid])
   _,feats,labels=examples(rgb,boxes)
   X.extend(feats);Y.extend(labels);counts["synthetic_train_images"]+=1;counts["train_candidates"]+=len(feats)
 if len(set(Y))!=2:raise ValueError("NEED_TWO_CLASSES")
 # Validation patient images: same two templates, synthetic new patient text + transforms
 validation=[]
 for pid in val:
  for template in FORM_ALLOW:
   k="blank__"+template;source=blank[k]
   rgb,truth=render_augmented(root/source["image"],source,pid,SEED+int(sha((pid+template).encode())[:6],16),fhir_facts[pid])
   boxes,feats,labels=examples(rgb,truth)
   validation.append((pid,template,boxes,feats,truth,labels))
 # Browser-rendered TEST screenshots correspond only to the 18 test patient IDs.
 # Nothing from this list influences training or threshold selection.
 test_pages=[]
 for k,item in sorted(filled.items()):
  if item["patient_id"] not in test:raise ValueError("TEST_IMAGE_SPLIT_VIOLATION")
  rgb=Image.open(root/item["image"]).convert("RGB")
  gt=[tuple(f["bbox"]) for f in item["fields"]]
  box,feat,labels=examples(rgb,gt)
  test_pages.append((item["patient_id"],item["template_key"],item["image"],box,feat,gt,labels))
 results=[];pred_by_mask={}
 masks=[m for n in range(1,len(BLOCKS)+1) for m in itertools.combinations(BLOCKS,n)]
 def control_b0(boxes):return [int((b[2]-b[0])>=80 and (b[3]-b[1])>=15) for b in boxes]
 # Baseline is a deterministic contour heuristic, NOT the teammate's B0 form-filling arm.
 for mask in [()] + masks:
  name="CV_B0_contours" if not mask else "RF_"+ "+".join(mask)
  if mask:
   model=fit_model(X,Y,mask)
   # Threshold is selected on validation only; fixed grid, maximize macro F1, tie -> larger threshold.
   grid=(.35,.50,.65,.80,.90)
   ranks=[]
   for t in grid:
    gs=[match(boxes,truth,model.predict_proba(np.asarray(f,dtype="float32")[:,effective_feats(mask)])[:,list(model.classes_).index(1)],t)
        for _,_,boxes,f,truth,_ in validation]
    tp=sum(x["tp"] for x in gs);fp=sum(x["fp"] for x in gs);fn=sum(x["fn"] for x in gs)
    ranks.append((2*tp/max(1,2*tp+fp+fn),t))
   cutoff=max(ranks)[1]
   weights=pickle.dumps({"mask":mask,"model":model,"features":effective_feats(mask)},protocol=4)
   ckpt=out/(name.replace("+","_")+".pkl")
   if ckpt.exists() and ckpt.read_bytes()!=weights:raise ValueError("CHECKPOINT_DRIFT")
   if not ckpt.exists():ckpt.write_bytes(weights)
   ck_hash=filehash(ckpt)
   importances={str(i):round(float(v),7) for i,v in zip(effective_feats(mask),model.feature_importances_)}
  else:
   cutoff=.5;ck_hash=None;importances={}
  page_rows=[];candidate_y=[];candidate_probs=[]
  for patient,template,image,boxes,features_,gt,labels in test_pages:
   if mask:
    probabilities=model.predict_proba(np.asarray(features_,dtype="float32")[:,effective_feats(mask)])[:,list(model.classes_).index(1)].tolist()
   else:probabilities=control_b0(boxes)
   stats=match(boxes,gt,probabilities,cutoff)
   candidate_y.extend(labels);candidate_probs.extend(probabilities)
   page_rows.append({"patient_id":patient,"template":template,"image_sha256":filehash(root/image),
      "n_gold":len(gt),"tp":stats["tp"],"fp":stats["fp"],"fn":stats["fn"],
      "full_page_success":stats["all_fields_recovered"],
      "predicted":[{"bbox":[int(x) for x in boxes[i]],"score":round(float(probabilities[i]),7)}
                   for i in stats["selected"]],
      "gold_scoring_sha256":sha(canonical(gt))})
  tp=sum(x["tp"] for x in page_rows);fp=sum(x["fp"] for x in page_rows);fn=sum(x["fn"] for x in page_rows)
  auc=roc_auc_score(candidate_y,candidate_probs) if len(set(candidate_y))==2 and len(set(candidate_probs))>1 else None
  result={"arm":name,"modules":list(mask),"checkpoint_sha256":ck_hash,"weight_feature_importance":importances,
     "threshold_selected_on_validation":cutoff,"n_train_patients":len(assigned_train),
     "n_validation_patients":len(val),"n_test_patients":len(test),"n_test_images":len(page_rows),
     "test_tp":tp,"test_fp":fp,"test_fn":fn,"precision":tp/max(1,tp+fp),"recall":tp/max(1,tp+fn),
     "f1":2*tp/max(1,2*tp+fp+fn),"candidate_auroc":auc,
     "full_page_successes":sum(x["full_page_success"] for x in page_rows),
     "pages":page_rows}
  results.append(result);pred_by_mask[name]=[x["full_page_success"] for x in page_rows]
 baseline=pred_by_mask["CV_B0_contours"];ids=[x[0] for x in test_pages]
 for arm in results:
  alt=pred_by_mask[arm["arm"]];lost=sum(a and not b for a,b in zip(baseline,alt))
  gained=sum(not a and b for a,b in zip(baseline,alt))
  arm["paired_vs_cv_b0"]={"baseline_only":lost,"challenger_only":gained,
    "delta_full_page":(gained-lost)/len(baseline),"mcnemar_exact_descriptive":exact_mcnemar(lost,gained),
    "patient_cluster_bootstrap95":patient_bootstrap(baseline,alt,ids),
    "warning":"Exact McNemar treats 3 pages per test patient as independent; patient-cluster CI is primary"}
 fco=[{"index":i,"arm":a["arm"],"weight_sha256":a["checkpoint_sha256"],
       "result_sha256":sha(canonical(a["pages"])),
       "n_images":a["n_test_images"]} for i,a in enumerate(results)]
 def tree(leaves):
  z=[hashlib.sha256(b"FF_VISION_LEAF_V1\x00"+canonical(x)).digest() for x in leaves]
  while len(z)>1:
   z=[hashlib.sha256(b"FF_VISION_NODE_V1\x00"+z[i]+z[i+1]).digest() if i+1<len(z) else z[i] for i in range(0,len(z),2)]
  return z[0].hex()
 report={"schema":"frontier_forms.local_vision_validator.v1","scale":args.size,
  "scope":"LOCAL_ONLY_RANDOM_FOREST_CLASSIFIER_ON_RENDERED_SYNTHETIC_FORM_IMAGES",
  "claim_ceiling":"EXPLORATORY: trained on actual synthetic MITRE Synthea patient FHIR demographics/contact values rendered into blank intake forms, with deterministic augmentations. Test forms share template geometry and were previously inspected. No clinical-field accuracy or LLM fine-tuning claim.",
  "source_manifest_sha256":filehash(frozen),"source_gold_boxes_sha256":filehash(root/"GOLD_BOXES.json"),
  "trainer_code_sha256":filehash(__file__),
  "train_validation_source_occurrences_sha256":fhir_train_val_sha256,
  "source_text_scope":"real MITRE Synthea synthetic FHIR name/DOB/contact fields, only train and validation",
  "n_train_patient":len(assigned_train),"n_train_examples":len(X),
  "n_test_patient":len(test),"n_test_images":len(test_pages),"n_validation_patient":len(val),
  "dataset_split_membership":{"train":assigned_train,"validation":val,"test":test},
  "modules":list(BLOCKS),"seed":SEED,"feature_map":BLOCKS,
  "trained_model":"sklearn.RandomForestClassifier 24 trees max_depth=10 min_samples_leaf=2",
  "loss":"binary candidate box classification; DOM boxes only used to train synthetic transform/score test",
  "no_external_calls":True,"no_new_png_or_weights_pushed":True,
  "merkle_recipe":"leaf=SHA256(FF_VISION_LEAF_V1+NUL+canonical UTF8 JSON); node=SHA256(FF_VISION_NODE_V1+NUL+left raw digest+right raw digest); odd carry",
  "fco_leaves":fco,"fco_merkle_root":tree(fco),"results":results}
 path=out/"run_report.json";tmp=canonical(report)
 if path.exists() and path.read_bytes()!=tmp:raise ValueError("IMMUTABLE_REPORT_CONFLICT")
 if not path.exists():path.write_bytes(tmp)
 # Public-safe JSON projection excludes patient-level exact IDs and any raw images/weights.
 public={k:v for k,v in report.items() if k not in ("dataset_split_membership","results")}
 public["results"]=[{k:v for k,v in a.items() if k!="pages"} for a in results]
 public["public_source"]={"test_page_image_hashes":sorted({x["image_sha256"] for a in results for x in a["pages"]})}
 public["model_weight_files"]="LOCAL_ONLY; checkpoint SHA-256 in each result"
 public["report_local_sha256"]=sha(tmp)
 return public
def main():
 p=argparse.ArgumentParser();p.add_argument("--source",required=True)
 p.add_argument("--cohort-manifest",required=True);p.add_argument("--out",required=True)
 p.add_argument("--size",choices=tuple(SIZES),default="tiny")
 args=p.parse_args();result=run(args);dst=Path(args.out)/"public_report.json";raw=canonical(result)
 if dst.exists() and dst.read_bytes()!=raw:raise ValueError("PUBLIC_IMMUTABLE_COLLISION")
 if not dst.exists():dst.write_bytes(raw)
 full=next(x for x in result["results"] if x["arm"]=="RF_geometry+shape+pixels")
 print(json.dumps({"status":"EXECUTED","size":args.size,"training_patients":result["n_train_patient"],
   "test_patients":result["n_test_patient"],"test_images":result["n_test_images"],
   "model_checkpoint_sha256":full["checkpoint_sha256"],"selected_model_f1":full["f1"],
   "baseline_f1":result["results"][0]["f1"],"model_AUROC":full["candidate_auroc"],
   "fco_merkle_root":result["fco_merkle_root"],"public_json_sha256":sha(raw)}),flush=True)
if __name__=="__main__":main()
