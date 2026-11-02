"""Model-by-model speed chart from the sanitized real-Pi paired pilot."""
from pathlib import Path
import json
import statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'charts/paired_pilot.json').read_text())['runs']
models=sorted({r['model'] for r in rows})
fig,axes=plt.subplots(len(models),1,figsize=(10,3.9*len(models)),squeeze=False)
fig.subplots_adjust(left=.33,right=.85,top=.70,bottom=.23,hspace=.7)
fig.suptitle('Faster form completion with our tooling layer',x=.035,y=.98,ha='left',fontsize=19,fontweight='bold')
fig.text(.035,.84,'Same model + same six synthetic medical-form cases • median time • lower is better',fontsize=11,color='#475569')
for ax,model in zip(axes[:,0],models):
    arms=['pi+browser-tools','frontier-tools']
    selected={a:[r for r in rows if r['model']==model and r['arm']==a] for a in arms}
    assert all(len(rs)==6 for rs in selected.values())
    assert all(not r['failed'] and not r['timed_out'] for rs in selected.values() for r in rs)
    med=[statistics.median(r['seconds'] for r in selected[a]) for a in arms]
    ax.barh([1,0],med,color=['#64748b','#059669'],height=.53)
    ax.set_yticks([1,0],['Baseline: model + Pi','Same model + our tooling'])
    ax.tick_params(axis='y',length=0)
    ax.set_xlim(0,max(med)*1.22);ax.set_ylim(-.6,1.6)
    ax.set_xlabel('Completion time (seconds)')
    for y,v in zip([1,0],med):ax.text(v+1.8,y,f'{v:.1f} s',va='center',fontweight='bold',fontsize=14)
    ax.set_title('DeepSeek V4.1 Flash',loc='left',fontweight='bold',fontsize=15,pad=16)
    for side in ['left','right','top']:ax.spines[side].set_visible(False)
    fig.text(.84,.67,f'{med[0]/med[1]:.1f}× faster\n{(1-med[1]/med[0])*100:.0f}% less time',ha='center',va='center',fontsize=13,fontweight='bold',color='#047857')
fig.text(.035,.04,'12-run development pilot: 3 forms × 2 patients × 2 harnesses, one run per case.\nBoth scored 119/121 fields correctly. Only one model has completed this real-Pi comparison.',fontsize=10,color='#475569')
out=ROOT/'charts/model_speed.png';fig.savefig(out,dpi=190,bbox_inches='tight')
p=ROOT/'charts/model_speed.svg';fig.savefig(p,bbox_inches='tight',metadata={'Date':None});p.write_text('\n'.join(l.rstrip() for l in p.read_text().splitlines())+'\n')
print(out)
