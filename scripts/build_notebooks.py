#!/usr/bin/env python3
"""Generates notebooks with Requirements/Data Input/Analysis/Output and explicit claim ceilings."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent.parent
def md(s):return {"cell_type":"markdown","id":hashlib.sha256(("md:"+s).encode()).hexdigest()[:12],"metadata":{},"source":s}
def code(s):return {"cell_type":"code","id":hashlib.sha256(("code:"+s).encode()).hexdigest()[:12],"execution_count":None,"metadata":{},"outputs":[],"source":s}
def nb(name,title,requirements,inputs,analysis,outputs,cells):
    intro=f"""# {title}

## Requirements
{requirements}

## Data input
{inputs}

## Data analysis
{analysis}

## Data output
{outputs}

## Claim ceiling
Notebook execution PASS verifies its local checks only. It never promotes a missing model/harness, held-out dataset, live Epic/Snyk API, Lean proof, or NVIDIA GPU to EXECUTED.
"""
    n={"cells":[md(intro)]+[code(x) for x in cells],"metadata":{"kernelspec":{"display_name":"FrontierForms Evidence Python","language":"python","name":"frontierforms-evidence"},"language_info":{"name":"python"}},"nbformat":4,"nbformat_minor":5}
    p=R/'notebooks'/name;p.write_text(json.dumps(n,indent=1)+"\n")
    print("WROTE",p.name)

nb("00_fco_merkle_replay.ipynb","EXP-000: Frozen predecessor Merkle verification",
"- Python 3.12+; exact frozen manifest and 15 leaf JSON records.\n- Exact SHA-256 root with explicit domain separation; comparison to declared predecessor.",
"- evidence/freeze/predecessor/manifest.json and leaves.jsonl, with no raw source or gold labels.",
"- Recompute every leaf hash with canonical JSON and every binary Merkle level; duplicate last leaf when odd.",
"- Root equality, ordered leaf count, predecessor reference, NOT_SIGNED and NOT_MMR_COMMITTED statuses.",
["""from pathlib import Path
import json,hashlib,sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
from verify_predecessor import verify
bundle=ROOT/'evidence/freeze/predecessor'
result=verify(bundle)
assert result['root']=='9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a'
assert result['root_recomputed']=='PASS' and result['leaves']==15
assert result['source_sha_verification']=='NOT_TESTED' and result['mmr']=='NOT_COMPUTED'
print(json.dumps({k:result[k] for k in ('root','root_recomputed','leaves','signature','mmr')},indent=2))"""])

nb("01_paired_mcnemar_bootstrap.ipynb","EXP-001: McNemar × paired bootstrap",
"- Exact one-to-one matched prompts, frozen discovery split, no tuning on held-out evaluation.\n- Alpha 0.05, two-sided exact McNemar and within-task paired bootstrap.",
"- evidence/stats/discovery_pair_flags.jsonl (hashed case keys + paired correctness flags only).",
"- Count four correctness cells; apply exact binomial discordance test; stratified paired bootstrap with pinned seed.",
"- Observed p-value, CI, promotion gate and explicit FAIL on superiority (not a notebook runtime failure).",
["""import json,sys,hashlib
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'src'))
from frontier_forms.statistics import admit
rows=[json.loads(x) for x in (R/'evidence/stats/discovery_pair_flags.jsonl').read_text().splitlines()]
result=admit(rows)
assert result['n']==38
assert result['table']['baseline_only']==2 and result['table']['challenger_only']==4
assert result['p_mcnemar_exact_two_sided']==0.6875
assert result['mcnemar_positive_gate'] is False
assert result['bootstrap_positive_gate'] is False
print(json.dumps(result,sort_keys=True,indent=2))"""])

nb("02_classification_auroc_fpr_fdr.ipynb","EXP-002: FPR, FDR, TPR, and AUROC admission",
"- Define the positive class before analysis; do not combine incompatible clinical task classes.\n- AUROC requires per-case continuous prediction scores and both classes.",
"- Per-task aggregated confusion tables for baseline and challenger; no patient records.",
"- Recompute FPR=FP/(FP+TN), FDR=FP/(TP+FP), TPR=TP/(TP+FN); guard zero denominator; gate AUROC.",
"- Task-wise metrics; AUROC NOT_COMPUTED when only hard labels exist.",
["""import json
from pathlib import Path
R=Path.cwd();s=json.loads((R/'evidence/stats/discovery_audit.json').read_text())
for task,arms in sorted(s['FPR_FDR_by_task'].items()):
    for arm,m in arms.items():
        tp,fp,tn,fn=(m[k] for k in ('TP','FP','TN','FN'))
        calc=lambda n,d:n/d if d else None
        assert m['FPR']==calc(fp,fp+tn)
        assert m['FDR']==calc(fp,tp+fp)
        assert m['TPR']==calc(tp,tp+fn)
        assert m['AUROC']=='NOT_COMPUTED_NO_CONTINUOUS_SCORES'
        print(task,arm,'FPR',m['FPR'],'FDR',m['FDR'],'TPR',m['TPR'])
