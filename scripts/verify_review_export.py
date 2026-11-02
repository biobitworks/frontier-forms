#!/usr/bin/env python3
"""Independently replay current and historical public-review Merkle roots."""
from pathlib import Path
import json,hashlib,subprocess
R=Path(__file__).resolve().parent.parent
HISTORICAL_COMMITS={
  'REVIEW-37152dc823a8009f':'bf58691bbf93753a9a63b4722e479d8b044fcb01',
  'REVIEW-513cb1f8e83d0eae':'ee75d57a65ef27ed80811fea0f9c8571ab184ac1',
  # red-team successor fix F-02: pin the Supabase-intake review root to the PR #3 head that created it,
  # otherwise any later edit of README.md etc. reports LEAF_FILE_MISMATCH for an intact commitment.
  'REVIEW-2f1cfafda7de0153':'da953450d33a721682191f77589c275e0b49731c',
}
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
for folder in sorted((R/'evidence/freeze/review_successor').glob('REVIEW-*')):
    m=json.loads((folder/'manifest.json').read_text())
    rows=[json.loads(x) for x in (folder/'leaves.jsonl').read_text().splitlines()]
    assert m['leaf_count']==len(rows) and m['leaf_order']==[r['path'] for r in rows]
    historical=folder.name in HISTORICAL_COMMITS
    for r in rows:
        if historical:
            proc=subprocess.run(['git','show',HISTORICAL_COMMITS[folder.name]+':'+r['path']],
                cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            if proc.returncode:raise RuntimeError('HISTORICAL_FILE_MISSING '+r['path'])
            raw=proc.stdout
        else:
            raw=(R/r['path']).read_bytes()
        if len(raw)!=r['size_bytes'] or sha(raw)!=r['sha256']:
            raise AssertionError('LEAF_FILE_MISMATCH '+r['path'])
    v=[hashlib.sha256(b'\x00'+canon(x)).digest() for x in rows]
    while len(v)>1:
        if len(v)%2:v.append(v[-1])
        v=[hashlib.sha256(b'\x01'+v[i]+v[i+1]).digest() for i in range(0,len(v),2)]
    assert v[0].hex()==m['root']
    assert m['signature']=='NOT_SIGNED' and m['mmr']=='NOT_COMPUTED'
    print('ROOT_VERIFIED',m['root'],'LEAVES',len(rows),
          'SOURCE','HISTORICAL_GIT_COMMIT' if historical else 'CURRENT_FILES')
