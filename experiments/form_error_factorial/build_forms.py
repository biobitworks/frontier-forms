#!/usr/bin/env python3
"""Prebuilt synthetic HTML form-error set from a declared frozen challenge report."""
import argparse,hashlib,html,json
from pathlib import Path
def canon(x):return (json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))+"\n").encode()
def hashb(x):return hashlib.sha256(x).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("cases");p.add_argument("out");p.add_argument("--per-attack",type=int,default=3);args=p.parse_args()
 src=json.loads(Path(args.cases).read_bytes());out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 chosen={};manifest=[]
 for idx,c in enumerate(src):
  attack=c["attack"];seen=chosen.get(attack,0)
  if seen>=args.per_attack:continue
  chosen[attack]=seen+1
  key=c["field"];value=c["observed"];pid=c["patient_id"]
  body="<html lang='en'><head><meta charset='utf-8'><title>Synthetic intake form</title></head><body>\n"
  body+="<h1>FHIR intake (synthetic)</h1><p>Test record only. No Epic submission.</p>\n"
  body+="<form><fieldset><legend>Patient intake</legend>\n"
  body+="<label for='field'>"+html.escape(key)+"</label><input id='field' name='"+html.escape(key,quote=True)+"' value='"+html.escape(value,quote=True)+"' readonly>\n"
  body+="<input type='hidden' name='source_patient_id' value='"+html.escape(pid,quote=True)+"'></fieldset></form></body></html>\n"
  b=body.encode("utf-8");fname=f"fixture_{len(manifest)+1:02d}.html";f=out/fname
  if f.exists() and f.read_bytes()!=b:raise ValueError("immutable form mismatch")
  if not f.exists():f.write_bytes(b)
  manifest.append({"file":fname,"attack":attack,"case_id":hashb(canon(c)),
      "source_sha256":c["source_sha256"],"form_sha256":hashb(b),
      "patient_id":pid,"field":key,"truth_not_embedded":True})
 m={"schema":"frontier_forms.synthetic_forms.v1","source_challenge_sha256":hashb(Path(args.cases).read_bytes()),"templates":manifest,
    "scope":"Synthetic-only prebuilt injected forms; controlled fault type hidden from HTML. No model training claims."}
 raw=canon(m);mf=out/"MANIFEST.json"
 if mf.exists() and mf.read_bytes()!=raw:raise ValueError("manifest mismatch")
 if not mf.exists():mf.write_bytes(raw)
 print(json.dumps({"forms":len(manifest),"by_type":chosen,"manifest_sha256":hashb(raw)}))
if __name__=="__main__":main()
