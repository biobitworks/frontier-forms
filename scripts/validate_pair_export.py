#!/usr/bin/env python3
"""Verifies public-safe discovery pairs are bounded by the original frozen split."""
from pathlib import Path
import json,hashlib,sys
def check(base):
    base=Path(base)
    split_path=base/'evidence/freeze/longebench_split_manifest.json'
    expected='46c48f08add45a2bc5941fba2ddca682e0ac136d718232aafa5c011438f92007'
    if hashlib.sha256(split_path.read_bytes()).hexdigest()!=expected:
        raise AssertionError('SPLIT_MANIFEST_SHA_MISMATCH')
    split=json.loads(split_path.read_text())
    discovery={x for task in split['task_partitions'].values() for x in task['discovery']}
    heldout={x for task in split['task_partitions'].values() for x in task['heldout']}
    records=[json.loads(x) for x in (base/'evidence/stats/discovery_pair_flags.jsonl').read_text().splitlines()]
    keys=[x['case_digest_sha256'] for x in records]
    if len(keys)!=38 or len(set(keys))!=38:raise AssertionError('PAIR_COUNT_OR_DUPLICATES')
    if not set(keys).issubset(discovery) or (set(keys)&heldout):
        raise AssertionError('NON_DISCOVERY_OR_LEAKED_HELDOUT_CASE')
    for x in records:
        task=x['task']
        if task not in split['task_partitions'] or x['case_digest_sha256'] not in split['task_partitions'][task]['discovery']:
            raise AssertionError('WRONG_TASK_OR_SPLIT_BINDING')
    return {'state':'PASS','pairs':len(keys),'split_manifest_sha256':expected,
            'heldout_overlap':0,'independent_model_oracle_check':'NOT_TESTED_FROM_METADATA_ONLY'}
if __name__=='__main__':
    print(json.dumps(check(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent),indent=2))
