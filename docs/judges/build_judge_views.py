#!/usr/bin/env python3
"""Build judge views from frozen, already-published PR and measurement receipts.
Does not train models, rerun experiments, rewrite input evidence, or compute Merkle roots.
"""
import html
import json
import subprocess
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/judges'
PULL=json.loads((OUT/'PR_HISTORY_SNAPSHOT.json').read_text())
def read(rel):return json.loads((ROOT/rel).read_text())
base=read('evidence/baseline/BASELINE_V1.json')
vlm=read('evidence/forms_vision/V1-qwen2.5vl-3b/summary.json')
tess=read('evidence/forms_vision/T1-tesseract-redteam/summary.json')
bbox=read('evidence/forms_bbox/LOCAL_BBOX_D1_D2_AUDIT_20261102.json')
logit=read('evidence/forms_box_validator/run_v3/summary.json')
det=read('evidence/forms_detectors/run_v1/DETECTOR_RESULTS_V1.json')
src_prs={x['number']:x for x in PULL['prs']}
CLAUDE={6,9,10,11,13,17,19,20,21,23,26,29,42}
CHATGPT={7,12,14,15,16,18,22}
TEAM={4}
def credit(n):
 if n in CLAUDE:return 'Claude Code (documented lane)' if n in (10,11,17,19,20,21,23,26,29,42) else 'Claude-associated / review'
 if n in (16,22):return 'ChatGPT (this conversation)'
 if n in CHATGPT:return 'ChatGPT / independent review lane'
 if n in TEAM:return 'Teammate (documented in PR)'
 return 'Unattributed / not independently established'
prs=[{'number':p['number'],'title':p['title'],'state':p['state'],'head':p['headRefOid'],'credit':credit(p['number']),
      'attribution_basis':'PR description/session or explicitly known lane; GitHub login is not reliable contributor attribution',
      'url':p['url']} for p in PULL['prs']]
(OUT/'PR_CONTRIBUTION_LEDGER.json').write_text(json.dumps({'schema':'FF-JUDGE-CREDIT-V1',
 'parent_main_sha':PULL['main_parent_sha'],'pr_count':len(prs),
 'credit_notes':'Credit identifies documented work lanes, not verified human authorship. Review and co-contributions may overlap.',
 'pulls':prs},indent=2,sort_keys=True)+'\n')
