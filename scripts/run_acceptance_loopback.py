#!/usr/bin/env python3
"""One LOCAL acceptance chain: synthetic FHIR -> browser -> field plan -> PDF -> vision.

Models are never hosted. The synthetic data are distinct from Epic sandbox records.
The route /fhir/R4 is read-only. No externally supplied URL is accepted.
PDFs, browser captures, and raw model prompts remain in an untracked local run dir.

Example:
  PYTHONPATH=src /opt/anaconda3/bin/python scripts/run_acceptance_loopback.py \
    --arm b0 --limit 100 --render-limit 3 --out runs/acceptance_b0
  PYTHONPATH=src /opt/anaconda3/bin/python scripts/run_acceptance_loopback.py \
    --arm qwen --model qwen2.5:0.5b --limit 1 --render-limit 1 \
    --out runs/acceptance_qwen
"""
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from frontier_forms.forms import b0, sft_data
from frontier_forms.forms.cohort import load_cohort, sha256_file
from frontier_forms.forms.harness import _http, score_field
from frontier_forms.forms.oracle import gold_answers
from frontier_forms.forms.server import FormState, serve
from frontier_forms.forms.templates import load_templates

def digest(b):
    return hashlib.sha256(b).hexdigest()

def canonical(x):
    return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()

def normalized(s):
    return re.sub(r"\s+"," ",str(s or "")).strip().casefold()

def safe_filename(s):
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+",s):
        raise ValueError("INVALID_OUTPUT_NAME")
    return s

def model_meta(name):
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags",timeout=10) as r:
        tags=json.load(r)
    entries=[v for v in tags["models"] if v.get("name")==name or v.get("model")==name]
    if len(entries)!=1 or not entries[0].get("digest"):
        raise RuntimeError("LOCAL_MODEL_DIGEST_UNAVAILABLE")
    return {"runtime":"local-ollama","name":name,"digest":entries[0]["digest"]}

def model_answer(name,prompt,seed):
    body={"model":name,"prompt":prompt,"stream":False,"think":False,
          "options":{"temperature":0,"seed":seed,"num_predict":192}}
    req=urllib.request.Request("http://127.0.0.1:11434/api/generate",
              data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=300) as r:
        x=json.load(r)
    return x.get("response","")

CSS="""body{font:15px Helvetica,Arial,sans-serif;margin:24px;width:820px}
.row{margin:9px 0;break-inside:avoid}
label{display:block;margin-bottom:3px}
input,select{width:600px;min-height:29px;font:14px Helvetica}
textarea{width:600px;height:64px;font:13px Helvetica}
.banner{font-size:12px}
.printed-value{display:none}
@media print{
  input,textarea,select,button{display:none!important}
  .printed-value{display:block;white-space:pre-wrap;overflow-wrap:anywhere;
    min-height:22px;min-width:560px;border:1px solid #999;padding:5px;font:14px Helvetica}
  body{width:auto}
}"""

def prepare_print_page(page,answers,template):
    """Use the same form DOM for browser and printed PDF, no separately mapped values."""
    vals={a["field_key"]:str(a["value"] if a.get("value") is not None else "")
          for a in answers if a["decision"]=="fill"}
    page.add_style_tag(content=CSS)
    # Untrusted patient-like strings passed as browser data, not HTML.
    for f in template["fields"]:
        k=f["field_key"]
        loc=page.locator('[name="'+k+'"]')
        if k not in vals:
            continue
        if f["type"]=="select":
            try:
                loc.select_option(value=vals[k])
            except Exception:
                # Report the mismatch; do not silently force a different dropdown.
                pass
        else:
            loc.fill(vals[k])
    page.evaluate("""() => {
      for(const el of document.querySelectorAll('input,textarea,select')){
        let sp=document.createElement('span');
        sp.className='printed-value';
        sp.textContent=el.value || '[NEEDS USER INPUT]';
        el.insertAdjacentElement('afterend',sp);
      }
    }""")
    dom=[]
    for f in template["fields"]:
        k=f["field_key"]
        item=page.locator('[name="'+k+'"]')
        bbox=item.bounding_box()
        val=item.input_value()
        dom.append({"field_key":k,"label":f["label"],"value":val,
                    "bbox_pixel":([round(bbox["x"],2),round(bbox["y"],2),
                       round(bbox["x"]+bbox["width"],2),round(bbox["y"]+bbox["height"],2)]
                       if bbox else None)})
    return dom

