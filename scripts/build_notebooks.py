#!/usr/bin/env python3
"""Deterministically generate Jupyter experiment notebooks from pinned cell sources."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def notebook(name,requirements,code):
    blocks=[
      dict(cell_type='markdown',metadata={},source=[
        '# '+name+'\n','\n','## REQUIREMENTS\n',
        requirements+'\n','\n','## INPUT → ANALYSIS → OUTPUT\n',
        'Do not interpret toy fixtures as held-out model evidence.\n']),
      dict(cell_type='code',execution_count=None,metadata={},outputs=[],source=code.splitlines(True))]
    return (ROOT/'notebooks'/(name+'.ipynb'),
      json.dumps({'cells':blocks,'metadata':{'kernelspec':{'display_name':'Python 3',
      'language':'python','name':'python3'},'language_info':{'name':'python'}},
      'nbformat':4,'nbformat_minor':5},ensure_ascii=False,indent=1)+'\n')
BOOKS=[]
BOOKS.append(notebook('01_custody_merkle',
  'Verify ordered-leaf SHA-256 construction, then verify original source bytes only if FCO_SOURCE_ROOT points to authorized workspace. Expected project root is a locator, not authorization to export.',
  """import os, sys, json
from pathlib import Path
r=Path.cwd().resolve()
if r.name=='notebooks': r=r.parent
sys.path.insert(0,str(r/'scripts'))
from verify_freeze import canonical,root,verify
fixture=[{'path':'a','sha256':'01'},{'path':'b','sha256':'02'}]
assert root(fixture)==root(fixture)
p=os.environ.get('FCO_SOURCE_ROOT')
out=verify(p,True) if p else {'state':'NOT_TESTED_PRIVATE_INPUT_ABSENT','fixture_test':'PASS'}
print(json.dumps(out,sort_keys=True))"""))
BOOKS.append(notebook('02_paired_mcnemar_bootstrap',
  'Compare paired predictions on exact same case keys and frozen answer oracle. Discovery predecessor is NEGATIVE, not evidence of improvement; real files require explicit FCO_SOURCE_ROOT.',
  """import os,sys,json
from pathlib import Path
r=Path.cwd().resolve()
if r.name=='notebooks':r=r.parent
sys.path.insert(0,str(r/'scripts'))
from paired_stats import exact_mcnemar,paired_bootstrap,analyze
assert exact_mcnemar(2,4)==0.6875
base=os.environ.get('FCO_SOURCE_ROOT')
if base:
    b=Path(base)/'eval/lb_mini_discovery_lfm2-1.2b-longevity-q4km_latest.jsonl'
    c=Path(base)/'eval/insilico_qwen3_06b_discovery_attempt3.jsonl'
    x=analyze(b,c)
    print(json.dumps({'scope':'DISCOVERY_ONLY',**x},sort_keys=True))
else:
    print(json.dumps({'scope':'SYNTHETIC_MCNEMAR_CHECK','p':exact_mcnemar(2,4),
      'real_paired_run':'NOT_TESTED_INPUT_ABSENT'}))"""))
BOOKS.append(notebook('03_lomo_auc_fpr_fdr',
  'Declare modules and frozen input set before leaving one out. LOMO training/evaluation is NOT_TESTED without real per-arm predictions. AUROC is only for binary score-labelled decisions.',
  """import sys,json
from pathlib import Path
r=Path.cwd().resolve()
if r.name=='notebooks':r=r.parent
sys.path.insert(0,str(r/'scripts'))
from quality_metrics import confusion,auroc,holm
modules=['preprocessing','retrieval','antigence_challenge','memory','model_routing','fhir_validator']
labels=[0,0,1,1];scores=[.1,.4,.7,.9]
assert auroc(labels,scores)==1.0
assert confusion(labels,scores)['FPR']==0
print(json.dumps({'module_ablations':{m:'NOT_TESTED' for m in modules},
  'synthetic_stats_fixture':{'auroc':auroc(labels,scores),
    **confusion(labels,scores)},'real_claim':'NOT_TESTED'},sort_keys=True))"""))
BOOKS.append(notebook('04_synthea_to_ehr_form',
  'Create deterministic synthetic source-grounded HTML forms from Synthea, then OCR images in a separate experiment. A rendered text form is not validated OCR. Never issue live EHR writes.',
  """import os,sys,json,tempfile
from pathlib import Path
r=Path.cwd().resolve()
if r.name=='notebooks':r=r.parent
sys.path.insert(0,str(r/'scripts'))
from forms_fixture import build_forms
p=os.environ.get('SYNTHEA_CSV_ZIP')
if p:
    with tempfile.TemporaryDirectory() as d:
        receipt=build_forms(Path(p),Path(d),limit=2)
        print(json.dumps(receipt,sort_keys=True))
else:
    print(json.dumps({'synthea_form_render':'NOT_TESTED_SOURCE_ABSENT',
      'epic_write':'PROHIBITED','clinical_validation':'NOT_TESTED'}))"""))
BOOKS.append(notebook('05_fireworks_harness_costs',
  'Do not call provider without authenticated authorization. Pin model, case IDs, prices, settings and image token count; compare direct and governed inference on same model. Provider execution is NOT_TESTED without receipts.',
  """import json,os
pricing={'input_usd_per_million':None,'output_usd_per_million':None,
 'source_timestamp':None,'model':None}
assert all(pricing[k] is None for k in ('input_usd_per_million','output_usd_per_million'))
print(json.dumps({'fireworks':'NOT_TESTED','pricing':'NOT_COMPUTED',
 'token_roi':'NOT_COMPUTED','method':'same-model direct vs governed paired evaluation',
 'note':'Do not equate model token output with billable image/OCR usage'},sort_keys=True))"""))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--check',action='store_true')
    args=p.parse_args()
    failures=[]
    for path,content in BOOKS:
        if args.check:
            if not path.exists() or path.read_text()!=content:failures.append(path.name)
        else:
            path.parent.mkdir(exist_ok=True,parents=True)
            path.write_text(content)
    if failures: raise SystemExit('NOTEBOOK_OUT_OF_SYNC:'+','.join(failures))
    print('NOTEBOOKS_'+('CHECKED' if args.check else 'WRITTEN')+' '+str(len(BOOKS)))
