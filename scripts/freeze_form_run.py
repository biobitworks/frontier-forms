#!/usr/bin/env python3
"""Append-only Merkle breakpoint for independently verifiable rendered synthetic forms."""
import argparse,hashlib,json
from pathlib import Path
from verify_freeze import canonical,root,sha,file_sha
PARENT="9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a"
def freeze_forms(source,archive):
    source=Path(source);archive=Path(archive)
    source_receipt=json.loads((source/'receipt.json').read_text())
    items=[json.loads(x) for x in (source/'inputs.jsonl').read_text().splitlines()]
    if len(items)!=source_receipt['case_count']:raise ValueError('ROW_COUNT')
    if sha((source/'inputs.jsonl').read_bytes())!=source_receipt['public_inputs_sha256']:
        raise ValueError('INPUT_LIST_CHANGED')
    private_path=source/'.private/oracle.jsonl'
    if file_sha(private_path)!=source_receipt['private_oracle_sha256']:
        raise ValueError('ORACLE_CHANGED')
    leaves=[{'type':'FORM_RUN_CONTEXT','source_sha256':source_receipt['source_sha256'],
        'parent_project_root':PARENT,'recipe':source_receipt['render_recipe']}]
    seen=set()
    for row in items:
        k=row['case_id']
        if k in seen:raise ValueError('DUPLICATE_CASE')
        seen.add(k)
        p=source/row['png_relative_path']
        if not p.is_file() or file_sha(p)!=row['png_sha256']:
            raise ValueError('PNG_HASH_MISMATCH:'+k)
        leaves.append({'type':'FORM_IMAGE_FCO','case_id':k,
            'input_fco_id':row['input_fco_id'],
            'occurrence_id':row['occurrence_id'],
            'png_sha256':row['png_sha256']})
    computed=root(leaves)
    dest=archive/('SYNFORM-'+computed[:16])
    receipt={'schema':'asi.forms.merkle.v1','root':computed,
      'parent_project_root':PARENT,'ordered_leaves':len(leaves),
      'form_count':len(items),'source_sha256':source_receipt['source_sha256'],
      'public_input_listing_sha256':source_receipt['public_inputs_sha256'],
      'private_oracle_sha256':source_receipt['private_oracle_sha256'],
      'scheme':'sha256(00||compact_sorted_json); sha256(01||left||right); odd_duplicate',
      'source_state':'SYNTHETIC_REPRODUCIBLE','ocr_state':'NOT_TESTED',
      'clinical_state':'NOT_TESTED','signed':'NOT_SIGNED','MMR':'NOT_COMPUTED',
      'public_export':'NOT_AUTHORIZED'}
    if dest.exists():
        if json.loads((dest/'manifest.json').read_text())!=receipt:
            raise ValueError('EXISTING_FREEZE_MISMATCH')
    else:
        dest.mkdir(parents=True)
        (dest/'manifest.json').write_bytes(canonical(receipt)+b'\n')
        (dest/'leaves.jsonl').write_bytes(b''.join(canonical(x)+b'\n' for x in leaves))
    replay=[json.loads(x) for x in (dest/'leaves.jsonl').read_text().splitlines()]
    assert root(replay)==computed
    return receipt
if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True);ap.add_argument('--archive',required=True)
    a=ap.parse_args()
    print(json.dumps(freeze_forms(a.source,a.archive),sort_keys=True))