print('AUROC_GATE=NOT_COMPUTED_NO_CONTINUOUS_SCORES')
print('NOTE: positive label A is arbitrary, NOT a medical diagnosis.')"""])

nb("03_lomo_harness_ablation.ipynb","EXP-003: LOMO / mechanism intervention ledger",
"- Each leave-one-mechanism-out (LOMO) arm must use same frozen Fireworks model, cases, system instructions, and generation parameters.\n- Identical-case counters and independent scorer.",
"- Planned harness arms and absent paired execution receipts.",
"- Declare pretraining/posttraining and mechanism interventions; do not infer their contribution from model-vs-model comparison.",
"- Machine-readable DEFERRED / NOT_TESTED matrix and no causal claim until each controlled removal executes.",
["""import json
mechanisms=['antigence_injection_policy','fco_fcg_context_binding','mcp_tool_permission_gate','evidence_grounding','recovery_abstention']
arms=[{'arm':'FULL','status':'NOT_TESTED','frozen_model':'UNSELECTED_FIREWORKS_SERVERLESS'}]
arms += [{'arm':'MINUS_'+m.upper(),'removed_mechanism':m,'status':'NOT_TESTED'} for m in mechanisms]
assert len({x['arm'] for x in arms})==len(arms)==6
assert all(x['status']=='NOT_TESTED' for x in arms)
print(json.dumps({'arms':arms,'LOMO_DELTA_AUROC':'NOT_COMPUTED','CAUSAL_INFERENCE':'NOT_SUPPORTED'},indent=2))"""])

nb("04_synthea_to_fhir_contract.ipynb","EXP-004: Synthea/Epic FHIR no-writeback contract",
"- Use synthetic patient records only. Production Epic credentials and write access explicitly prohibited.\n- FHIR resource shape is an interface constraint, NOT proof of interoperability.",
"- Metadata-only example fixture (manual synthetic value, NOT claimed to be Synthea output).",
"- Type-check draft FHIR Patient, Observation and Provenance resource envelopes; reject undeclared source.",
"- Validation of fixture envelope, source_type, patient id, and LIVE_EPIC=NOT_TESTED.",
["""import json, re
source={'source_type':'MANUAL_SYNTHETIC_FIXTURE_NOT_SYNTHEA','patient_id':'test-patient-001','clinical_name':'EXAMPLE ONLY'}
FHIR={'resourceType':'Patient','id':source['patient_id'],'identifier':[{'system':'urn:frontier-forms:test-only','value':source['patient_id']}],
      'name':[{'text':source['clinical_name']}]}
