"""Export only aggregate local run metrics and render model-specific horizontal bars.
Usage: python bench/publish_live_results.py --source /path/to/bench/results/pilot
No model calls, credentials, patient records, predictions or answer keys are exported.
"""
import argparse,hashlib,json,statistics as st
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'charts'
MODELS=['deepseek-v4p1-flash','glm-5p3','qwen3p8-max','gpt-oss-120b']
NAMES={'deepseek-v4p1-flash':'DeepSeek V4.1 Flash','glm-5p3':'GLM 5.3','qwen3p8-max':'Qwen Max','gpt-oss-120b':'GPT-OSS 120B'}
ARMS=['pi+browser-tools','frontier-tools']
METRICS=['arm','model','form','repeat','failed','timed_out','seconds','correct','fields','full_form','model_calls','cost_usd','input','cached','output','wrong','missed','fabricated','unsafe','submitted','unknown','unknown_held','unknown_flagged','evidence_valid','evidence_needed','sensitivity']
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);args=ap.parse_args()
raw=[]
for p in sorted(args.source.glob('*.r1.json')):
 try:r=json.loads(p.read_text())
 except (ValueError,OSError):continue
 if r.get('model') not in MODELS or r.get('arm') not in ARMS:continue
 if r.get('form') not in ['primary_care_registration','urgent_care_history','insurance_update']:continue
 if r.get('patient') not in ['SYN-00015','SYN-00037']:continue
 raw.append((r,hashlib.sha256(p.read_bytes()).hexdigest()))
cases={c:f'case-{i+1:02}' for i,c in enumerate(sorted({(r['form'],r['patient']) for r,_ in raw}))}
rows=[]
for r,digest in raw:
 row={k:r.get(k) for k in METRICS};row.update(case=cases[(r['form'],r['patient'])],local_receipt_sha256=digest);rows.append(row)
payload={'classification':'SYNTHETIC_AGGREGATE_METRICS_ONLY','expected_runs_per_model':12,'models':MODELS,'runs':rows}
serialized=json.dumps(payload,indent=2,sort_keys=True)+'\n'
p=OUT/'live_metrics.json'
if p.exists() and p.read_text()==serialized:
 print('UNCHANGED');raise SystemExit(0)
p.write_text(serialized)
plt.rcParams.update({'svg.hashsalt':'frontier-live','font.family':'DejaVu Sans','font.size':11})
fig,axes=plt.subplots(4,1,figsize=(11,12));fig.subplots_adjust(left=.34,right=.88,top=.87,bottom=.09,hspace=.9)
fig.suptitle('Real Pi baseline vs our tooling — by model',x=.035,y=.98,ha='left',fontsize=20,fontweight='bold')
fig.text(.035,.93,'Same synthetic medical cases per model • median completion time • lower is better',color='#475569')
lines=['# Live model benchmark results','','Real Pi + browser-tools versus the same model with Frontier Forms tools. Updated whenever a local run finishes. Only matched cases enter comparison bars; unfinished and failed cases remain visible below.','',
'![Model speed comparisons](model_speed.png)','','| Model | Runs saved | Matched cases | Median Pi → tools | Correct fields Pi → tools | Mean estimated API cost Pi → tools | Failures Pi / tools |','|---|---:|---:|---|---|---|---|']
for ax,model in zip(axes,MODELS):
 rs=[r for r in rows if r['model']==model]; lookup={(r['case'],r['arm']):r for r in rs}
 matched=sorted(c for c in {r['case'] for r in rs} if all((c,a) in lookup for a in ARMS))
 paired={a:[lookup[(c,a)] for c in matched] for a in ARMS}
 failures=[sum(bool(r['failed'] or r['timed_out']) for r in rs if r['arm']==a) for a in ARMS]
 ax.set_title(f'{NAMES[model]}   |   {len(rs)}/12 runs saved, {len(matched)}/6 matched cases',loc='left',fontsize=12,fontweight='bold')
 ax.set_yticks([1,0],['Baseline: model + Pi','Same model + our tooling']);ax.tick_params(axis='y',length=0)
 ax.set_ylim(-.6,1.6)
 for side in ['top','right','left']:ax.spines[side].set_visible(False)
 if matched:
  values=[st.median(r['seconds'] for r in paired[a]) for a in ARMS]
  ax.barh([1,0],values,color=['#64748b','#059669'],height=.5);ax.set_xlim(0,max(values)*1.3 or 1)
  for y,v in zip([1,0],values):ax.text(v+ax.get_xlim()[1]*.025,y,f'{v:.1f} s',va='center',fontweight='bold')
  quality=[f"{sum(r['correct'] for r in paired[a])}/{sum(r['fields'] for r in paired[a])}" for a in ARMS]
  costs=[st.mean(r['cost_usd'] for r in paired[a]) for a in ARMS]
  time=f'{values[0]:.1f} → {values[1]:.1f} s'
  if any(failures):time+=' (includes failed stops; no speedup claim)'
  lines.append(f'| {NAMES[model]} | {len(rs)}/12 | {len(matched)}/6 | {time} | {quality[0]} → {quality[1]} | ${costs[0]:.4f} → ${costs[1]:.4f} | {failures[0]} / {failures[1]} |')
 else:
  ax.set_xlim(0,1);ax.set_xticks([]);ax.text(.05,.5,'Running — waiting for a matched pair',transform=ax.transAxes,color='#475569')
  lines.append(f'| {NAMES[model]} | {len(rs)}/12 | 0/6 | Pending | Pending | Pending | {failures[0]} / {failures[1]} |')
 if any(failures):ax.text(.02,.02,f'Failed/time-out cases: Pi {failures[0]}, tools {failures[1]}; elapsed time is not success.',transform=ax.transAxes,fontsize=8,color='#b45309')
 ax.set_xlabel('Elapsed seconds (failed stops included if present)')
fig.text(.035,.025,'Development pilot: one run per case/arm. Partial comparisons are explicitly labeled.\nAccuracy includes safe abstention. Failures stay in the results; a fast failed stop is not a speed improvement.',fontsize=10,color='#475569')
fig.savefig(OUT/'model_speed.png',dpi=170,bbox_inches='tight')
svg=OUT/'model_speed.svg';fig.savefig(svg,bbox_inches='tight',metadata={'Date':None});svg.write_text('\n'.join(l.rstrip() for l in svg.read_text().splitlines())+'\n');plt.close(fig)
lines+=['','## Conditions and limitations','','Three form types × two synthetic patients × two arms per model. Same hosted model ID per comparison, temperature zero and low reasoning effort. Shuffled cases; the first portion used three concurrent jobs, then the queue was increased to twelve for the submission deadline. This concurrency change can affect measured latency and is not a controlled speed comparison across models. Within-model bars use the exact same matched cases.','',
'No held-out validation, repetitions, statistical confidence or clinical superiority is established. A partial result can change as more cases finish. If an arm fails or times out, its elapsed time must not be described as successful completion speed. Original DeepSeek [full pilot details](README.md) and [tooling explanation](TOOLING_WRITEUP.md).','',
'[All sanitized run metrics](live_metrics.json) include completed single-arm cases before their counterpart finishes. Patient records, predictions, raw logs, failure messages and answer keys remain local. Receipt hashes identify the local artifacts.','']
(OUT/'LIVE_RESULTS.md').write_text('\n'.join(lines))
print('UPDATED',len(rows),'runs')
