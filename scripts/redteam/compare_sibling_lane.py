#!/usr/bin/env python3
"""Case-level cross-check against the concurrent sibling red-team lane (different code, same frozen cases).

Sibling: origin/redteam/claude-fcg-local-ablation-20261102 (Claude Opus 5.5 session), public bits under redteam/results/.
This lane: evidence/redteam/lanes/*_PUBLIC.jsonl. Both key cases by sha256(canon([hf_rev, lb_id, prompt])).
Agreement here is a code-level replication (same hosts, same weights, temperature 0), NOT an independent population.
Writes evidence/redteam/sibling_lane_crosscheck.json. Read-only on the sibling branch.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent.parent
SIB = 'origin/redteam/claude-fcg-local-ablation-20261102'
ARM_MAP = {'direct': 'B0_baseline', 'fco': 'C1_fco_projection', 'fcg': 'C2_full_fcg', 'inject_direct': 'C6_prompt_injection', 'forged_noverify': 'C4_corrupt_leaf'}
LANE_MAP = {'L0': 'S-L0', 'L1': 'S-L1', 'L3': 'P-L3'}


def git_show(path):
    p = subprocess.run(['git', 'show', f'{SIB}:{path}'], cwd=R, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout.decode() if p.returncode == 0 else None


def main():
    head = subprocess.run(['git', 'rev-parse', SIB], cwd=R, stdout=subprocess.PIPE, text=True).stdout.strip()
    out = {'schema': 'redteam.sibling_crosscheck.v1', 'sibling_branch': SIB, 'sibling_head': head, 'comparisons': {}, 'note': 'code-level replication only'}
    for mine_tag, sib_lane in LANE_MAP.items():
        for split in ('discovery', 'heldout'):
            txt = git_show(f'redteam/results/bits_{sib_lane}_{split}.jsonl')
            mine_files = list((R / 'evidence/redteam/lanes').glob(f'{mine_tag}_*_{split}_PUBLIC.jsonl'))
            if txt is None or not mine_files:
                out['comparisons'][f'{mine_tag}:{split}'] = {'status': 'NOT_COMPARABLE', 'sibling_present': txt is not None, 'mine_present': bool(mine_files)}
                continue
            sib = {}
            for line in txt.splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                sib.setdefault(r['arm'], {})[r['row_key_sha256']] = r
            mine = {}
            for x in mine_files[0].read_text().splitlines():
                if x.strip():
                    r = json.loads(x); mine[r.get('key') or r['case_digest_sha256']] = r
            comp = {}
            for my_arm, sib_arm in ARM_MAP.items():
                if sib_arm not in sib:
                    comp[f'{my_arm}~{sib_arm}'] = 'SIBLING_ARM_MISSING'
                    continue
                keys = sorted(set(mine) & set(sib[sib_arm]))
                agree = sum(1 for k in keys if bool(mine[k]['arms'][my_arm]['strict_correct']) == bool(sib[sib_arm][k]['correct_strict']))
                comp[f'{my_arm}~{sib_arm}'] = {'n_common': len(keys), 'strict_correct_agreement': agree,
                                               'mine_correct': sum(1 for k in keys if mine[k]['arms'][my_arm]['strict_correct']),
                                               'sibling_correct': sum(1 for k in keys if sib[sib_arm][k]['correct_strict']),
                                               'sibling_prompt_tokens': sum(sib[sib_arm][k].get('prompt_tokens') or 0 for k in keys),
                                               'mine_prompt_tokens': sum(mine[k]['arms'][my_arm].get('prompt_tokens') or 0 for k in keys),
                                               'caveat': 'arms are similar in intent but NOT byte-identical prompts (sibling C2 carries proof siblings; this lane does not)' if my_arm != 'direct' else 'byte-identical frozen messages expected'}
            out['comparisons'][f'{mine_tag}:{split}'] = comp
    (R / 'evidence/redteam/sibling_lane_crosscheck.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(json.dumps(out, indent=1)[:4000])


if __name__ == '__main__':
    main()
