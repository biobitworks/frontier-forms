"""Render horizontal baseline-vs-improved graphs from published aggregate receipts. No inference."""
from pathlib import Path
import csv
import json
import statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'charts'
rows=json.loads((OUT/'paired_pilot.json').read_text())['runs']
ARMS=['pi+browser-tools','frontier-tools']
LABELS=['Baseline: model + Pi','Improved: model + our tools']
COLORS=['#64748b','#059669']
model={r['model'] for r in rows}
assert len(model)==1
cases={r['case'] for r in rows}
assert len(rows)==2*len(cases)==12
assert all(sum(r['case']==c and r['arm']==a for r in rows)==1 for c in cases for a in ARMS)
assert all(not r['failed'] and not r['timed_out'] for r in rows), 'Include failure accounting before publishing changed runs'
by={a:[r for r in rows if r['arm']==a] for a in ARMS}
summary={a:{'runs':len(rs),'median_seconds':st.median(r['seconds'] for r in rs),
 'correct':sum(r['correct'] for r in rs),'fields':sum(r['fields'] for r in rs),
 'mean_cost_usd':st.mean(r['cost_usd'] for r in rs),'mean_model_calls':st.mean(r['model_calls'] for r in rs),
 'mean_tokens':st.mean(r['input']+r['cached']+r['output'] for r in rs),
 'full_forms':sum(r['full_form'] for r in rs),'failed':sum(r['failed'] for r in rs),
 'fabricated':sum(r['fabricated'] for r in rs),'unsafe':sum(r['unsafe'] for r in rs),
 'closed_correct':sum(r['sensitivity']['closed']['correct'] for r in rs),
 'closed_fields':sum(r['sensitivity']['closed']['fields'] for r in rs),
 'open_correct':sum(r['sensitivity']['open']['correct'] for r in rs),
 'open_fields':sum(r['sensitivity']['open']['fields'] for r in rs)} for a,rs in by.items()}
with (OUT/'summary.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['arm',*next(iter(summary.values())).keys()],lineterminator='\n');w.writeheader()
 for a,s in summary.items():w.writerow({'arm':a,**s})
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'svg.hashsalt':'frontier-pilot'})

def save(fig,name):
 fig.savefig(OUT/f'{name}.png',dpi=180,bbox_inches='tight')
 p=OUT/f'{name}.svg';fig.savefig(p,bbox_inches='tight',metadata={'Date':None});p.write_text('\n'.join(l.rstrip() for l in p.read_text().splitlines())+'\n');plt.close(fig)

def bars(ax,values,title,formatter,limit=None):
 ax.barh([1,0],values,color=COLORS,height=.52)
 ax.set_yticks([1,0],LABELS);ax.tick_params(axis='y',length=0)
 ax.set_title(title,loc='left',fontsize=13,pad=14)
 ax.set_xlim(0,limit or max(values)*1.33)
 for y,v in zip([1,0],values):ax.text(v+ax.get_xlim()[1]*.025,y,formatter(v),va='center',fontweight='bold')
 ax.set_ylim(-.65,1.65)

fig,axes=plt.subplots(2,2,figsize=(14,8));fig.subplots_adjust(wspace=.72,hspace=.65,left=.19,right=.94,bottom=.13,top=.79)
fig.suptitle('Same model. Same medical forms. Different harness.',x=.04,ha='left',fontsize=21,fontweight='bold',y=.98)
fig.text(.04,.90,'DeepSeek V4.1 Flash • real Pi + browser-tools vs Frontier Forms tools',fontsize=13,color='#475569')
fig.text(.04,.86,'3 synthetic form types × 2 patients • 6 matched cases per arm • one run per case',fontsize=11,color='#475569')
bars(axes[0,0],[summary[a]['median_seconds'] for a in ARMS],'Completion time — lower is better',lambda v:f'{v:.1f} s')
bars(axes[0,1],[100*summary[a]['correct']/summary[a]['fields'] for a in ARMS],'Correct fields — higher is better',lambda v:f'{v:.1f}%',115)
bars(axes[1,0],[summary[a]['mean_cost_usd'] for a in ARMS],'Estimated API cost / form — lower is better',lambda v:f'${v:.4f}')
bars(axes[1,1],[summary[a]['mean_model_calls'] for a in ARMS],'Model calls / form — lower is better',lambda v:f'{v:.1f}')
fig.text(.04,.035,'Development pilot, not held-out validation. Time = median; cost/calls = mean. Correct fields include safe abstention.\nNeutral scoring excludes defensible No/blank answers for absent facts. API cost uses configured token rates.',fontsize=10,color='#475569')
save(fig,'baseline_vs_improved')

