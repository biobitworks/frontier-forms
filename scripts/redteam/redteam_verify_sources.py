#!/usr/bin/env python3
"""Claude red-team: INDEPENDENT replay of the frozen FCO/FCG commitments.

This is deliberately NOT the predecessor's verifier (scripts/verify_predecessor.py,
scripts/freeze_dataset.py). It re-implements canonicalization, leaf/node domain
separation, odd-leaf duplication and inclusion-proof checking from the written
scheme only, then runs negative controls against the real frozen data.

Runs on the machine that holds the original source bytes (magicSTUDIObox). Emits a
public-safe receipt: no prompts, no gold answers, no oracle hashes, no raw rows.

Hashes prove identity/integrity only. They do not prove clinical truth, causality or
model competence.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, platform, sys, time
from pathlib import Path

EXPECTED = {
    'root_728': '5f9a7e51f1ee03d70d34e99358fe14230efa396f7fd851df21f424e6843f61b1',
    'root_15': '9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a',
    'split_manifest_sha256': '46c48f08add45a2bc5941fba2ddca682e0ac136d718232aafa5c011438f92007',
    'snapshot': 'LN-MINI-ec719d04c3707ca1cb',
    'hf_revision': '0b6bab2ac5de29b0ad4fcbf062022a6b1c742e9f',
}
TASKS = ('LB-0307', 'LB-0309', 'LB-0314', 'LB-0315')


def canon(o) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def sha_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def leaf(o, prefix=b'\x00') -> bytes:
    return hashlib.sha256(prefix + canon(o)).digest()


def node(l: bytes, r: bytes, prefix=b'\x01') -> bytes:
    return hashlib.sha256(prefix + l + r).digest()


def root(leaves, dup_odd=True, prefix=b'\x01') -> bytes:
    level = list(leaves)
    if not level:
        raise ValueError('EMPTY')
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1] if dup_odd else b'\x00' * 32)
        level = [node(level[i], level[i + 1], prefix) for i in range(0, len(level), 2)]
    return level[0]


def proof_ok(leaf_bytes: bytes, siblings, expected_root: bytes) -> bool:
    cur = leaf_bytes
    for s in siblings:
        sib = bytes.fromhex(s['sibling'])
        cur = node(sib, cur) if s['side'] == 'left' else node(cur, sib)
    return cur == expected_root


def file_sha(p: Path):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(16 << 20), b''):
            h.update(chunk)
    return h.hexdigest(), p.stat().st_size


def jsonl(p: Path):
    return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]


def check_728(source: Path, out: dict):
    snap = source / 'custody/snapshots' / EXPECTED['snapshot']
    src_fco = json.loads((snap / 'dataset_source_fco.json').read_text())
    inputs = jsonl(snap / 'inputs.jsonl')
    proofs = jsonl(snap / 'proofs.jsonl')
    edges = jsonl(snap / 'fcg_edges.jsonl')
    manifest = json.loads((snap / 'manifest.json').read_text())
    leaves = [leaf(src_fco)] + [leaf(r['input']) for r in inputs]
    got = root(leaves).hex()
    r = {
        'inputs': len(inputs), 'proofs': len(proofs), 'edges': len(edges),
        'manifest_root': manifest['public_merkle_root'],
        'recomputed_root': got,
        'root_match_manifest': got == manifest['public_merkle_root'],
        'root_match_expected': got == EXPECTED['root_728'],
        'source_fco_id_match': ('fco:' + sha_hex(canon(src_fco))) == manifest['source_fco_id'],
        'source_fco_raw_sha_match_manifest': src_fco['raw_sha256'] == manifest['source_sha256'],
    }
    # per-input identity, leaf hash, proof, edge
    bad_id = bad_leaf = bad_proof = bad_index = 0
    for i, (rec, pf) in enumerate(zip(inputs, proofs)):
        if rec['input_fco_id'] != 'fco:' + sha_hex(canon(rec['input'])):
            bad_id += 1
        if pf['leaf_hash'] != leaves[i + 1].hex() or pf['case_id'] != rec['case_id']:
            bad_leaf += 1
        if pf['index_in_tree'] != i + 1:
            bad_index += 1
        if not proof_ok(leaves[i + 1], pf['siblings'], bytes.fromhex(got)):
            bad_proof += 1
    edge_ok = all(e['rel'] == 'DERIVED_INPUT_AT' and e['src'] == manifest['source_fco_id']
                  and e['dst'] == inputs[k]['input_fco_id'] and e['context']['row_index'] == k
                  for k, e in enumerate(edges)) and len(edges) == len(inputs)
    # oracle leakage in public inputs
    roles = collections.Counter(m.get('role') for rec in inputs for m in rec['input']['messages'])
    leak_keys = sum(1 for rec in inputs if any(k in rec['input'] for k in ('answer', 'gold', 'oracle')))
    vis_ok = all(rec['input'].get('gold_visibility') == 'PROHIBITED_IN_MODEL_INPUT' for rec in inputs)
    r.update({
        'input_fco_id_mismatches': bad_id, 'leaf_hash_mismatches': bad_leaf,
        'proof_index_mismatches': bad_index, 'inclusion_proof_failures': bad_proof,
        'edges_consistent': edge_ok,
        'public_input_roles': dict(roles),
        'assistant_role_in_public_inputs': roles.get('assistant', 0),
        'answer_like_keys_in_public_inputs': leak_keys,
        'gold_visibility_flag_all_prohibited': vis_ok,
    })
    # negative controls on copies
    neg = {}
    mut = list(leaves); mut[5] = leaf({'forged': True})
    neg['corrupt_leaf_changes_root'] = root(mut).hex() != got
    neg['corrupt_leaf_breaks_its_proof'] = not proof_ok(mut[5], proofs[4]['siblings'], bytes.fromhex(got))
    swp = list(leaves); swp[3], swp[4] = swp[4], swp[3]
    neg['reorder_changes_root'] = root(swp).hex() != got
    neg['remove_leaf_changes_root'] = root(leaves[:-1]).hex() != got
    neg['leaf_prefix_swap_changes_root'] = root([leaf(src_fco, b'\x01')] + [leaf(x['input'], b'\x01') for x in inputs]).hex() != got
    neg['node_prefix_swap_changes_root'] = root(leaves, prefix=b'\x00').hex() != got
    neg['zero_pad_instead_of_dup_changes_root'] = root(leaves, dup_odd=False).hex() != got
    # known weakness of duplicate-last-odd trees: appending a copy of the last leaf
    # yields the SAME root. Leaf count must therefore be bound outside the root.
    neg['duplicate_last_leaf_appended_same_root'] = root(leaves + [leaves[-1]]).hex() == got
    neg['manifest_binds_leaf_count'] = manifest.get('rows') == len(inputs)
    r['negative_controls'] = neg
    out['snapshot_728'] = r
    return inputs, leaves, got


def check_15(source: Path, out: dict):
    d = source / 'custody/project_freezes/ASI-FRONTIER-9e4d4df8aa7a887e'
    man = json.loads((d / 'manifest.json').read_text())
    rows = jsonl(d / 'leaves.jsonl')
    leaves = [leaf(x) for x in rows]
    got = root(leaves).hex()
    files = []
    t0 = time.monotonic()
    for x in rows[1:-1]:
        p = source / x['path']
        if p.is_file():
            s, n = file_sha(p)
            files.append({'path': x['path'], 'sha_match': s == x['sha256'], 'size_match': n == x['size_bytes']})
        else:
            files.append({'path': x['path'], 'sha_match': None, 'size_match': None, 'missing': True})
    out['project_15'] = {
        'leaf_count': len(rows), 'manifest_root': man['root'], 'recomputed_root': got,
        'root_match_manifest': got == man['root'], 'root_match_expected': got == EXPECTED['root_15'],
        'leaf_order_match': [x['path'] for x in rows] == man['leaf_order'],
        'context_leaf_sha_match': sha_hex(canon(rows[0]['context'])) == rows[0]['sha256'],
        'edges_leaf_sha_match': sha_hex(canon(rows[-1]['edges'])) == rows[-1]['sha256'],
        'parent_root_declared': man['parent']['root'],
        'parent_root_matches_728': man['parent']['root'] == EXPECTED['root_728'],
        'source_files': files,
        'all_source_bytes_match': all(f['sha_match'] and f['size_match'] for f in files),
        'rehash_seconds': round(time.monotonic() - t0, 3),
        'local_leaves_sha256': sha_hex((d / 'leaves.jsonl').read_bytes()),
        'local_manifest_sha256': sha_hex((d / 'manifest.json').read_bytes()),
        'negative_controls': {
            'corrupt_leaf_changes_root': root([leaf(dict(x, sha256='0' * 64)) if i == 2 else l for i, (x, l) in enumerate(zip(rows, leaves))]).hex() != got,
            'duplicate_last_leaf_appended_same_root': root(leaves + [leaves[-1]]).hex() == got,
        },
    }


def check_pairs(source: Path, inputs, pairs_path: Path, out: dict):
    split_p = source / 'eval/longebench_split_manifest.json'
    split = json.loads(split_p.read_text())
    r = {'split_manifest_sha256_match': sha_hex(split_p.read_bytes()) == EXPECTED['split_manifest_sha256']}
    # key = sha256(canon([REV, lb_id, last_user_prompt])) recomputed from PUBLIC inputs
    key_to = {}
    for rec in inputs:
        inp = rec['input']
        prompt = inp['messages'][-1]['content']
        k = sha_hex(canon([EXPECTED['hf_revision'], inp['context']['lb_id'], prompt]))
        key_to[k] = (rec['case_id'], inp['context']['lb_id'], rec['index'])
    parts = split['task_partitions']
    allk = {}
    for t, p in parts.items():
        for name, ks in p.items():
            for k in ks:
                allk.setdefault(k, []).append((t, name))
    r['split_keys_total'] = len(allk)
    r['split_keys_assigned_once'] = all(len(v) == 1 for v in allk.values())
    r['split_keys_resolve_to_public_input'] = sum(1 for k in allk if k in key_to)
    r['split_keys_task_matches_input'] = sum(1 for k, v in allk.items() if k in key_to and key_to[k][1] == v[0][0])
    r['partition_sizes'] = {t: {n: len(v) for n, v in p.items()} for t, p in parts.items()}
    pairs = jsonl(pairs_path)
    r['pairs'] = len(pairs)
    r['pairs_resolve_to_public_input'] = sum(1 for x in pairs if x['case_digest_sha256'] in key_to)
    r['pairs_in_discovery_partition'] = sum(1 for x in pairs if allk.get(x['case_digest_sha256'], [('', '')])[0][1] == 'discovery')
    r['pairs_task_matches_input'] = sum(1 for x in pairs if key_to.get(x['case_digest_sha256'], (None, None))[1] == x['task'])
    # recompute correctness from local eval receipts (gold stays local)
    a = {x['row_key_sha256']: x for x in jsonl(source / 'eval/lb_mini_discovery_lfm2-1.2b-longevity-q4km_latest.jsonl')}
    b = {x['row_key_sha256']: x for x in jsonl(source / 'eval/insilico_qwen3_06b_discovery_attempt3.jsonl')}
    r['eval_keys_identical'] = set(a) == set(b) == {x['case_digest_sha256'] for x in pairs}
    r['eval_status_all_executed'] = all(x['status'] == 'EXECUTED' for x in list(a.values()) + list(b.values()))
    r['baseline_unparsed_outputs'] = sum(1 for x in a.values() if x.get('pred') is None)
    r['challenger_unparsed_outputs'] = sum(1 for x in b.values() if x.get('prediction') is None)
    r['gold_agrees_between_eval_files'] = all(a[k]['gold'] == b[k]['gold'] for k in a)
    # gold in eval files equals private oracle for that case (local-only check)
    oracles = {o['case_id']: o for o in jsonl(source / '.private/snapshots' / EXPECTED['snapshot'] / 'oracles.jsonl')}
    r['eval_gold_matches_private_oracle'] = all(
        oracles[key_to[k][0]]['answer'].strip() == a[k]['gold'] for k in a if k in key_to)
    rec_a = {k: (x['pred'] == x['gold']) for k, x in a.items()}
    rec_b = {k: (x['prediction'] == x['gold']) for k, x in b.items()}
    r['recomputed_correct_matches_stored_flag'] = all(rec_a[k] == a[k]['correct'] and rec_b[k] == b[k]['correct'] for k in a)
    r['pair_flags_match_recomputed'] = all(
        rec_a[x['case_digest_sha256']] == x['baseline_correct'] and rec_b[x['case_digest_sha256']] == x['challenger_correct'] for x in pairs)
    n_b = sum(1 for k in a if rec_a[k] and not rec_b[k]); n_c = sum(1 for k in a if rec_b[k] and not rec_a[k])
    r['recomputed_table'] = {'n': len(a), 'baseline_correct': sum(rec_a.values()), 'challenger_correct': sum(rec_b.values()),
                             'baseline_only': n_b, 'challenger_only': n_c}
    import math
    nn = n_b + n_c
    r['recomputed_mcnemar_exact_two_sided_p'] = min(1.0, 2 * sum(math.comb(nn, k) for k in range(min(n_b, n_c) + 1)) / 2 ** nn) if nn else 1.0
    out['pairs_38'] = r
    return split


def regenerate_split(source: Path, split, out: dict):
    try:
        import pyarrow.parquet as pq
    except Exception as e:  # pragma: no cover
        out['split_regeneration'] = {'status': 'NOT_TESTED_NO_PYARROW', 'error': type(e).__name__}
        return
    raw = source / 'datasets/longebench/mini/eval-00000-of-00001.parquet'
    rows = pq.read_table(raw).to_pylist()
    by = collections.defaultdict(list)
    for r in rows:
        if r['lb_id'] not in TASKS:
            continue
        assert r['messages'][-1]['role'] == 'assistant'
        prompt = r['messages'][-2]['content']
        by[r['lb_id']].append(sha_hex(canon([EXPECTED['hf_revision'], r['lb_id'], prompt])))
    parts = {}
    for t, ks in sorted(by.items()):
        s = sorted(ks); n = len(s)
        d = s[:min(10, n // 3)]; h = s[min(10, n // 3):min(20, 2 * n // 3)]; rsv = s[min(20, 2 * n // 3):]
        parts[t] = {'discovery': d, 'heldout': h, 'reserve': rsv}
    regen = {'schema': 'longebench_mini_split.v1', 'source_dataset': 'insilicomedicine/longebench',
             'source_revision': EXPECTED['hf_revision'], 'source_parquet_sha256': sha_hex(raw.read_bytes()),
             'task_partitions': parts}
    regen_bytes = json.dumps(regen, sort_keys=True, indent=2).encode() + b'\n'
    out['split_regeneration'] = {
        'status': 'EXECUTED', 'rows_in_parquet': len(rows),
        'task_rows': {t: len(v) for t, v in by.items()},
        'structural_match': regen['task_partitions'] == split['task_partitions'],
        'regenerated_sha256': sha_hex(regen_bytes),
        'byte_identical_to_frozen_manifest': sha_hex(regen_bytes) == EXPECTED['split_manifest_sha256'],
        'deterministic_rule': 'sorted by key; discovery=first min(10,n//3); heldout next; reserve rest',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True, type=Path)
    ap.add_argument('--pairs', required=True, type=Path, help='evidence/stats/discovery_pair_flags.jsonl')
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    out = {'schema': 'redteam.independent_replay.v1', 'verifier': 'claude-redteam independent reimplementation',
           'host': platform.node(), 'python': sys.version.split()[0], 'platform': platform.platform(),
           'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'source_path': 'REDACTED', 'meaning': 'INTEGRITY_ONLY_NOT_TRUTH', 'signature': 'NOT_SIGNED', 'mmr': 'NOT_COMPUTED'}
    inputs, leaves, got = check_728(a.source, out)
    check_15(a.source, out)
    split = check_pairs(a.source, inputs, a.pairs, out)
    regenerate_split(a.source, split, out)
    s7, s15, pr = out['snapshot_728'], out['project_15'], out['pairs_38']
    out['status'] = {
        'root_728': 'PASS' if s7['root_match_expected'] and s7['inclusion_proof_failures'] == 0 else 'FAIL',
        'root_15': 'PASS' if s15['root_match_expected'] and s15['all_source_bytes_match'] else 'FAIL',
        'oracle_isolation_public_inputs': 'PASS' if s7['assistant_role_in_public_inputs'] == 0 and s7['answer_like_keys_in_public_inputs'] == 0 else 'FAIL',
        'pair_binding_38': 'PASS' if pr['pairs_resolve_to_public_input'] == 38 and pr['pair_flags_match_recomputed'] and pr['pairs_in_discovery_partition'] == 38 else 'FAIL',
        'split_regeneration': out['split_regeneration']['status'] if out['split_regeneration']['status'] != 'EXECUTED' else ('PASS' if out['split_regeneration']['byte_identical_to_frozen_manifest'] else 'FAIL'),
        'duplicate_last_leaf_collision_present': s7['negative_controls']['duplicate_last_leaf_appended_same_root'],
    }
    out['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, sort_keys=True, indent=2) + '\n')
    print(json.dumps(out['status'], indent=2))
    if any(v == 'FAIL' for v in out['status'].values()):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
