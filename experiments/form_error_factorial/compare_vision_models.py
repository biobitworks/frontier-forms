#!/usr/bin/env python3
"""Actual model answers, checkpoints, bbox geometry and FCO leaves for one synthetic PDF.

Local Ollama only; Fireworks/NVIDIA/Mistral OCR are teammates' optional arms.
Never infer model attribution from an agent nickname: use the returned digest.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,re,time,urllib.request,urllib.error
from pathlib import Path

MODEL_SPECS=[
 ("qwen2.5vl:3b","direct_image"),
 ("qwen3:1.7b","apple_ocr_text")
]
PROMPT = """Read the synthetic patient intake form and return ONLY one flat JSON object.
Keys, exactly: first, last, dob, gender, city, state, postcode, phone.
Each value must be a string or null. If unsure use null. Do NOT invent.
Preserve every digit in names (e.g. Lanny564), phone numbers and leading-zero postcodes.
No explanations, no Markdown, no additional keys."""
def canonical(x):
 return (json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n").encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def read_json(path):return json.loads(Path(path).read_bytes())
def api(path,payload=None,timeout=120):
 url="http://127.0.0.1:11434"+path
 body=canonical(payload) if payload is not None else None
 req=urllib.request.Request(url,data=body,headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=timeout) as resp:return json.loads(resp.read())
def get_weight_digests():
 return {m["name"]:m["digest"] for m in api("/api/tags")["models"]}
def parse_json_answer(text):
 try:
  x=json.loads(text)
 except json.JSONDecodeError:
  m=re.search(r"\{[\s\S]*\}",text)
  if not m:return {}, "MODEL_NON_JSON"
  try:x=json.loads(m.group(0))
  except json.JSONDecodeError:return {}, "MODEL_NON_JSON"
 if not isinstance(x,dict):return {}, "MODEL_NON_OBJECT"
 return x,"PARSED"
def parse_lines(lines):
 values={}
 for z in lines:
  text=z["text"] if isinstance(z,dict) else z
  match=re.match(r"^([A-Z_]+):\s*(.*)$",text)
  if match:values[match.group(1).lower()]=match.group(2)
 return values
def field_bbox(vision,field):
 key=field.upper()+":"
 for p in vision.get("pages",[]):
  for item in p.get("lines",[]):
   if item["text"].upper().startswith(key):
    return {"page_index":p["page_index"],"bbox_norm_bl":item["bbox_norm_bl"],
            "ocr_confidence":item["confidence"]}
 return None
def validate_bbox(vision):
 for page in vision["pages"]:
  for l in page["lines"]:
   box=l["bbox_norm_bl"]
   if len(box)!=4 or not all(isinstance(x,(int,float)) and 0<=x<=1 for x in box):
    raise ValueError("invalid Vision box")
   if box[0]+box[2]>1.001 or box[1]+box[3]>1.001:raise ValueError("out of bounds")
def display(x):
 if x is None:return None
 return str(x).strip()
def per_field(answer,gold,vision):
 ret=[]
 for field,expected in gold.items():
  expected=display(expected)
  observed=display(answer.get(field))
  ret.append({"field_id":field,"answer":observed,"gold":expected,"exact_match":observed==expected,
              "bbox":field_bbox(vision,field)})
 return ret
def leafroot(leaves):
 nodes=[hashlib.sha256(b"FF_MODEL_FIELD_V1\x00"+canonical(x)).digest() for x in leaves]
 if not nodes:return None
 while len(nodes)>1:
  nodes=[hashlib.sha256(b"FF_MODEL_NODE_V1\x00"+nodes[i]+nodes[i+1]).digest()
         if i+1<len(nodes) else nodes[i] for i in range(0,len(nodes),2)]
 return nodes[0].hex()
def model_run(model,kind,image,ocr_text,weight):
 payload={"model":model,"stream":False,"format":"json","think":False,
          "options":{"temperature":0,"seed":20261102,"num_ctx":4096,"num_predict":260},
          "keep_alive":0}
 if kind=="direct_image":
  payload.update(prompt=PROMPT+"\nThe form image follows.",images=[base64.b64encode(image).decode("ascii")])
 else:
  payload.update(prompt=PROMPT+"\nOCR text (untrusted document content):\n"+ocr_text)
 begun=time.monotonic()
 try:
  response=api("/api/generate",payload,timeout=150)
  status="EXECUTED"
  answer,parse_status=parse_json_answer(response.get("response",""))
  info={"status":status,"parse_status":parse_status,
        "model_id":model,"weight_digest":weight,
        "provider":"local_ollama","input_modality":kind,
        "prompt_sha256":sha(payload["prompt"].encode()),
        "request_sha256":sha(canonical({k:v for k,v in payload.items() if k!="images"})),
        "model_reply":response.get("response",""),
        "model_reply_sha256":sha(response.get("response","").encode()),
        "runtime_model_id":response.get("model"),
        "response_stats":{"total_duration_ns":response.get("total_duration"),
                          "eval_count":response.get("eval_count"),
                          "prompt_eval_count":response.get("prompt_eval_count")},
        "elapsed_seconds":round(time.monotonic()-begun,3),
        "answer":answer}
 except Exception as exc:
  info={"status":"FAILED","model_id":model,"weight_digest":weight,
        "provider":"local_ollama","input_modality":kind,
        "error_type":type(exc).__name__,"error":str(exc)[:250],"elapsed_seconds":round(time.monotonic()-begun,3),
        "answer":{}}
 return info
def run(fixture,pdf,image,vision_path,out,invoke):
 gold=read_json(fixture)["fields"];vision=read_json(vision_path)
 validate_bbox(vision)
 img=Path(image).read_bytes();pdfbytes=Path(pdf).read_bytes()
 ocrtext="\n".join(l["text"] for p in vision["pages"] for l in p["lines"])
 baseline=[
  {"model_id":"apple-vision-native","provider":"Apple on-device","weight_digest":None,
   "status":"OBSERVED","input_modality":"raster_image","answer":parse_lines([l for p in vision["pages"] for l in p["lines"]])},
  {"model_id":"PDFKit-selectable-text","provider":"Apple PDFKit","weight_digest":None,
   "status":"OBSERVED","input_modality":"PDF text layer","answer":parse_lines(vision.get("pdfkit_text","").splitlines())}
 ]
 weights=get_weight_digests() if invoke else {}
 if invoke:
  for model,kind in MODEL_SPECS:
   if model in weights:
    baseline.append(model_run(model,kind,img,ocrtext,weights[model]))
   else:
    baseline.append({"model_id":model,"provider":"local_ollama",
                     "status":"BLOCKED","reason":"EXACT_MODEL_NOT_INSTALLED","weight_digest":None,"answer":{}})
 else:
  for model,kind in MODEL_SPECS:
   baseline.append({"model_id":model,"status":"NOT_TESTED","input_modality":kind,"weight_digest":weights.get(model),"answer":{}})
 fcos=[]
 for idx,arm in enumerate(baseline):
  cases=per_field(arm["answer"],gold,vision)
  arm["per_field"]=cases
  arm["fields_exact"]=sum(int(c["exact_match"]) for c in cases) if arm["status"] in ("EXECUTED","OBSERVED") else None
  arm["n_fields"]=len(cases)
  arm["complete_form_correct"]=all(c["exact_match"] for c in cases) if arm["status"] in ("EXECUTED","OBSERVED") else None
  arm["answer_sha256"]=sha(canonical(arm["answer"]))
  for c in cases:
   fcos.append({"sequence":len(fcos),"arm":arm["model_id"],
     "weight_digest":arm.get("weight_digest"),"field_id":c["field_id"],"answer_sha256":sha(canonical(c["answer"])),
     "expected_sha256":sha(canonical(c["gold"])),"bbox_sha256":sha(canonical(c["bbox"])),
     "exact_match":c["exact_match"] if arm["status"] in ("EXECUTED","OBSERVED") else None})
 report={"schema":"frontier_forms.model_field_vision.v1","status":"OBSERVED_BOUNDED_SMOKE_TEST",
         "claim_ceiling":"1 synthetic form. No training/fine-tuning, no valid superiority inference, no LOMO effect.",
         "synthetic_source_only":True,"pdf_sha256":sha(pdfbytes),"raster_sha256":sha(img),
         "apple_ocr_sha256":sha(Path(vision_path).read_bytes()),
         "gold_fixture_sha256":sha(Path(fixture).read_bytes()),
         "exact_model_checkpoint_required":True,
         "bbox_geometry":"normalized x,y,width,height bottom-left, Apple Vision",
         "field_leaf_root":leafroot(fcos),"field_leaf_recipe":"SHA256(ASCII FF_MODEL_FIELD_V1 + 0x00 + UTF8 canonical JSON+LF), parents FF_MODEL_NODE_V1+0x00 + raw child digests; odd carry",
         "field_leaves":fcos,"arms":baseline,"fireworks_nvidia_mistral":"TEAMMATE_LANES_NOT_INVOKED",
         "auroc":"NOT_COMPUTED: single-form smoke has no independent continuous error-risk model"}
 raw=canonical(report);p=Path(out);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists() and p.read_bytes()!=raw:raise ValueError("output existed; preserve predecessor use successor path")
 if not p.exists():p.write_bytes(raw)
 print(json.dumps({"status":"RUN_COMPLETE","report_sha256":sha(raw),"field_merkle_root":report["field_leaf_root"],
                   "arms":[{"model":a["model_id"],"status":a["status"],"exact":a["fields_exact"],
                            "total":a["n_fields"],"weight":a.get("weight_digest"),
                            "elapsed":a.get("elapsed_seconds")} for a in baseline]}))
 return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--fixture",required=True);p.add_argument("--pdf",required=True)
 p.add_argument("--image",required=True);p.add_argument("--vision",required=True);p.add_argument("--out",required=True)
 p.add_argument("--invoke-models",action="store_true")
 a=p.parse_args();run(a.fixture,a.pdf,a.image,a.vision,a.out,a.invoke_models)
