"""Rebuild submission charts from saved aggregate trials; no model calls.
Run with Python plus matplotlib: python bench/plot_results.py
"""
from pathlib import Path
import csv
import hashlib
import json
import statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'results_ablation.jsonl'
OUT = ROOT / 'charts'
OUT.mkdir(exist_ok=True)
rows = [json.loads(line) for line in SOURCE.read_text().splitlines()]
runs = [r for r in rows if 'trial' in r]
assert len(runs) == 105 and all(not r['failed'] and not r['submitted'] for r in runs)
MODELS = [('glm-5p3-fast', 'GLM 5.3 Fast'), ('glm-5p3-flash', 'GLM 5.3 Flash'), ('minimax-m3p1-flash', 'MiniMax Flash')]
SETUPS = [('Agent loop', 'toolloop', 'json', 'each'), ('Parallel groups', 'batched', 'json', 'each'),
          ('+ Compact replies', 'batched', 'lines', 'each'), ('Parallel + one write', 'batched', 'json', 'all'),
          ('All improvements', 'batched', 'lines', 'all')]
COLORS = ['#61758a', '#21a179', '#277da8']
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':11, 'axes.spines.top':False, 'axes.spines.right':False,
                     'axes.titleweight':'bold', 'figure.facecolor':'#ffffff', 'axes.facecolor':'#ffffff'})

def select(model, setup):
    _, mode, reply, writes = setup
    found = [r for r in runs if r['form']=='b' and r['model'].rsplit('/',1)[-1]==model
             and r['mode']==mode and r['reply']==reply and r['writes']==writes]
    assert len(found)==5, (model,setup,len(found))
    return found

def median(model, setup, key='total_s'):
    return st.median(r[key] for r in select(model,setup))

def finish(fig, name, footer):
    fig.text(.08,.025,footer,fontsize=9,color='#475569')
    fig.savefig(OUT / f'{name}.png', dpi=180, bbox_inches='tight')
    svg = OUT / f'{name}.svg'
    fig.savefig(svg, bbox_inches='tight', metadata={'Date': None})
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    plt.close(fig)

summary=[]
for model,label in MODELS:
    for setup in SETUPS:
        rs=select(model,setup); times=[r['total_s'] for r in rs]; correct=[int(r['correct'].split('/')[0]) for r in rs]
        summary.append(dict(model=model,setup=setup[0],trials=5,median_seconds=st.median(times),min_seconds=min(times),max_seconds=max(times),
                            median_correct=st.median(correct),min_correct=min(correct),max_correct=max(correct),fields=65))
