from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent.parent
patterns=[
 'README.md','.gitignore','requirements-notebooks.txt',
 'src/frontier_forms/*.py','scripts/*.py','tests/*.py','notebooks/*.ipynb',
 'docs/**/*.md','experiments/*.md','.planning/phases/*.md','.gsigmad/*.md',
 '.github/workflows/*.yml','lean/*.lean',
 'evidence/freeze/predecessor/*','evidence/freeze/longebench_split_manifest.json',
 'evidence/stats/*.json','evidence/stats/*.jsonl',
 'evidence/receipts/*.json','evidence/receipts/*.txt',
 'evidence/notebook_runs_v1/*.ipynb','evidence/notebook_runs_v1/*.json',
 'evidence/notebook_runs_v2_prekeyfix/*.ipynb','evidence/notebook_runs_v2_prekeyfix/*.json',
 'evidence/notebook_runs_v3/*.ipynb','evidence/notebook_runs_v3/*.json']
paths=sorted({p for pattern in patterns for p in R.glob(pattern) if p.is_file()})
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
leaves=[{'path':p.relative_to(R).as_posix(),'size_bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for p in paths]
v=[bytes.fromhex(sha(b'\x00'+canon(x))) for x in leaves]
while len(v)>1:
    if len(v)%2:v.append(v[-1])
    v=[hashlib.sha256(b'\x01'+v[i]+v[i+1]).digest() for i in range(0,len(v),2)]
root=v[0].hex()
out=R/'evidence/freeze/review_successor'/('REVIEW-'+root[:16])
out.mkdir(parents=True,exist_ok=False)
(out/'leaves.jsonl').write_bytes(b''.join(canon(x)+b'\n' for x in leaves))
manifest={'schema':'fco.review_successor.v1','root':root,'leaf_count':len(leaves),
 'leaf_order':[x['path'] for x in leaves],
 'parent_project_root':'37152dc823a8009fc8d7a7a2b7abaf819fa00e6bc3377b2b2ea1f50cfe7641e7',
 'origin_project_root':'9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a',
 'parent_repo_commit':'bf58691bbf93753a9a63b4722e479d8b044fcb01',
 'construction':'sha256(00||canonical_leaf);sha256(01||left_bytes||right_bytes);duplicate_last',
 'signature':'NOT_SIGNED','mmr':'NOT_COMPUTED','raw_source_export':'NOT_AUTHORIZED',
 'evaluation':'DISCOVERY_NEGATIVE','fireworks':'NOT_TESTED'}
(out/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
print('SUCCESSOR_ROOT',root,'LEAVES',len(leaves))
