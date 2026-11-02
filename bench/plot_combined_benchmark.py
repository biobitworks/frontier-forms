"""One figure: models stacked vertically; runtime, accuracy and cost side by side."""
from pathlib import Path
import json,statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'charts'
rows=json.loads((OUT/'live_metrics.json').read_text())['runs']
MODELS=[('deepseek-v4p1-flash','DeepSeek V4.1 Flash'),('glm-5p3','GLM 5.3'),('qwen3p8-max','Qwen Max'),('gpt-oss-120b','GPT-OSS 120B')]
ARMS=['pi+browser-tools','frontier-tools']
COLORS=['#64748b','#059669']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.hashsalt':'frontier-combined'})
fig,axes=plt.subplots(4,3,figsize=(15,10.5))
fig.subplots_adjust(left=.19,right=.96,top=.81,bottom=.11,wspace=.35,hspace=.8)
fig.suptitle('Same model. Same forms. Pi vs our tooling.',x=.035,y=.98,ha='left',fontsize=23,fontweight='bold')
fig.text(.035,.925,'48-run synthetic medical-form pilot • 6 matched cases per arm for each model',fontsize=12,color='#475569')
fig.legend(handles=[Patch(color=COLORS[0],label='Baseline: model + Pi'),Patch(color=COLORS[1],label='Same model + our tooling')],loc='upper left',bbox_to_anchor=(.03,.90),ncol=2,frameon=False,fontsize=12)
headings=['Runtime (seconds) ↓','Correct fields (%) ↑','Estimated API cost / form ($) ↓']
for c,title in enumerate(headings):axes[0,c].set_title(title,loc='left',fontsize=13,fontweight='bold',pad=24)
for i,(model,label) in enumerate(MODELS):
 rs=[r for r in rows if r['model']==model]
 cases=sorted({r['case'] for r in rs});lookup={(r['case'],r['arm']):r for r in rs}
 assert len(cases)==6 and len(rs)==12 and all((case,a) in lookup for case in cases for a in ARMS)
 by={a:[lookup[(case,a)] for case in cases] for a in ARMS}
 assert not any(r['failed'] or r['timed_out'] for r in rs)
 vals=[[st.median(r['seconds'] for r in by[a]) for a in ARMS],
       [100*sum(r['correct'] for r in by[a])/sum(r['fields'] for r in by[a]) for a in ARMS],
       [st.mean(r['cost_usd'] for r in by[a]) for a in ARMS]]
 for c in range(3):
  ax=axes[i,c];ax.barh([1,0],vals[c],height=.53,color=COLORS)
  ax.set_xlim(0,[120,120,.25][c]);ax.set_ylim(-.6,1.6);ax.set_yticks([])
  ax.set_xticks([[0,40,80,120],[0,50,100],[0,.1,.2]][c]);ax.tick_params(axis='x',labelsize=9,colors='#64748b',length=0)
  for side in ['left','top','right']:ax.spines[side].set_visible(False)
  ax.spines['bottom'].set_color('#cbd5e1')
  for y,v in zip([1,0],vals[c]):
   text=f'{v:.1f} s' if c==0 else f'{v:.1f}%' if c==1 else f'${v:.4f}'
   ax.text(v+ax.get_xlim()[1]*.025,y,text,va='center',fontsize=11,fontweight='bold')
 pos=axes[i,0].get_position()
 fig.text(.035,pos.y0+pos.height*.52,label,ha='left',va='center',fontsize=12,fontweight='bold')
fig.text(.035,.035,'Runtime = median time until stopping; accuracy = correct fields / scored fields; cost = mean estimated token cost.\nDevelopment pilot, not clinical validation. GLM trades some accuracy for speed. GPT-OSS’s short Pi runtime reflects poor form completion (19/121).',fontsize=10,color='#475569')
fig.savefig(OUT/'combined_benchmark.png',dpi=180,bbox_inches='tight')
p=OUT/'combined_benchmark.svg';fig.savefig(p,bbox_inches='tight',metadata={'Date':None});p.write_text('\n'.join(l.rstrip() for l in p.read_text().splitlines())+'\n')
plt.close(fig)
print('Combined chart written')