source={
 'baseline':'evidence/baseline/BASELINE_V1.json',
 'vlm':'evidence/forms_vision/V1-qwen2.5vl-3b/summary.json',
 'tesseract':'evidence/forms_vision/T1-tesseract-redteam/summary.json',
 'd1_d2':'evidence/forms_bbox/LOCAL_BBOX_D1_D2_AUDIT_20261102.json',
 'logistic':'evidence/forms_box_validator/run_v3/summary.json',
 'detector':'evidence/forms_detectors/run_v1/DETECTOR_RESULTS_V1.json',
 'training_history':'dashboard/training_progress_latest.json'
}
metrics=[
 {'id':'KPI-01','value':'100','title':'Synthetic patients','denominator':'100 FHIR R4 subset bundles','pr':10,'source':'data/forms_cohort_v1/MANIFEST.json','claim':'OBSERVED','caveat':'Not 100 independent datasets; separate from teammate Supabase cohort'},
 {'id':'KPI-02','value':'18 / 54','title':'Frozen baseline full-form success','denominator':'18 held-out patients × 3 forms','pr':17,'source':source['baseline'],'claim':'OBSERVED','caveat':'B0 deterministic rules; every required field must be correct'},
 {'id':'KPI-03','value':'30 / 54','title':'B0 + L1+L2+L3 full-form success','denominator':'Same held-out 54 forms','pr':10,'source':source['baseline'],'claim':'DISCOVERY_ONLY','caveat':'Rules developed after B0 errors inspected; not independent replication'},
 {'id':'KPI-04','value':f"{vlm['box_recall_iou50']*100:.1f}%",'title':'Local pretrained VLM box recall','denominator':f"{vlm['fields']} fields / {vlm['images']} images",'pr':19,'source':source['vlm'],'claim':'OBSERVED','caveat':f"213 false boxes; {vlm['value_read_match_nonblank']*100:.1f}% value read match, not source-truth correctness"},
 {'id':'KPI-05','value':f"{bbox['D2']['metrics']['recall_iou50']*100:.1f}%",'title':'D2 trained candidate-box recall','denominator':f"{bbox['D2']['test_images']} held-out filled images, known layouts",'pr':16,'source':source['d1_d2'],'claim':'EXPLORATORY','caveat':f"Precision {bbox['D2']['metrics']['precision_iou50']*100:.1f}%; {bbox['D2']['metrics']['fp']} false positives; post-hoc architecture"},
 {'id':'KPI-06','value':f"{det['combinations']['M1+M2+M3']['recall']*100:.1f}%",'title':'Synthetic injected-error detector recall','denominator':f"{det['combinations']['M1+M2+M3']['instances']} injected faults",'pr':10,'source':source['detector'],'claim':'DISCOVERY_ONLY','caveat':f"{det['combinations']['M1+M2+M3']['fp_fields']} false-positive clean fields; shared generator/oracle risk"}
]
rows=[
 ('Synthetic cohort & source provenance',('REPORTED','100 Supabase patients; DB readback not verified','#4'),('OBSERVED','100 Synthea v3.4.0 JSON subset patients, 63/19/18','#10'),('REVIEWED','Independent provenance checks; not identical to Supabase','#17'),('PARTIAL','Synthetic FHIR only; Epic sandbox distinct','#10')),
 ('HTML form test server',('IMPLEMENTED','Supabase/teammate application lane','#4'),('OBSERVED','Read-only loopback FHIR, 3 forms, B0','#10'),('OBSERVED','100-patient 218-case echo runner in open PR','#22'),('PARTIAL','No real Epic UI/production writeback','#22')),
 ('Field mapping accuracy',('UNKNOWN','Teammate DB accuracy not verified','#5'),('DISCOVERY','B0+FCG 30/54 vs 18/54, previously inspected test','#10'),('OBSERVED','B0 full 218 cases, 1,867/2,180 fields correct','#22'),('NOT_TESTED','New independent cohort required','#31')),
 ('Local Qwen text inference',('NOT_TESTED','No independently verified teammate model gain','#4'),('OBSERVED','Red-team Qwen mapper 46-image comparison','#23'),('OBSERVED','One-patient Qwen 12/20 smoke in draft','#22'),('NEGATIVE','Qwen mappers below deterministic parser in PR23','#23')),
 ('Qwen LoRA weight training',('NOT_TESTED','No audited production fine-tune','#4'),('IN_PROGRESS','M0/M1 training and scoring work item','#38'),('NOT_TESTED','No completed post-training admission in this review','#22'),('NOT_TESTED','Weight-change improvement absent','#38')),
 ('HTML/CSS and PDF readback',('NOT_TESTED','Teammate production form readback unavailable','#37'),('OBSERVED','Local Apple PDFKit OCR arm and receipts','#10'),('OBSERVED','CSS preview, Qwen PDF smoke and 3 PDF OCR files in open PR','#22'),('PARTIAL','Full pipeline readback unverified','#22')),
 ('Pretrained VLM & OCR',('NOT_TESTED','Teammate visual QA not verified','#4'),('OBSERVED','Qwen2.5vl:3b 57 images; Tesseract 57 images','#19'),('OBSERVED','One-form Apple/Qwen paired field fixture','#12'),('PARTIAL','OCR text location != clinical source correctness','#19')),
 ('Trained bbox validators',('NOT_TESTED','No teammate weight-provenance evaluation','#4'),('IMPLEMENTED','YOLOv8n pipeline; final generalization not established','#19'),('NEGATIVE','D1 13.1% recall; D2 95.6% recall, low precision; logistic tie','#16'),('NOT_TESTED','Unseen form-family detector replication','#40')),
 ('Prompt-injection robustness',('NOT_TESTED','No clinical adversarial exercise','#4'),('OBSERVED','18 paired VLM injection examples (PR draft)','#29'),('OBSERVED','Synthea field forgery O/0 and source-binding fixtures','#12'),('PARTIAL','Filter false-strip and new threat set not admitted','#34')),
 ('Lean/Merkle/FCO/LOMO custody',('NOT_TESTED','No end-to-end teammate writeback proof','#5'),('OBSERVED','Independent root replay and gate factorial, custody weaknesses','#21'),('OBSERVED','Single-leaf ablations/identity audits, no causal inference','#18'),('DISCOVERY','Source graph admission not production causal proof','#44')),
 ('Public synthetic JSON policy',('UNKNOWN','Legacy files subject to exact-blob policy','#30'),('IMPLEMENTED','Tasks/CI and security review successors','#42'),('OBSERVED','Strict checker and legacy-freeze reconciliation','#30'),('PARTIAL','Legacy non-JSON bytes excepted; CI status must be checked','#30')),
 ('Replication & real Epic writeback',('NOT_TESTED','DB readback not established','#37'),('NOT_TESTED','New cohort and Epic form fidelity pending','#31'),('NOT_TESTED','No live Epic write/read authorization','#22'),('NOT_TESTED','No validated end-to-end writeback','#44'))
]
columns=['Teammate','Claude','ChatGPT / independent','Cross-lane admission']
matrix=[]
for label,*cells in rows:
 matrix.append({'capability':label,'cells':[{'column':columns[i],'state':c[0],'detail':c[1],'reference':c[2]} for i,c in enumerate(cells)]})