def render_case(browser,base,template,patient_id,answers,pdf_path,vision_tool=None):
    import fitz
    page=browser.new_page(viewport={"width":900,"height":1100},device_scale_factor=1)
    try:
        page.goto(base+"/preview/forms/"+template["template_key"],wait_until="domcontentloaded")
        dom=prepare_print_page(page,answers,template)
        pdf=page.pdf(format="Letter",print_background=True,
                     margin={"top":"0.35in","right":"0.35in","bottom":"0.35in","left":"0.35in"})
        pdf_path.write_bytes(pdf)
        with fitz.open(stream=pdf,filetype="pdf") as doc:
            pdf_pages=doc.page_count
            pdf_text=" ".join(p.get_text() for p in doc)
        seen={d["field_key"]:d["value"] for d in dom}
        filled=[a for a in answers if a["decision"]=="fill" and a.get("value") not in (None,"")]
        html_mismatches=[a["field_key"] for a in filled if
             normalized(seen.get(a["field_key"]))!=normalized(a["value"])]
        # Note: PDF text extraction is NOT a geometric, per-field OCR alignment.
        missing_pdf=[a["field_key"] for a in filled if
                     normalized(a["value"]) not in normalized(pdf_text)]
        vision={"state":"NOT_TESTED"}
        if vision_tool:
            import subprocess
            vpath=pdf_path.with_suffix(".vision.json")
            subprocess.run([vision_tool,str(pdf_path),str(vpath)],check=True,
                           capture_output=True,text=True,timeout=180)
            raw=json.loads(vpath.read_text())
            recognized=" ".join(line.get("text","") for p in raw["pages"]
                                     for line in p.get("lines",[]))
            missing_ocr=[a["field_key"] for a in filled
                             if normalized(a["value"]) not in normalized(recognized)]
            vision={"state":"EXECUTED","engine":raw["engine"],"page_count":len(raw["pages"]),
                    "line_count":sum(len(p.get("lines",[])) for p in raw["pages"]),
                    "pdfkit_text_sha256":digest(raw.get("pdfkit_text","").encode()),
                    "ocr_missing_whole_value_fields":missing_ocr,
                    "bbox_lines_with_coordinates":sum(len(p.get("lines",[])) for p in raw["pages"]),
                    "box_to_form_field_alignment":"NOT_TESTED"}
        return {"pdf_sha256":digest(pdf),"pdf_pages":pdf_pages,
                "html_field_count":len(dom),"pdf_text_sha256":digest(pdf_text.encode()),
                "dom_answers":dom,"html_value_mismatches":html_mismatches,
                "pdf_text_missing_whole_value_fields":missing_pdf,
                "vision":vision}
    finally:
        page.close()

