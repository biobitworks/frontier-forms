#!/usr/bin/env python3
"""Independent reconstruction of existing ASI 15-leaf Merkle predecessor.
Hashes prove bytes, NOT correctness or attribution. No writes to source.
"""
from __future__ import annotations
import argparse,hashlib,json,pathlib
def canon(x):
    return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def root_of(leaves):
    level=[bytes.fromhex(sha(b'\x00'+canon(x))) for x in leaves]
    while len(level)>1:
        if len(level)%2:level.append(level[-1])
        level=[hashlib.sha256(b'\x01'+level[i]+level[i+1]).digest()
               for i in range(0,len(level),2)]
    return level[0].hex()
def verify(bundle,source=None):
    path=bundle/'manifest.json'
    m=json.loads(path.read_text())
    leaves=[json.loads(s) for s in (bundle/'leaves.jsonl').read_text().splitlines() if s.strip()]
    got=root_of(leaves)
    if got!=m['root'] or len(leaves)!=m['leaf_count']:
        raise AssertionError(f'ROOT_MISMATCH expected={m["root"]} got={got}')
    if [x['path'] for x in leaves]!=m['leaf_order']:
        raise AssertionError('LEAF_ORDER_MISMATCH')
    context=leaves[0]['context']
    assert sha(canon(context))==leaves[0]['sha256']
    assert sha(canon(leaves[-1]['edges']))==leaves[-1]['sha256']
    files=[]
    for x in leaves[1:-1]:
        rel=x['path']
        p=source/rel if source else None
        status='NOT_TESTED_SOURCE_UNAVAILABLE' if source is None else 'MISSING'
        if p is not None and p.is_file():
            gotsha=file_sha(p)
            status='PASS' if gotsha==x['sha256'] and p.stat().st_size==x['size_bytes'] else 'FAIL'
        files.append({'path':rel,'expected_sha256':x['sha256'],'status':status})
    result={
      'schema':'fco.predecessor_verification.v1','root':got,'root_recomputed':'PASS',
      'leaves':len(leaves),'leaf_order':'PASS','context_digest':'PASS','edge_digest':'PASS',
      'parent_snapshot':m.get('parent'),'source_files':files,
      'source_sha_verification':'PASS' if all(x['status']=='PASS' for x in files) else
       ('NOT_TESTED' if not source else 'FAIL'),
      'signature':'NOT_SIGNED','mmr':'NOT_COMPUTED','meaning':'INTEGRITY_ONLY_NOT_TRUTH',
      'source_path_in_receipt':'REDACTED'
    }
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--bundle',required=True,type=pathlib.Path)
    ap.add_argument('--source',type=pathlib.Path)
    ap.add_argument('--receipt',type=pathlib.Path)
    a=ap.parse_args();res=verify(a.bundle,a.source)
    text=json.dumps(res,sort_keys=True,indent=2)+'\n'
    if a.receipt:a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(text)
    print(text)
    if res['root_recomputed']!='PASS' or res['source_sha_verification']=='FAIL':raise SystemExit(2)