package={'schema':'FF-JUDGES-ACCOMPLISHMENT-MATRIX-V1','parent_main_sha':PULL['main_parent_sha'],
 'pr_snapshot':PULL['summary'],'pr_count':len(PULL['prs']),'credit_policy':'Human/team/Claude vs ChatGPT credit based on distinct PR lanes; not inferred from shared github login.',
 'metrics':metrics,'matrix':matrix,'source_files':source,'detector_factorial':[{'combination':k,'recall':v['recall'],'false_positive_clean_fields':v['fp_fields'],'instances':v['instances'],'status':'DISCOVERY_ONLY'} for k,v in sorted(det['combinations'].items())], 'merkle_root':'NOT_COMPUTED',
 'model_gain_admitted':'NO','real_epic_writeback':'NOT_TESTED','publication_note':'Legacy byte exceptions are not a claim that old binaries conform to JSON-only requirements.'}
(OUT/'ACCOMPLISHMENT_MATRIX_20261102.json').write_text(json.dumps(package,indent=2,sort_keys=True)+'\n')
print('BUILT matrix cells',len(matrix)*4,'metrics',len(metrics),'PRs',len(prs))
# Every pre-existing main image is inventoried and given a caption. This does
# NOT modify, replace, edit, or republish the underlying binary images.
def classify(path):
 if path.startswith('data/forms_vision_v1/'):
  if Path(path).name.startswith('blank__'):return 'Synthetic blank web-form screenshot (DOM box training/reference; not model prediction).',10,'OBSERVED'
  return 'Synthetic B0-filled web-form screenshot (image evidence only; clinical correctness not implied).',10,'OBSERVED'
 if path.startswith('data/forms_vision_inject_v1/'):
  return 'Synthetic medication/allergy intake screenshot for clean-versus-prompt-injection testing.',10,'OBSERVED'
 if path.startswith('redteam/ehr/data/forms/'):
  return 'SYNFORM2 red-team '+('injected' if '.inj.' in path else 'clean')+' form; not a real patient record.',21,'OBSERVED'
 if path.startswith('experiments/form_error_factorial/'):
  return 'Synthetic intake form image used in the independent Apple Vision/Qwen example; not benchmark-wide evidence.',12,'OBSERVED'
 if path.startswith('docs/architecture/'):
  return 'Diagram of FCO/FCG and gate-factorial study; depicts synthetic experiment, not real-world clinical gain.',21,'OBSERVED'
 return 'Existing repository visual; subject not independently pixel-inspected.',None,'UNKNOWN'
imgs=sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('*')
            if p.is_file() and p.suffix.lower() in ('.png','.svg','.jpg','.jpeg','.webp','.gif')
            and '.git' not in p.parts and not str(p.relative_to(ROOT)).startswith('docs/judges/'))
asset_inventory=[]
for i,p in enumerate(imgs,1):
 cap,n,state=classify(p)
 asset_inventory.append({'image_id':f'IMG-{i:03}','path':p,'caption':cap,'source_pr':n,
      'credit':credit(n) if n else 'UNKNOWN','status':state,
      'scope':'Already tracked in main; this inventory does not claim that bytes comply with the new JSON-only publication policy',
      'link':'../../'+p})
# Draft Claude image overlays, never mislabeled as merged main assets.
try:
 draft_pr=src_prs[29]
 listing=json.loads(subprocess.check_output(['gh','pr','view','29','-R','biobitworks/frontier-forms',
                         '--json','files','--jq','[.files[].path]'],text=True))
 overlays=sorted(p for p in listing if p.endswith('.overlay.png'))
 for j,p in enumerate(overlays,1):
  asset_inventory.append({'image_id':f'DRAFT-IMG-{j:03}','path':p,
      'caption':'Claude Qwen2.5VL box/label overlay, '+('injected' if '/injected__' in p else 'clean')+' synthetic form. Draft figure; provenance from PR #29.',
      'source_pr':29,'credit':'Claude Code (documented lane)','status':'DRAFT_ONLY',
      'scope':'Open PR #29; do not present as evidence already merged into main.',
      'link':'https://github.com/biobitworks/frontier-forms/blob/'+draft_pr['headRefOid']+'/'+p})
except Exception as exc:
 overlays=[]
 print('DRAFT_OVERLAY_INVENTORY_UNAVAILABLE',str(exc)[:140])
