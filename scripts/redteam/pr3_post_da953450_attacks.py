"""Re-run red-team attacks A1, A2 and A4 against a checkout of PR #3 head da51622 (works on copies only).
Usage: git worktree add /tmp/pr3 da51622 && python3 -I scripts/redteam/pr3_post_da953450_attacks.py /tmp/pr3
"""
import json,shutil,subprocess,sys,tempfile,pathlib
WT=pathlib.Path(sys.argv[1])
out={}
def copytree():
    t=pathlib.Path(tempfile.mkdtemp());d=t/'wt'
    shutil.copytree(WT,d,ignore=shutil.ignore_patterns('.git'));
    # verifier uses git show for historical; keep a git dir
    subprocess.run(['git','init','-q'],cwd=d);return d
# A1 on new review successor (95 leaves) using verify_review_export logic, current-files branch
d=copytree()
f=d/'evidence/freeze/review_successor/REVIEW-90761061e69fffe2'
for other in (d/'evidence/freeze/review_successor').glob('REVIEW-*'):
    if other.name!=f.name: shutil.rmtree(other)
rows=(f/'leaves.jsonl').read_text().splitlines()
m=json.loads((f/'manifest.json').read_text())
rows.append(rows[-1]); m['leaf_count']+=1; m['leaf_order'].append(m['leaf_order'][-1])
m['parent_project_root']='f'*64; m['parent_repo_commit']='0'*40   # A2 at the same time
(f/'leaves.jsonl').write_text('\n'.join(rows)+'\n'); (f/'manifest.json').write_text(json.dumps(m))
p=subprocess.run([sys.executable,'scripts/verify_review_export.py'],cwd=d,capture_output=True,text=True)
out['A1_A2_review_successor_90761061']={'leaves':len(rows),'forged_parent':True,'rc':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()[-200:]}
# A1 on predecessor bundle through the new exporter gate's verify()
sys.path.insert(0,str(WT/'scripts'))
from verify_predecessor import verify
d2=copytree();b=d2/'evidence/freeze/predecessor'
L=(b/'leaves.jsonl').read_text().splitlines();M=json.loads((b/'manifest.json').read_text())
L.append(L[-1]);M['leaf_count']+=1;M['leaf_order'].append(M['leaf_order'][-1]);M['parent']='forged-parent'
(b/'leaves.jsonl').write_text('\n'.join(L)+'\n');(b/'manifest.json').write_text(json.dumps(M))
try:
    r=verify(b,None);out['A1_A2_predecessor_verify']={'result':'ACCEPTED','root':r['root'],'leaves':r['leaves'],'parent_echoed':r['parent_snapshot']}
except Exception as e: out['A1_A2_predecessor_verify']={'result':'REJECTED','err':str(e)}
# A4 dangling edges in predecessor edge leaf
P=[json.loads(x) for x in (WT/'evidence/freeze/predecessor/leaves.jsonl').read_text().splitlines() if x.strip()]
edges=P[-1]['edges']; ids=set()
for x in P: ids.update(str(v) for k,v in x.items() if k in ('id','path','fco_id'))
ids.update(str(x.get('path')) for x in P)
def ends(e):
    if isinstance(e,dict): return [e.get(k) for k in ('from','to','source','target','src','dst') if k in e]
    return list(e[::2]) if isinstance(e,list) else []
dang=sorted({str(t) for e in edges for t in ends(e) if t is not None and str(t) not in ids})
out['A4_edge_endpoints']={'edges':len(edges),'endpoints_not_a_leaf_path':dang[:20],'n':len(dang),'checker_in_verify':'edge digest only'}
print(json.dumps(out,indent=1))
