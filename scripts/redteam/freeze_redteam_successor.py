#!/usr/bin/env python3
"""Append-only Merkle successor for the Claude red-team lane.

Differences from the predecessor's freeze_review_export.py, each motivated by a red-team finding:
  F-01  leaf 0 is a context leaf that binds leaf_count, parent roots and the Git commit, so the duplicate-last-odd
        collision (appending a copy of the last leaf) can no longer keep the root while changing the count.
  F-02  the manifest records the Git commit whose bytes were hashed so a verifier never depends on the working tree.
Scheme otherwise identical: sha256(00||canonical_leaf); sha256(01||left||right); duplicate-last-odd.
Creates evidence/breakpoints/REDTEAM-<root16>/ with leaves.jsonl + manifest.json; refuses to overwrite.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent.parent
PARENT_ROOT = '2f1cfafda7de0153fc932c52f36ce49d7ea25307b218ba392bae80b8d72c95a2'
ORIGIN_ROOT = '9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a'
PATTERNS = ['README.md', 'README_AI.md', 'scripts/redteam/*.py', 'src/frontier_forms/redteam_stats.py', 'src/frontier_forms/fhir_draft.py',
            'tests/test_redteam_*.py', 'tests/test_fhir_draft.py', 'notebooks/1*_redteam_*.ipynb',
            'docs/reviews/CLAUDE_REDTEAM_REPORT.md', 'docs/architecture/LEAF_GAIN_ATTRIBUTION.md', 'experiments/CLAUDE_LAB_NOTEBOOK.md',
            'evidence/redteam/*.json', 'evidence/redteam/*.jsonl', 'evidence/redteam/*.txt', 'evidence/redteam/lanes/*',
            'evidence/notebook_runs_redteam_v1/*', 'scripts/verify_review_export.py']


def canon(o): return json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
def sha(b): return hashlib.sha256(b).hexdigest()
def leaf(o): return hashlib.sha256(b'\x00' + canon(o)).digest()


def root(leaves):
    v = list(leaves)
    while len(v) > 1:
        if len(v) % 2:
            v.append(v[-1])
        v = [hashlib.sha256(b'\x01' + v[i] + v[i + 1]).digest() for i in range(0, len(v), 2)]
    return v[0].hex()


def build(commit: str):
    paths = sorted({p for pat in PATTERNS for p in R.glob(pat) if p.is_file() and 'evidence/breakpoints' not in p.as_posix()})
    files = [{'path': p.relative_to(R).as_posix(), 'size_bytes': len(p.read_bytes()), 'sha256': sha(p.read_bytes())} for p in paths]
    context = {'schema': 'fco.redteam_successor.context.v1', 'leaf_count': len(files) + 1, 'parent_project_root': PARENT_ROOT,
               'origin_project_root': ORIGIN_ROOT, 'hashed_at_git_commit': commit, 'lane': 'redteam/claude-fcg-local-ablation-20261102'}
    rows = [{'path': 'REDTEAM_CONTEXT', 'context': context, 'sha256': sha(canon(context))}] + files
    return rows, root([leaf(x) for x in rows])


def verify(folder: Path, commit: str | None = None):
    m = json.loads((folder / 'manifest.json').read_text())
    rows = [json.loads(x) for x in (folder / 'leaves.jsonl').read_text().splitlines()]
    assert m['leaf_count'] == len(rows) == rows[0]['context']['leaf_count'], 'LEAF_COUNT_NOT_BOUND'
    assert [r['path'] for r in rows] == m['leaf_order'], 'LEAF_ORDER'
    assert root([leaf(x) for x in rows]) == m['root'], 'ROOT_MISMATCH'
    commit = commit or m['hashed_at_git_commit']
    for r in rows[1:]:
        proc = subprocess.run(['git', 'show', f"{commit}:{r['path']}"], cwd=R, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode:
            raise AssertionError('HISTORICAL_FILE_MISSING ' + r['path'])
        if sha(proc.stdout) != r['sha256'] or len(proc.stdout) != r['size_bytes']:
            raise AssertionError('LEAF_FILE_MISMATCH ' + r['path'])
    return m['root'], len(rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--commit', help='Git commit whose tree is being frozen (required for --write)')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--verify', type=Path)
    a = ap.parse_args()
    if a.verify:
        r, n = verify(a.verify)
        print('REDTEAM_SUCCESSOR_VERIFIED', r, 'LEAVES', n, 'SOURCE', 'HISTORICAL_GIT_COMMIT')
        sys.exit(0)
    commit = a.commit or subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=R, stdout=subprocess.PIPE, text=True).stdout.strip()
    rows, rt = build(commit)
    print('REDTEAM_SUCCESSOR_ROOT', rt, 'LEAVES', len(rows), 'COMMIT', commit)
    if a.write:
        out = R / 'evidence/breakpoints' / ('REDTEAM-' + rt[:16])
        out.mkdir(parents=True, exist_ok=False)
        (out / 'leaves.jsonl').write_bytes(b''.join(canon(x) + b'\n' for x in rows))
        manifest = {'schema': 'fco.redteam_successor.v1', 'root': rt, 'leaf_count': len(rows), 'leaf_order': [x['path'] for x in rows],
                    'parent_project_root': PARENT_ROOT, 'origin_project_root': ORIGIN_ROOT, 'parent_repo_commit': 'da953450d33a721682191f77589c275e0b49731c',
                    'hashed_at_git_commit': commit, 'construction': 'sha256(00||canonical_leaf);sha256(01||left||right);duplicate_last;leaf0_binds_count',
                    'signature': 'NOT_SIGNED', 'mmr': 'NOT_COMPUTED', 'raw_source_export': 'NOT_AUTHORIZED', 'evaluation': 'SEE_CLAUDE_REDTEAM_REPORT'}
        (out / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
        print('WROTE', out)
