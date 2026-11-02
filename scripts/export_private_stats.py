#!/usr/bin/env python3
"""Export hashed paired correctness only; NO patient or answer data into public Git."""
import json,sys,collections,hashlib
from pathlib import Path
repo=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(repo/'src'))
from frontier_forms.statistics import admit,binary_confusion

# Fail closed: historical source-root attribution requires frozen *input bytes*,
# not merely stable case keys or self-reported correctness.
EXPECTED_PROJECT_ROOT='9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a'
REQUIRED_FROZEN_INPUTS=(
    'eval/longebench_split_manifest.json',
    'eval/lb_mini_discovery_lfm2-1.2b-longevity-q4km_latest.jsonl',
    'eval/insilico_qwen3_06b_discovery_attempt3.jsonl',
)
def verify_private_export_inputs(src):
    bundle=repo/'evidence/freeze/predecessor'
    sys.path.insert(0,str(repo/'scripts'))
    from verify_predecessor import verify,file_sha
    verified=verify(bundle,None)
    if verified['root']!=EXPECTED_PROJECT_ROOT or verified['root_recomputed']!='PASS':
        raise AssertionError('FROZEN_PROJECT_ROOT_MISMATCH')
    frozen=[json.loads(x) for x in (bundle/'leaves.jsonl').read_text().splitlines() if x.strip()]
    by_path={x['path']:x for x in frozen}
    for rel in REQUIRED_FROZEN_INPUTS:
        expected=by_path.get(rel)
        if expected is None:raise AssertionError('FROZEN_DESCRIPTOR_MISSING '+rel)
        p=src/rel
        if not p.is_file():raise AssertionError('PRIVATE_SOURCE_MISSING '+rel)
        if p.stat().st_size!=expected['size_bytes'] or file_sha(p)!=expected['sha256']:
            raise AssertionError('PRIVATE_SOURCE_HASH_MISMATCH '+rel)
    return EXPECTED_PROJECT_ROOT
def export(src):
    verified_root=verify_private_export_inputs(src)
    e=src/'eval'
    a=[json.loads(s) for s in (e/'lb_mini_discovery_lfm2-1.2b-longevity-q4km_latest.jsonl').read_text().splitlines()]
    b=[json.loads(s) for s in (e/'insilico_qwen3_06b_discovery_attempt3.jsonl').read_text().splitlines()]
    aa={x['row_key_sha256']:x for x in a}
    assert len(aa)==len(a)==len(b)==38
    assert len(set(x['row_key_sha256'] for x in b))==38
    pairs=[]
    for x in b:
        k=x['row_key_sha256'];q=aa[k]
        assert q['task']==x['task'] and q['gold']==x['gold']
        pairs.append({'case_digest_sha256':k,'task':x['task'],
                      'baseline_correct':bool(q['correct']),
                      'challenger_correct':bool(x['correct'])})
    out=repo/'evidence/stats/discovery_pair_flags.jsonl'
    out.write_text(''.join(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n' for x in pairs))
    stat=admit(pairs)
    # No raw case labels exported. Only aggregate confusion matrices per task.
    per={}
    for task in sorted({x['task'] for x in b}):
        old=[{'gold':x['gold'],'pred':x['pred']} for x in a if x['task']==task]
        new=[{'gold':x['gold'],'pred':x['prediction']} for x in b if x['task']==task]
        per[task]={'baseline':binary_confusion(old),'challenger':binary_confusion(new)}
    stat.update({'source':'local source-bound 38-case discovery only',
          'frozen_source_root':verified_root,
          'source_byte_verification':'PASS_3_FROZEN_EVAL_INPUTS',
          'FPR_FDR_by_task':per,'AUROC':'NOT_COMPUTED_NO_CONTINUOUS_SCORES',
          'FIREWORKS':'NOT_TESTED','EHR_OCR':'NOT_TESTED',
          'external_replication':'NOT_TESTED','contamination_control':'NO_GOLD_IN_MODEL_INPUTS'})
    (repo/'evidence/stats/discovery_audit.json').write_text(json.dumps(stat,sort_keys=True,indent=2)+'\n')
    print('EXPORTED_38_SOURCE_BOUND_BOOLEAN_PAIRS',stat['p_mcnemar_exact_two_sided'],stat['ci_delta_bootstrap_stratified_95'],stat['promotion'])
if __name__=='__main__': export(Path(sys.argv[1]))