with (OUT/'summary.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]),lineterminator='\n');w.writeheader();w.writerows(summary)

x=np.arange(3); width=.34
fig,ax=plt.subplots(figsize=(10,5.5));fig.subplots_adjust(bottom=.19,top=.80)
for offset,setup,color in [(-width/2,SETUPS[0],COLORS[0]),(width/2,SETUPS[-1],COLORS[1])]:
    vals=[median(m,setup) for m,_ in MODELS]
    bars=ax.bar(x+offset,vals,width,label=setup[0],color=color)
    ax.bar_label(bars,labels=[f'{v:.2f}s' for v in vals],padding=4)
ax.set_xticks(x,[label for _,label in MODELS]);ax.set_ylabel('Median completion time (seconds)');ax.set_ylim(0,20)
ax.legend(frameon=False,loc='upper left');ax.set_title('Same model, less waiting',loc='left',pad=40)
fig.text(.08,.85,'65-question job form • five trials per setup • lower is better',color='#475569')
finish(fig,'speed','Warm-run pilot on plain HTML. Baseline is a simplified agent loop, not Pi. No medical speed claim.')

fig,ax=plt.subplots(figsize=(10,5.5));fig.subplots_adjust(bottom=.19,top=.80)
for offset,setup,color in [(-width/2,SETUPS[0],COLORS[0]),(width/2,SETUPS[-1],COLORS[1])]:
    med=[];lo=[];hi=[]
    for model,_ in MODELS:
        vals=[int(r['correct'].split('/')[0]) for r in select(model,setup)];v=st.median(vals)
        med.append(v);lo.append(v-min(vals));hi.append(max(vals)-v)
    bars=ax.bar(x+offset,med,width,label=setup[0],color=color,yerr=[lo,hi],capsize=5)
    ax.bar_label(bars,labels=[f'{v:g}/65' for v in med],padding=8)
ax.set_xticks(x,[label for _,label in MODELS]);ax.set_ylabel('Correct fields out of 65');ax.set_ylim(0,73)
ax.legend(frameon=False,loc='upper right',bbox_to_anchor=(1,1.18));ax.set_title('Speed improves; accuracy stays broadly similar',loc='left',pad=40)
fig.text(.08,.85,'Median correct fields • whiskers show observed min–max across five trials',color='#475569')
finish(fig,'accuracy','Corrected page-state scoring. Whiskers are trial ranges, not confidence intervals. No accuracy superiority claim.')

fig,ax=plt.subplots(figsize=(11,6));fig.subplots_adjust(left=.25,bottom=.17,top=.83)
y=np.arange(5);h=.23
for i,(model,label) in enumerate(MODELS):
    vals=[median(model,s) for s in SETUPS]
    bars=ax.barh(y+(i-1)*h,vals,h,label=label,color=COLORS[i])
    ax.bar_label(bars,labels=[f'{v:.2f}s' for v in vals],padding=4,fontsize=9)
ax.set_yticks(y,[s[0] for s in SETUPS]);ax.invert_yaxis();ax.set_xlim(0,20);ax.set_xlabel('Median completion time (seconds)')
ax.set_title('What each optimization contributes',loc='left',pad=40);ax.legend(frameon=False,loc='lower right')
fig.text(.25,.88,'65-question job form • five trials per configuration',color='#475569')
finish(fig,'ablation','Measured configurations, not additive causal estimates. One browser write produces the clearest GLM speed gain.')

sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
lines=['# Benchmark charts and submission explanation','','## The 20-second explanation','',
'> We speed up the work around the model: ask independent questions in parallel, request shorter answers, and fill the page in one browser operation. On our 65-question job-form pilot, the same GLM model went from 6.08 seconds to 1.99 seconds—about three times faster—with broadly similar accuracy. We are now testing this approach on synthetic medical forms; medical superiority has not been established.','',
'## Measured speed improvement','','| Same model | Agent loop | Optimized harness | Speedup | Time reduction |','|---|---:|---:|---:|---:|']
for model,label in MODELS:
    a,b=median(model,SETUPS[0]),median(model,SETUPS[-1]);lines.append(f'| {label} | {a:.2f} s | {b:.2f} s | {a/b:.2f}× | {(1-b/a)*100:.1f}% |')
lines += ['', '![Completion time](speed.png)','','![Accuracy](accuracy.png)','','![Individual configurations](ablation.png)','',
'## Why it helps','','1. **Ask together:** split independent questions into six concurrent groups, reducing serial waiting.',
'2. **Say less:** use compact answer lines instead of verbose JSON. This pilot omits evidence/confidence in compact output; medical answers need that information restored.',
'3. **Write together:** apply answers in one browser operation and read controls back, falling back to slower field filling when needed. No fallback was needed on these plain HTML forms.','',
'## What the numbers establish','','The charts use corrected saved aggregate results, not newly executed model runs. There are five trials for every plotted model/configuration. The full source contains 105 trials across both form sizes; these charts show the 75 trials on the 65-question form. Times are medians from warm runs; latency uncertainty and independent replication have not been established. Accuracy uses actual page state. The baseline is a simplified three-tool agent loop, not real Pi. These are harness speed measurements, not evidence that one model is intrinsically better, that FCG causes an improvement, or that medical accuracy improved.','',
'Keep the medical lane separate: two preliminary Pi dev-form fills exist locally; there is no completed medical tools-versus-Pi comparison, fine-tuning result, or improvement-over-time study. The 280 oracle checks verify the form/scoring fixtures; they are not 280 successful model runs.','',
'## Reproduce the charts','','`python bench/plot_results.py` requires matplotlib and numpy; it makes no model calls. See [aggregate trial source](../results_ablation.jsonl), [plotted summary CSV](summary.csv), and [benchmark methodology](../README.md). PNG and SVG versions are provided for slides.','',f'Source SHA-256: `{sha}`.','']
(OUT/'README.md').write_text('\n'.join(lines))
print('Wrote three charts (PNG + SVG), summary CSV and submission explanation.')
