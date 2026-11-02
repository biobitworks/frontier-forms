#!/usr/bin/env python3
"""Independent successor verifier: rehash all listed files and rebuild root."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent.parent
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
for folder in sorted((R/'evidence/freeze/review_successor').glob('REVIEW-*')):
    m=json.loads((folder/'manifest.json').read_bytes())
    leaves=[json.loads(s) for s in (folder/'leaves.jsonl').read_text().splitlines()]
    if len(leaves)!=m['leaf_count'] or [x['path'] for x in leaves]!=m['leaf_order']:
        raise AssertionError('ORDER_OR_COUNT')
    for x in leaves:
        raw=(R/x['path']).read_bytes()
        if len(raw)!=x['size_bytes'] or sha(raw)!=x['sha256']:
            raise AssertionError('FILE_CHANGED: '+x['path'])
    nodes=[bytes.fromhex(sha(b'\x00'+canon(x))) for x in leaves]
    while len(nodes)>1:
        if len(nodes)%2:nodes.extend(nodes[-1:])
        nodes=[hashlib.sha256(b'\x01'+nodes[i]+nodes[i+1]).digest()
               for i in range(0,len(nodes),2)]
    if nodes[0].hex()!=m['root']:
        raise AssertionError('MERKLE_ROOT_MISMATCH')
    assert m['signed']=='NOT_SIGNED' and m['mmr']=='NOT_COMPUTED'
    print('PUBLIC_REVIEW_ROOT_PASS',m['root'],'LEAVES',len(leaves),'RAW_SOURCES','NOT_REEXPORTED')