assert FHIR['resourceType']=='Patient'
assert re.fullmatch(r'[A-Za-z0-9\\-.]{1,64}',FHIR['id'])
assert source['source_type']!='REAL_PATIENT'
print(json.dumps({'example_fhir':FHIR,'FHIR_STRUCTURE':'FIXTURE_ONLY','SYNTHEA_FORM_OCR':'NOT_TESTED',
  'EPIC_OAUTH':'NOT_TESTED','EPIC_READ':'NOT_TESTED','EPIC_WRITE':'PROHIBITED'},indent=2))"""])

nb("05_fireworks_pricing_roi.ipynb","EXP-005: Fireworks token ROI & economic comparison",
"- Use model- and date-pinned Fireworks serverless prices; actual usage requires API receipts.\n- Never equate illustrative token charges with actual cost, GPU energy, or productivity ROI.",
"- Public advertised GLM-5.3-Flash unit rates as of 2026-11-02, actual usage records absent.",
"- Formula: input_token_count×input_rate/1e6 + cached×cached_rate/1e6 + output×output_rate/1e6.\n- Compare quality-adjusted cost only after held-out performance and serverless receipts exist.",
"- Unit-test pricing formula; actual cost/ROI NOT_COMPUTED.",
["""import json
price={'model':'accounts/fireworks/models/glm-5p3-flash','asof':'2026-11-02',
  'input_per_million_usd':0.15,'cached_per_million_usd':0.03,'output_per_million_usd':0.50,
  'source':'https://fireworks.ai/models/fireworks/glm-5p3-flash'}
def cost(inp,out,cached=0):
    assert inp>=0 and out>=0 and cached>=0
    return (inp*price['input_per_million_usd']+out*price['output_per_million_usd']+cached*price['cached_per_million_usd'])/1e6
assert abs(cost(1000000,1000000)-.65)<1e-12
assert cost(0,0)==0
print(json.dumps({'unit_test':'PASS','pricing':price,'actual_fireworks_usage':'NOT_TESTED',
  'cost_per_correct':'NOT_COMPUTED','token_ROI':'NOT_COMPUTED','quality_guardrail':'NOT_TESTED'},indent=2))"""])

nb("06_lean_gsd_gsigmad_admission.ipynb","EXP-006: Lean4 / GSD / GSigmaD integration gates",
"- GSD governs project phases; GSigmaD governs EXP/prompt/lab notebook claims.\n- Lean4 source file can be committed but may not be declared proved unless actual lean command exits 0.",
"- docs/protocols and .planning phase; absence of executed Lean/Snyk/gsigmad receipts.",
"- Review required source files, distinguish proposed governance from executed validation.",
"- PASS for documentation check; Lean/GSD/GSigmaD claim promotion remains NOT_TESTED.",
["""from pathlib import Path
import json,hashlib
r=Path.cwd()
required=['.planning/phases/01-source-audit.md','docs/protocols/EXPERIMENT_CONTRACT.md',
          'docs/reviews/CLAUDE_HANDOFF.md','lean/Admission.lean']
for f in required:
    assert (r/f).exists(),f
print(json.dumps({'documentation_presence':'PASS','lean_compilation':'NOT_TESTED',
'gsigmad_experiment_audit':'NOT_TESTED','gsd_phase_runner':'NOT_TESTED',
'snyk_scan':'NOT_TESTED','claims_gate':'HOLD'},indent=2))"""])

nb("07_supabase_source_gate.ipynb","EXP-007: Supabase dataset intake, no premature freeze",
"- A source link, access authority, schema and data classification are prerequisites for a database query.\n- No actual row/transaction/source hash is asserted without an observed snapshot.",
"- evidence/sources/supabase_source_intake.json (user-reported dataset under construction; contains no raw rows).",
"- Validate explicit UNKNOWN/NULL/NOT_COMPUTED states and a nonadmitted source edge; verify frozen predecessor is preserved.",
"- Report SOURCE=REPORTED_IN_PROGRESS, FROZEN=NO, SOURCE_MERKLE=NOT_COMPUTED and block Fireworks training/evaluation admission.",
["""import json
from pathlib import Path
r=Path.cwd()
s=json.loads((r/'evidence/sources/supabase_source_intake.json').read_text())
assert s['schema']=='fco.supabase.source_intake.v1'
assert s['state']=='REPORTED_IN_PROGRESS'
assert s['rows_observed'] is None
assert s['project_ref'] is None
assert s['snapshot_merkle_root']=='NOT_COMPUTED'
assert s['actual_supabase_query']=='NOT_EXECUTED'
assert s['source_to_fcg_edge']['state']=='NOT_TESTED'
print(json.dumps({'source_intake':'PASS','dataset_freeze':'NOT_EXECUTED',
 'row_count':'UNKNOWN','snapshot_root':'NOT_COMPUTED',
 'fireworks_admission':'BLOCKED_SOURCE_NOT_FROZEN'},indent=2))"""])