def run(args):
    if args.arm=="qwen" and not args.model:
        raise ValueError("QWEN_REQUIRES_MODEL")
    if args.limit<1 or args.limit>100 or args.render_limit<0:
        raise ValueError("INVALID_LIMIT")
    if args.render_limit>args.limit*3:
        raise ValueError("RENDER_LIMIT_EXCEEDS_MAX_CASES")
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    members,bundles=load_cohort(ROOT/"data/forms_cohort_v1/bundles",limit=args.limit)
    if len(members)!=args.limit:
        raise RuntimeError("COHORT_COUNT_MISMATCH")
    templates=load_templates()
    base_meta=model_meta(args.model) if args.arm=="qwen" else {"runtime":"rules","name":"B0","digest":None}
    state=FormState(members,bundles,templates)
    httpd=serve(state,host="127.0.0.1",port=0)
    base="http://127.0.0.1:"+str(httpd.server_address[1])
    browser=None
    t0=time.monotonic()
    rows=[]
    raw_model=[]
    rendered=0
    try:
        assert _http(base,"/healthz")["synthetic_only"]
        assert _http(base,"/forms")==sorted(templates)
        # Read-only synthetic FHIR is part of acceptance, not a live Epic call.
        assert _http(base,"/fhir/R4/metadata")["fhirVersion"]=="4.0.1"
        for m in members:
            passport=_http(base,"/api/passport/"+m.patient_id)
            assert passport["patient_id"]
            assert _http(base,"/fhir/R4/Patient/"+m.patient_id)["resourceType"]=="Patient"
            for key,t in sorted(templates.items()):
                if m.split not in t["splits"]:
                    continue
                html=_http(base,"/forms/"+key)
                fields=b0.inspect_form(html)
                assert len(fields)==len(t["fields"])
                if args.arm=="b0":
                    answers=b0.fill_plan(html,passport)["answers"]
                else:
                    answers=[]
                    text=sft_data.passport_text(passport)
                    for f in fields:
                        item={"label":f["label"],"type":f["type"] if f["type"] in ("textarea","select","number") else "text",
                              "options":f["options"]}
                        prompt=sft_data.prompt(item,text)
                        response=model_answer(args.model,prompt,args.seed)
                        decision,value=sft_data.parse_completion(response)
                        answers.append({"field_key":f["name"],"decision":decision,
                          "value":value,"evidence_fact_ids":[],"reason":args.arm})
                        raw_model.append({"case_key":m.patient_id+"|"+key,
                          "field_key":f["name"],"model_digest":base_meta["digest"],
                          "prompt_sha256":digest(prompt.encode()),"response_sha256":digest(response.encode()),
                          "raw_response":response,"decision":decision,"value":value})
                echo=_http(base,"/forms/"+key+"/submit",
                           {"patient_id":m.patient_id,"answers":answers})
                assert echo.get("accepted") is True
                expected=gold_answers(bundles[m.patient_id],t)
                pred={a["field_key"]:a for a in answers}
                result={k:score_field(g,pred.get(k)) for k,g in sorted(expected.items())}
                record={"case_key":m.patient_id+"|"+key,"patient_id":m.patient_id,
                        "source_bundle_sha256":sha256_file(m.path),
                        "split":m.split,"template_key":key,"model":base_meta,
                        "model_field_answers":[{"field_key":a["field_key"],"decision":a["decision"],
                                                "value":a["value"]} for a in answers],
                        "per_field":result,
                        "field_correct":sum(x["correct"] for x in result.values()),
                        "field_total":len(result),
                        "server_echo":echo["answers"]==sorted(answers,key=lambda x:x["field_key"]),
                        "render_state":"NOT_TESTED"}
                if rendered<args.render_limit:
                    if browser is None:
                        from playwright.sync_api import sync_playwright
                        pw=sync_playwright().start()
                        chrome=Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
                        browser=pw.chromium.launch(headless=True,**({"executable_path":str(chrome)} if chrome.is_file() else {}))
                    path=out/"pdf"
                    path.mkdir(exist_ok=True)
                    filename=safe_filename("case_%03d_%s" % (rendered,key))
                    artifact=render_case(browser,base,t,m.patient_id,answers,
                                         path/(filename+".pdf"),args.vision_tool)
                    record["render_state"]="EXECUTED"
                    record["render"]={k:v for k,v in artifact.items() if k!="dom_answers"}
                    record["bbox_dom"]=artifact["dom_answers"]
                    rendered+=1
                rows.append(record)
                if len(rows)%25==0:
                    print("PROGRESS",json.dumps({"cases":len(rows),"patients_so_far":len({r["patient_id"] for r in rows}),
                                                 "pdf_rendered":rendered}),flush=True)
    finally:
        if browser:
            browser.close()
            pw.stop()
        httpd.shutdown()
        httpd.server_close()
    # Local per-field answers and raw model data are not uploaded.
    (out/"case_evidence.json").write_bytes(canonical(rows))
    if raw_model:
        (out/"model_raw_answers.json").write_bytes(canonical(raw_model))
    total=sum(r["field_total"] for r in rows)
    correct=sum(r["field_correct"] for r in rows)
    all_render=[r for r in rows if r["render_state"]=="EXECUTED"]
    failures={
       "server_echo":sum(not r["server_echo"] for r in rows),
       "html_value":sum(len(r["render"]["html_value_mismatches"]) for r in all_render),
       "pdf_text":sum(len(r["render"]["pdf_text_missing_whole_value_fields"]) for r in all_render),
       "vision_ocr_text":sum(len(r["render"]["vision"].get("ocr_missing_whole_value_fields",[])) for r in all_render),
    }
    report={"schema":"frontier-forms-acceptance-v1","state":"EXECUTED",
            "patient_count":len(members),"patient_unique":len({m.patient_id for m in members}),
            "case_count":len(rows),"field_count":total,"field_correct":correct,
            "field_accuracy":round(correct/total,6) if total else None,
            "split_counts":{s:sum(m.split==s for m in members) for s in ("train","validation","test")},
            "template_keys":sorted(templates),"rendered_pdf_cases":len(all_render),
            "vision_executed_cases":sum(r["render"]["vision"]["state"]=="EXECUTED" for r in all_render),
            "failures":failures,"model":base_meta,"cohort":"MITRE Synthea synthetic subset, not Epic sandbox",
            "open_epic_form_fidelity":"NOT_TESTED",
            "new_template_generalization":"NOT_TESTED",
            "pdf_bbox_field_alignment":"NOT_TESTED",
            "model_weights_updated":"NO",
            "hosted_inference":"NONE","data_publication":"LOCAL_OUTPUT_ONLY",
            "case_evidence_sha256":sha256_file(out/"case_evidence.json"),
            "model_raw_answers_sha256":sha256_file(out/"model_raw_answers.json") if raw_model else None,
            "elapsed_seconds":round(time.monotonic()-t0,2)}
    (out/"ACCEPTANCE_SUMMARY.json").write_bytes(canonical(report))
    print("COMPLETE",json.dumps(report),flush=True)
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--arm",choices=["b0","qwen"],default="b0")
    parser.add_argument("--model",default=None)
    parser.add_argument("--limit",type=int,default=100)
    parser.add_argument("--render-limit",type=int,default=3)
    parser.add_argument("--seed",type=int,default=20261102)
    parser.add_argument("--vision-tool",default=None)
    parser.add_argument("--out",required=True)
    run(parser.parse_args())
