#!/usr/bin/env python3
"""Verify frozen public source identities and branch inventory; no scientific claims."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'docs/judges/FINAL_PUBLIC_DATA_COVERAGE_20261102_V1.json'
def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def verify():
    j=json.loads(PATH.read_text())
    assert j['schema']=='frontier-forms.final-public-data-coverage.v1'
    assert j['predecessor_main_sha']=='f10e1d7bb6856c85f9db054d409867ff65922c02'
    pr=j['github_pull_requests']
    assert pr['merged']==60 and pr['closed_without_merge']==4 and pr['open_at_predecessor']==0
    assert pr['total']==pr['merged']+pr['closed_without_merge']
    assert {x['number'] for x in pr['closed_without_merge_prs']}=={1,27,45,55}
    assert len(pr['merged_pr_numbers'])==60
    refs=j['branches_not_ancestor_of_main_at_snapshot']
    assert len(refs)==j['branch_count_not_ancestor_of_main']==13
    assert len({x['ref'] for x in refs})==13
    for path,value in j['public_source_identity_checks'].items():
        file=ROOT/path
        assert file.is_file() and file.stat().st_size==value['size_bytes'],path
        assert sha(path)==value['sha256'],'SOURCE_HASH_DRIFT:'+path
    historical=j['imported_historical_receipt']
    assert sha(historical['path'])==historical['exact_sha256']
    assert json.loads((ROOT/historical['path']).read_text())['new_ci']=='NOT_YET_EXECUTED'
    assert j['restrictions']['scientific_gain_admissions']==0
    assert j['restrictions']['FCAR']=='HOLD'
    assert j['restrictions']['external_hackersquad_submission_receipt']=='UNKNOWN'
    assert j['new_root']=='NOT_COMPUTED' and j['no_model_inference_reperformed']
    for item in refs:
        assert item['status']=='NOT_MERGED_BRANCH_SNAPSHOT_REVIEW_REQUIRED'
        assert len(item['head_sha'])==40
    assert j['status']=='PUBLIC_EVIDENCE_AND_ALL_OPEN_PRS_RECONCILED_NOT_ALL_PRIVATE_OR_BRANCH_BYTES_MERGED'
    assert 'NOT_MERGED' in (ROOT/'README.md').read_text()
    print('FINAL_PUBLIC_DATA_COVERAGE PASS',
          'source_files',len(j['public_source_identity_checks']),
          'public_main_at_cutoff',j['file_inventory_main_predecessor']['total_tracked'],
          'merged_prs',pr['merged'],'closed',pr['closed_without_merge'],
          'unmerged_branch_refs',len(refs),
          'no_scientific_admission',True)
    return j
if __name__=='__main__':verify()
