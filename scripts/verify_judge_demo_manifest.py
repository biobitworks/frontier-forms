#!/usr/bin/env python3
"""Replay every published synthetic judge demo asset hash and declared Merkle root."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1]
D=R/'docs/demo'
canon=lambda o:json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
sha=lambda b:hashlib.sha256(b).hexdigest()
def root(items):
 level=[hashlib.sha256(b'\x00'+canon(x)).digest() for x in items]
 if not level:raise AssertionError('EMPTY_MANIFEST')
 while len(level)>1:
  if len(level)%2:level.append(level[-1])
  level=[hashlib.sha256(b'\x01'+level[i]+level[i+1]).digest() for i in range(0,len(level),2)]
 return level[0].hex()
def verify():
 m=json.loads((D/'manifest.json').read_text())
 bad=[];leaves=[]
 for path,v in sorted(m['assets'].items()):
  p=D/path
  if not p.is_file():bad.append((path,'MISSING'));continue
  raw=p.read_bytes()
  if len(raw)!=v['bytes'] or sha(raw)!=v['sha256']:bad.append((path,'BYTE_OR_SHA_DRIFT'))
  leaves.append({'path':path,'bytes':len(raw),'sha256':sha(raw)})
 if bad:raise AssertionError('MANIFEST_INPUT_DRIFT:'+str(bad[:12]))
 receipt=json.loads((D/'MANIFEST_REPAIR_V2.json').read_text())
 if receipt['manifest_sha256']!=sha((D/'manifest.json').read_bytes()):raise AssertionError('REPAIRED_MANIFEST_SHA_CHANGED')
 if receipt['asset_root']!=root(leaves):raise AssertionError('62_LEAF_MERKLE_DRIFT')
 old=(D/'manifest_v1_pre_repair.json').read_bytes()
 if receipt['predecessor_manifest_sha256']!=sha(old):raise AssertionError('PREDECESSOR_MANIFEST_DRIFT')
 return {'status':'PASS','assets':len(leaves),'repaired_annotation_json':receipt['repaired_files'],'asset_root':receipt['asset_root']}
if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