(OUT/'IMAGE_CAPTION_INVENTORY.json').write_text(json.dumps({'schema':'FF-JUDGES-IMAGE-CAPTIONS-V1',
 'main_sha':PULL['main_parent_sha'],'main_images':len(imgs),'draft_overlay_images':len(overlays),
 'images':asset_inventory,'pixel_inspection':'NOT_EXECUTED; captions grounded in file paths and source workflows'},indent=2,sort_keys=True)+'\n')
def pick(prefix):
 return next((i['path'] for i in asset_inventory if i['path'].startswith(prefix) and i['status']!='DRAFT_ONLY'),None)
figs=[
 ('FIG-01','Gate-factorial and Merkle/Lean/FCO experiment','docs/architecture/gate_factorial_heatmap.svg',21,'Observed synthetic gate-factorial diagram; roots attest canonical identity, not causality.','OBSERVED'),
 ('FIG-02','Longitudinal progress dashboard','dashboard/training_progress.html',18,'Distinguishes actual model snapshots, weight-only comparisons, LOMO and cross-sectional ablations.','OBSERVED'),
 ('FIG-03','Error detector factorial heatmap','evidence/forms_detectors/run_v1/heatmap.html',10,'702 injected errors; full M1+M2+M3 recall 694/702 with 236 false-positive clean fields.','DISCOVERY'),
 ('FIG-04','16-mask synthetic source-fault heatmap','experiments/form_error_factorial/heatmap.html',12,'Small/medium/tiny synthetic challenge fixtures; by-design corrections do not demonstrate model improvement.','DISCOVERY'),
 ('FIG-05','Apple Vision / Qwen field-box overlay example','experiments/form_error_factorial/vision_overlay.html',12,'Eight-field synthetic fixture; actual answers and boxes, not a 100-form clinical benchmark.','OBSERVED'),
 ('FIG-06','Synthetic blank registration form','data/forms_vision_v1/blank__new_patient_registration_v1.png',10,'Browser raster of empty synthetic form; DOM gold box geometry is not independent annotation.','OBSERVED'),
 ('FIG-07','Filled registration form from B0',pick('data/forms_vision_v1/filled__new_patient_registration_v1__'),10,'Synthetic patient values rendered in a test form; does not establish held-out clinical accuracy.','OBSERVED'),
 ('FIG-08','Synthetic adversarial medication-allergy intake',pick('data/forms_vision_inject_v1/injected__medication_allergy_intake_v1__'),10,'Injected instruction is untrusted page content; compare against clean twin before robustness claims.','OBSERVED'),
 ('FIG-09','Local Apple/Qwen demonstration raster','experiments/form_error_factorial/sample_vision/synthetic_intake.png',12,'Single synthetic intake example with separate model/box receipts.','OBSERVED'),
 ('FIG-10','Historical evidence admission heatmap','dashboard/training_heatmap.html',7,'Earlier historical/planned statuses; do not use as evidence of new neural training gains.','HISTORICAL')
]
figs.append(('FIG-11','Claude clean bounding-box overlay viewer (draft)','evidence/forms_vision/bbox_overlays_v1.html',29,
 'Interactive JSON-derived overlay viewer from open PR #29; not merged. Model predictions, not oracle truth.','DRAFT_ONLY'))
figs.append(('FIG-12','Claude adversarial bounding-box overlay viewer (draft)','evidence/forms_vision/bbox_overlays_inject_v1.html',29,
 'Clean/injected synthetic viewer from open PR #29; its claimed robustness requires independent audit.','DRAFT_ONLY'))
figures=[]
for fid,title,path,pr,caveat,state in figs:
 if not path:continue
 link=('https://github.com/biobitworks/frontier-forms/blob/'+src_prs[29]['headRefOid']+'/'+path if state=='DRAFT_ONLY' else '../../'+path)
 figures.append({'id':fid,'title':title,'path':path,'source_pr':pr,'credited_lane':credit(pr),
    'status':state,'caption':caveat,'href':link,'alt':title+' — '+state,
    'asset_kind':'image' if Path(path).suffix.lower() in ('.png','.svg','.jpg','.jpeg') else 'interactive HTML'})
(OUT/'JUDGE_FIGURE_CATALOG.json').write_text(json.dumps({'schema':'FF-JUDGE-FIGURES-V1','parent_main_sha':PULL['main_parent_sha'],
 'figures':figures,'figure_count':len(figures),'policy':'References existing images; no new public patient images or weights are generated.'},indent=2,sort_keys=True)+'\n')
print('CAPTIONS',len(asset_inventory),'MAIN',len(imgs),'DRAFT',len(overlays),'FIGURES',len(figures))