forms=[('primary_care_registration','Primary care registration'),('urgent_care_history','Urgent care history'),('insurance_update','Insurance update')]
fig,axes=plt.subplots(3,1,figsize=(10,8));fig.subplots_adjust(left=.30,bottom=.11,top=.85,hspace=.7)
fig.suptitle('Time to complete each medical form',x=.04,ha='left',fontsize=20,fontweight='bold',y=.98)
fig.text(.04,.92,'Same DeepSeek model • median of the same two patients • lower is better',color='#475569')
for ax,(key,label) in zip(axes,forms):
 vals=[st.median(r['seconds'] for r in by[a] if r['form']==key) for a in ARMS]
 bars(ax,vals,label,lambda v:f'{v:.1f} s',max(r['seconds'] for r in rows)*1.1)
fig.text(.04,.025,'Small development pilot: one run per patient/form/arm. No clinical or statistical superiority claim.',fontsize=10,color='#475569')
save(fig,'time_by_form')
a,b=[summary[x] for x in ARMS]
text=f'''# Real Pi baseline versus Frontier Forms

## Explain it in 20 seconds

> We used the same DeepSeek model on the same six synthetic medical-form cases. With Pi, the model operates the browser through general tools. With our harness, code handles form inspection, record retrieval, validation and page filling, and the model maps questions to answers. Median completion time fell from {a['median_seconds']:.1f} to {b['median_seconds']:.1f} seconds ({a['median_seconds']/b['median_seconds']:.1f}× faster). Field scores were {a['correct']}/{a['fields']} versus {b['correct']}/{b['fields']}. This is a small development pilot, not a clinical validation.

![Baseline versus improved](baseline_vs_improved.png)

![Time per form](time_by_form.png)

## Exact setup

- Baseline: Pi 1.5.0 with the browser-tools skill and DeepSeek `deepseek-v4p1-flash` on Fireworks.
- Improved: Frontier Forms `packages/fill-tools`, using the same model/provider, temperature 0 and low reasoning effort.
- Same 3 form types, same 2 synthetic patients, same browser-state scorer and task restrictions; 12 runs total, 6 per arm. Shuffled order, up to 3 concurrent runs. One patient was used during development; this is not a held-out result.
- Timing covers harness execution from launch through completion, before the common scoring step. It excludes browser startup. Summaries use median time and mean cost/calls/tokens.
- Failures: {a['failed']}/6 baseline, {b['failed']}/6 improved. Full-form successes: {a['full_forms']}/6 versus {b['full_forms']}/6. Fabricated fields: {a['fabricated']} versus {b['fabricated']}; unsafe fields: {a['unsafe']} versus {b['unsafe']}.
- Mean tokens per form (uncached input + cached input + output): {a['mean_tokens']:,.0f} versus {b['mean_tokens']:,.0f}. Estimated API spend is based on configured token rates, not an invoice.

## Accuracy and the absent-fact rule

The main score is neutral: unsupported Yes is wrong; defensible No/blank for an absent fact is excluded. Both arms use identical scoring. Missing/conflicted/expired facts, signatures and accidental submission are checked separately. Correct-field percentages include safe abstention; they are not the fraction of fields physically filled.

| Policy | Pi baseline | Our harness + tools |
|---|---:|---:|
| Neutral | {a['correct']}/{a['fields']} | {b['correct']}/{b['fields']} |
| Closed: absent means No | {a['closed_correct']}/{a['closed_fields']} | {b['closed_correct']}/{b['closed_fields']} |
| Open: absent means unknown | {a['open_correct']}/{a['open_fields']} | {b['open_correct']}/{b['open_fields']} |

## What changed

Our harness gives the model relevant record facts and structured questions in parallel batches. Code then validates proposed answers, applies them through browser controls, and verifies page state. Pi uses general browser operations and a longer agent conversation. These are two whole-system configurations; the pilot does not isolate each mechanism's contribution.

No medical accuracy superiority, fine-tuning gain or improvement-over-time claim is established. There is one run per case/arm, no confidence interval or independent replication, and no model weight digest from the hosted provider. Historical job-form charts are [separate](../job_form_charts/README.md); they are not the Pi baseline.

## Data and reproduction

[Sanitized paired metrics](paired_pilot.json) contain only numeric outcomes, opaque matched-case IDs and local artifact hashes; patient records, predictions, answer keys and transcripts stay private. [Summary CSV](summary.csv). Rebuild with `python bench/plot_pi_comparison.py` (matplotlib required). The underlying pilot is `bench/harness/pilot.py`; raw runs require the private frozen synthetic export and API access. Source snapshots and receipt hashes identify this pilot's provenance; they do not independently prove model outputs.
'''
(OUT/'README.md').write_text(text)
print(text.split('## Exact setup')[0])
