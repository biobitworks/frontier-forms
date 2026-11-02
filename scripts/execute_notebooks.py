#!/usr/bin/env python3
"""Execute all notebooks in a repo-local ephemeral kernel environment.
Executed notebooks become successor receipts; never rewrite source notebooks.
"""
from pathlib import Path
import json,hashlib,os,sys,tempfile,datetime,uuid
R=Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='frontier-forms-kernels-') as tmp:
    ks=Path(tmp)/'kernels'/'frontierforms-evidence';ks.mkdir(parents=True)
    kernel={'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
      'display_name':'Frontier Forms Evidence','language':'python'}
    (ks/'kernel.json').write_text(json.dumps(kernel))
    os.environ['JUPYTER_PATH']=tmp+os.pathsep+os.environ.get('JUPYTER_PATH','')
    import nbformat
    from nbclient import NotebookClient
    run_name='RUN-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:12]
    out=R/'evidence/notebook_runs'/run_name
    out.mkdir(parents=True,exist_ok=False)
    results=[]
    for p in sorted((R/'notebooks').glob('*.ipynb')):
      nb=nbformat.read(str(p),as_version=4)
      state='PASS';error=None
      try:
        ran=NotebookClient(nb,timeout=180,kernel_name='frontierforms-evidence',
                          resources={'metadata':{'path':str(R)}}).execute()
        op=out/(p.stem+'_EXECUTED.ipynb')
        nbformat.write(ran,str(op))
        sha=hashlib.sha256(op.read_bytes()).hexdigest()
      except Exception as ex:
        state='FAIL';error=type(ex).__name__+': '+str(ex)[:700]
        sha=None
      results.append({'notebook':p.name,'execution':state,'receipt_sha256':sha,'error':error})
      print('NOTEBOOK',p.name,state,flush=True)
    manifest={'schema':'notebook.execution.v1','execution_environment':'LOCAL_PYTHON3.12_IPYKERNEL',
      'receipt_directory':out.relative_to(R).as_posix(),
      'predecessor_run':'evidence/notebook_runs_v4',
      'notebooks':results,'model_inference':'NOT_RUN_IN_NOTEBOOKS','clinician_assessment':'NOT_TESTED',
      'claims':'OFFLINE_PROTOCOL_AND_REPLAY_ONLY'}
    (out/'execution_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    if any(x['execution']!='PASS' for x in results):raise SystemExit(3)
    print('APPEND_ONLY_EXECUTION_RECEIPTS',out.relative_to(R),flush=True)
