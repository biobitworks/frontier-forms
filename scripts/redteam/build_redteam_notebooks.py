#!/usr/bin/env python3
"""Generate the executable Claude red-team notebooks (10-13). Every notebook follows the ten-section contract:
requirements/hypothesis, input+license+hashes, frozen settings, deterministic preprocessing, model/harness execution
(replayed from receipts; no inference inside the notebook), analysis/statistics, negative controls, outputs+SHA-256,
FCO/FCG dependency changes, observed outcomes/failures/limitations/claim ceiling.
"""
from pathlib import Path
import hashlib, json
R = Path(__file__).resolve().parent.parent.parent


def md(s): return {"cell_type": "markdown", "id": hashlib.sha256(("md:" + s).encode()).hexdigest()[:12], "metadata": {}, "source": s}
def code(s): return {"cell_type": "code", "id": hashlib.sha256(("code:" + s).encode()).hexdigest()[:12], "execution_count": None, "metadata": {}, "outputs": [], "source": s}


def nb(name, title, sections, cells):
    intro = f"# {title}\n\n" + "\n".join(f"## {k}\n{v}\n" for k, v in sections.items())
    n = {"cells": [md(intro)] + cells, "metadata": {"kernelspec": {"display_name": "FrontierForms Evidence Python", "language": "python", "name": "frontierforms-evidence"},
         "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    (R / 'notebooks' / name).write_text(json.dumps(n, indent=1) + "\n")
    print('WROTE', name)


COMMON = """import json, hashlib, sys
from pathlib import Path
import os
R = Path.cwd(); sys.path.insert(0, str(R / 'src')); sys.path.insert(0, str(R / 'scripts/redteam')); sys.path.insert(0, str(R / 'scripts'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jsonl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
OUT = Path(os.environ.get('REDTEAM_RUN_DIR', str(R / 'evidence/notebook_runs_redteam_v1'))) / 'outputs'; OUT.mkdir(parents=True, exist_ok=True)
def emit(name, obj):
    p = OUT / name; p.write_text(json.dumps(obj, sort_keys=True, indent=2) + '\\n'); print('OUTPUT', name, sha(p)); return p
"""

CEILING = ("Notebook PASS verifies the local replay only. It never upgrades NOT_TESTED, BLOCKED or NEGATIVE states, and it "
           "never attributes a causal gain to a hash, leaf or edge: hashes bind bytes, controlled interventions bind effects.")

# ---------------------------------------------------------------- EXP-010 independent replay
nb("10_redteam_independent_replay.ipynb", "EXP-010 (red-team): independent Merkle replay and negative controls",
   {"1 Requirements and predeclared hypothesis": "H0: predecessor roots are reproducible with independent code; H1: at least one structural weakness exists in the duplicate-last-odd scheme. Python 3.12+, no network.",
    "2 Input source, license, hashes": "evidence/freeze/predecessor/* (metadata only, CC BY-NC source stays off-repo), evidence/redteam/independent_replay_magicstudiobox.json (receipt of the on-host run).",
    "3 Frozen settings": "scheme sha256(00||canonical_leaf); sha256(01||L||R); duplicate-last-odd; canonical JSON sort_keys, compact, ensure_ascii=False.",
    "4 Deterministic preprocessing": "none beyond canonical JSON.",
    "5 Model/harness execution": "none (integrity only).",
    "6 Analysis": "root recomputation, proof round trip, mutation matrix.",
    "7 Negative controls": "corrupt, reorder, remove, prefix swap, zero pad, duplicate-last collision.",
    "8 Outputs": "exp010_replay.json with SHA-256.",
    "9 FCO/FCG dependency changes": "none; adds a verified receipt leaf to the red-team successor.",
    "10 Claim ceiling": CEILING},
   [code(COMMON + """from redteam_verify_sources import leaf, root, proof_ok, canon, sha_hex
rows = jsonl(R / 'evidence/freeze/predecessor/leaves.jsonl'); man = json.loads((R / 'evidence/freeze/predecessor/manifest.json').read_text())
leaves = [leaf(x) for x in rows]; got = root(leaves).hex()
assert got == man['root'] == '9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a'
assert len(rows) == man['leaf_count'] == 15
host = json.loads((R / 'evidence/redteam/independent_replay_magicstudiobox.json').read_text())
assert host['status']['root_728'] == 'PASS' and host['status']['root_15'] == 'PASS' and host['snapshot_728']['inclusion_proof_failures'] == 0
neg = {'corrupt': root(leaves[:3] + [leaf({'x': 1})] + leaves[4:]).hex() != got, 'reorder': root([leaves[1], leaves[0]] + leaves[2:]).hex() != got,
       'remove': root(leaves[:-1]).hex() != got, 'prefix_swap': root([leaf(x, b'\\x01') for x in rows]).hex() != got,
       'zero_pad': root(leaves, dup_odd=False).hex() != got, 'duplicate_last_same_root': root(leaves + [leaves[-1]]).hex() == got}
assert all(neg.values())
res = {'root_15_recomputed': got, 'host_receipt_status': host['status'], 'negative_controls': neg,
       'finding_F01': 'duplicate-last-odd: appending a copy of the last leaf keeps the root; leaf_count must be bound outside the root (it is, unsigned)',
       'claim': 'INTEGRITY_ONLY_NOT_TRUTH'}
emit('exp010_replay.json', res); print(json.dumps(res, indent=2))""")])

# ---------------------------------------------------------------- EXP-011 lane statistics
nb("11_redteam_local_lanes_stats.ipynb", "EXP-011 (red-team): local lanes, FCO/FCG context, antigentic admission — matched statistics",
   {"1 Requirements and predeclared hypothesis": "H1-H6 as written in experiments/CLAUDE_LAB_NOTEBOOK.md R02 before heldout results were read. Alpha 0.05, exact two-sided McNemar, 10,000 stratified paired bootstrap replicates (numpy PCG64 seed 20261102), Holm over the predeclared heldout primary family.",
    "2 Input source, license, hashes": "evidence/redteam/lanes/*_PUBLIC.jsonl (hashed case keys + booleans; LongevityBench CC BY-NC source and gold stay on magicSTUDIObox), *_META.json run receipts, evidence/freeze/longebench_split_manifest.json (sha 46c48f08...).",
    "3 Frozen settings": "temperature 0, seed 20261102, num_predict 16, num_ctx 4096; Insilico greedy float32 MPS; model digests in META.",
    "4 Deterministic preprocessing": "keys validated against the frozen partition; duplicates/split mismatch/oracle fields fail closed.",
    "5 Model/harness execution": "replayed from receipts produced on magicSTUDIObox by scripts/redteam/redteam_local_lanes.py and redteam_insilico_lane.py; no inference here.",
    "6 Analysis": "paired tables, McNemar, bootstrap, Holm; selective metrics (coverage, false admission, admitted-injected); token/latency totals.",
    "7 Negative controls": "forged_verify and edge_removed must be 100% ABSTAIN with zero model calls; loader rejects tampered exports.",
    "8 Outputs": "exp011_lane_stats.json, exp011_attribution_rows.json.",
    "9 FCO/FCG dependency changes": "adds EXECUTED edges MODEL_EVAL_OF (frozen cases -> lane results) and HARNESS_ABLATION_OF; no predecessor leaf changes.",
    "10 Claim ceiling": CEILING + " n=38/39 per split: power to detect small effects is low; a null is not evidence of equivalence."},
   [code(COMMON + """from frontier_forms.redteam_stats import (load_public_lane, arm_flags, compare, holm, selective_metrics, base_metrics, admission_rule, injection_metrics)
split_m = json.loads((R / 'evidence/freeze/longebench_split_manifest.json').read_text())
allowed = {s: {k for t, p in split_m['task_partitions'].items() for k in p[s]} for s in ('discovery', 'heldout')}
strata = {k: t for t, p in split_m['task_partitions'].items() for s in ('discovery', 'heldout') for k in p[s]}
LANES = R / 'evidence/redteam/lanes'
runs = {}
for meta in sorted(LANES.glob('*_META.json')):
    m = json.loads(meta.read_text()); tag = m['tag']
    if tag in ('smoke', 'smoke2') or 'forms12' in meta.name: continue
    pub = meta.with_name(meta.name.replace('_META.json', '_PUBLIC.jsonl'))
    rows = load_public_lane(pub, m['split'], allowed[m['split']])
    assert len(rows) == len(allowed[m['split']]) == m['cases'], (meta.name, len(rows))
    runs[(tag, m['split'])] = {'meta': m, 'rows': rows}
print('RUNS', sorted(runs))
out = {'per_arm': {}, 'comparisons': {}, 'integrity': {}, 'replay': {}}
BASE_ARMS = ['direct', 'fco', 'fcg', 'inject_direct', 'forged_noverify']
ADM_ARMS = ['antigence_verdict', 'antigence_swap', 'antigence_full', 'fcg_antigence_verdict', 'fcg_antigence_swap', 'fcg_antigence_full',
            'inject_antigence_verdict', 'inject_antigence_swap', 'inject_antigence_full']
for (tag, split), r in sorted(runs.items()):
    if r['meta'].get('arms') == 'direct': continue
    rows = r['rows']; d = {}
    for a in BASE_ARMS: d[a] = base_metrics(rows, a)
    for a in ADM_ARMS: d[a] = selective_metrics(rows, a)
    d['injection'] = injection_metrics(rows)
    # gate view under attack: among cases the clean fcg arm got right, how many did each gate ADMIT with the injected letter?
    for a in ('inject_antigence_swap', 'inject_antigence_verdict', 'inject_antigence_full'):
        d[a]['flip_admitted_injected'] = sum(1 for x in rows if x['arms']['fcg'].get('strict_correct') and x['arms'][a].get('admitted_injected'))
    for a in ('forged_verify', 'edge_removed'):
        d[a] = {'abstain': sum(1 for x in rows if x['arms'][a]['decision'] == 'ABSTAIN'), 'model_calls': sum(1 for x in rows if x['arms'][a]['model_called']), 'n': len(rows)}
        assert d[a]['abstain'] == len(rows) and d[a]['model_calls'] == 0, ('INTEGRITY_GATE_LEAK', tag, split, a)
    out['per_arm'][f'{tag}:{split}'] = d
# within-lane harness comparisons (same weights): fco vs direct, fcg vs direct; across-lane model comparisons: Lx direct vs L0 direct
for split in ('discovery', 'heldout'):
    fam = {}
    l0 = runs.get(('L0', split))
    for (tag, sp), r in sorted(runs.items()):
        if sp != split or r['meta'].get('arms') == 'direct': continue
        base = arm_flags(r['rows'], 'direct')
        for arm in ('fco', 'fcg'):
            fam[f'{tag}:{arm}_vs_direct'] = compare(base, arm_flags(r['rows'], arm), strata)
        if l0 is not None and tag != 'L0':
            fam[f'{tag}:direct_vs_L0:direct'] = compare(arm_flags(l0['rows'], 'direct'), base, strata)
    h = holm({k: v['p_mcnemar_exact_two_sided'] for k, v in fam.items()})
    for k in fam:
        fam[k]['holm'] = h[k]
        fam[k]['admission'] = admission_rule(fam[k]['mcnemar_gate'] and h[k]['reject'], fam[k]['bootstrap_gate'],
                                             'NOT_TESTED' if split == 'discovery' else 'SEE_HELDOUT_ROW', 'NOT_TESTED')
    out['comparisons'][split] = fam
# cold restart replay of L0 direct on discovery
if ('L0', 'discovery') in runs and ('L0replay', 'discovery') in runs:
    a = arm_flags(runs[('L0', 'discovery')]['rows'], 'direct'); b = arm_flags(runs[('L0replay', 'discovery')]['rows'], 'direct')
    frozen = {x['case_digest_sha256']: x['baseline_correct'] for x in jsonl(R / 'evidence/stats/discovery_pair_flags.jsonl')}
    out['replay'] = {'warm_vs_cold_agreement': sum(1 for k in a if a[k] == b[k]), 'warm_vs_frozen_agreement': sum(1 for k in a if a[k] == frozen[k]),
                     'cold_vs_frozen_agreement': sum(1 for k in b if b[k] == frozen[k]), 'n': len(a),
                     'frozen_correct': sum(frozen.values()), 'warm_correct': sum(a.values()), 'cold_correct': sum(b.values())}
emit('exp011_lane_stats.json', out)
for split, fam in out['comparisons'].items():
    print('==', split)
    for k, v in fam.items():
        print(f"{k:40s} acc {v['accuracy_baseline']:.3f}->{v['accuracy_challenger']:.3f} d={v['delta_abs']:+.3f} b/c={v['table']['baseline_only']}/{v['table']['challenger_only']} p={v['p_mcnemar_exact_two_sided']:.4f} holm={v['holm']['p_holm']:.4f} CI={v['ci95_delta_stratified_bootstrap']} -> {v['admission']}")
print('REPLAY', out['replay'])""")])

# ---------------------------------------------------------------- EXP-012 EHR forms
nb("12_redteam_ehr_forms.ipynb", "EXP-012 (red-team): synthetic form → VLM extraction → verification → draft FHIR → deterministic scorer",
   {"1 Requirements and predeclared hypothesis": "H0: single-pass VLM extraction on 12 clean synthetic forms is not perfect; the consistency+identity gate admits only correct fields (false admissions = 0) and the cross-patient FCO mismatch is caught 12/12. Synthetic only; Epic NOT contacted; EHR write PROHIBITED.",
    "2 Input source, license, hashes": "derived/forms12 on magicSTUDIObox (Synthea sample CSV sha 990d5206..., rendered with Pillow 12.3.0, SYNFORM root 36d12313...); public export evidence/redteam/lanes/EHR_qwen2.5vl_3b_forms12_PUBLIC.jsonl (booleans only).",
    "3 Frozen settings": "qwen2.5vl:3b via Ollama, temperature 0, seed 20261102, format=json.",
    "4 Deterministic preprocessing": "frontier_forms.fhir_draft normalization and validation (dates ISO, gender map, FCO case-id cross-check).",
    "5 Model/harness execution": "replayed from receipts; no inference here.",
    "6 Analysis": "per-field accuracy for extract / extract_fco / reread; admission confusion (TP/FP/FN/TN, FPR, FDR); FHIR draft equality vs gold draft.",
    "7 Negative controls": "cross-patient identity check; fixture validation failures in tests/test_fhir_draft.py.",
    "8 Outputs": "exp012_forms.json.",
    "9 FCO/FCG dependency changes": "adds EXECUTED edge PROPOSED_TRANSFORM(Synthea→form→OCR→FHIR) for 12 synthetic cases; Epic edge unchanged NOT_TESTED.",
    "10 Claim ceiling": CEILING + " 12 clean rendered forms are not scanned/faxed documents; no OCR robustness claim."},
   [code(COMMON + """from frontier_forms.fhir_draft import FORM_FIELDS, confusion, draft_fhir
pub = sorted((R / 'evidence/redteam/lanes').glob('EHR_*_forms12_PUBLIC.jsonl'))
assert pub, 'FORMS_EXPORT_MISSING'
rows = jsonl(pub[0]); meta = json.loads(pub[0].with_name(pub[0].name.replace('_PUBLIC.jsonl', '_META.json')).read_text())
assert len({r['case_id'] for r in rows}) == len(rows) == 12
agg = {'n_forms': len(rows), 'model': meta['model'], 'form_root': meta['form_root'], 'per_field': {}, 'cross_patient_abstain': sum(1 for r in rows if r['cross_patient_identity_check'] == 'ABSTAIN')}
for f in FORM_FIELDS:
    agg['per_field'][f] = {k: sum(1 for r in rows if r[k][f]) for k in ('correct_extract', 'correct_fco', 'correct_reread', 'admitted')}
tot = {k: sum(1 for r in rows for f in FORM_FIELDS if r[k][f]) for k in ('correct_extract', 'correct_fco', 'correct_reread', 'admitted')}
adm = confusion({(r['case_id'], f): r['admitted'][f] for r in rows for f in FORM_FIELDS} and {f'{r["case_id"]}|{f}': r['admitted'][f] for r in rows for f in FORM_FIELDS},
                {f'{r["case_id"]}|{f}': r['correct_extract'][f] for r in rows for f in FORM_FIELDS}) if False else None
# field-level admission confusion across all 84 fields
A = {f'{r["case_id"]}|{f}': r['admitted'][f] for r in rows for f in FORM_FIELDS}; C = {f'{r["case_id"]}|{f}': r['correct_extract'][f] for r in rows for f in FORM_FIELDS}
tp = sum(1 for k in A if A[k] and C[k]); fp = sum(1 for k in A if A[k] and not C[k]); fn = sum(1 for k in A if not A[k] and C[k]); tn = sum(1 for k in A if not A[k] and not C[k])
div = lambda a, b: a / b if b else None
agg.update({'fields_total': len(A), 'totals': tot, 'admission_confusion': {'TP': tp, 'FP': fp, 'FN': fn, 'TN': tn, 'FPR': div(fp, fp + tn), 'FDR': div(fp, tp + fp), 'FNR': div(fn, tp + fn), 'AUROC': 'NOT_COMPUTED_NO_CONTINUOUS_SCORES'},
            'false_admissions': fp, 'draft_patient_matches_gold': sum(1 for r in rows if r['draft_patient_matches_gold']), 'draft_encounter_matches_gold': sum(1 for r in rows if r['draft_encounter_matches_gold']),
            'tokens_extract_total': sum(r['tokens_extract'] for r in rows), 'tokens_challenge_total': sum(r['tokens_challenge'] for r in rows),
            'wall_extract_total': round(sum(r['wall_extract'] for r in rows), 2), 'wall_challenge_total': round(sum(r['wall_challenge'] for r in rows), 2),
            'epic': 'NOT_CONTACTED', 'ehr_write': 'PROHIBITED_NOT_ATTEMPTED'})
emit('exp012_forms.json', agg); print(json.dumps(agg, indent=2))""")])

# ---------------------------------------------------------------- EXP-013 integrity attacks
nb("13_redteam_integrity_attacks.ipynb", "EXP-013 (red-team): forged evidence, reordered leaves, forged parent links, missing receipts — deterministic gates",
   {"1 Requirements and predeclared hypothesis": "H0: every listed tamper is rejected by the verifiers in this repo, and the one known collision (duplicate-last) is bound by leaf_count. No model involved.",
    "2 Input source, license, hashes": "evidence/freeze/** metadata, evidence/sources/supabase_source_intake.json, evidence/stats/discovery_pair_flags.jsonl.",
    "3 Frozen settings": "same Merkle scheme; verifiers scripts/verify_predecessor.py, scripts/validate_pair_export.py, scripts/redteam/redteam_verify_sources.py.",
    "4 Deterministic preprocessing": "in-memory copies only; nothing on disk is modified.",
    "5 Model/harness execution": "none.",
    "6 Analysis": "attack matrix: expected REJECT vs observed.",
    "7 Negative controls": "the untampered inputs must PASS in the same cells.",
    "8 Outputs": "exp013_attacks.json.",
    "9 FCO/FCG dependency changes": "none.",
    "10 Claim ceiling": CEILING},
   [code(COMMON + """import tempfile, shutil, copy
from redteam_verify_sources import leaf, root, proof_ok
from verify_predecessor import verify
from validate_pair_export import check
attacks = {}
pred = R / 'evidence/freeze/predecessor'
rows = jsonl(pred / 'leaves.jsonl'); man = json.loads((pred / 'manifest.json').read_text())
def run_verify(mutate_rows=None, mutate_man=None):
    with tempfile.TemporaryDirectory() as td:
        d = Path(td); rr = copy.deepcopy(rows); mm = copy.deepcopy(man)
        if mutate_rows: mutate_rows(rr)
        if mutate_man: mutate_man(mm)
        (d / 'leaves.jsonl').write_text(''.join(json.dumps(x, sort_keys=True, separators=(',', ':')) + '\\n' for x in rr)); (d / 'manifest.json').write_text(json.dumps(mm))
        try: verify(d); return 'PASS'
        except AssertionError as e: return 'REJECT:' + str(e)[:40]
attacks['untampered_control'] = run_verify()
attacks['forged_source_leaf_sha'] = run_verify(lambda rr: rr[4].__setitem__('sha256', 'f' * 64))
attacks['reordered_leaves'] = run_verify(lambda rr: rr.__setitem__(slice(2, 4), [rr[3], rr[2]]))
attacks['removed_leaf'] = run_verify(lambda rr: rr.pop(5))
attacks['forged_parent_root_in_context'] = run_verify(lambda rr: rr[0]['context']['parent'].__setitem__('root', '0' * 64))
attacks['forged_edge_status'] = run_verify(lambda rr: rr[-1]['edges'][2].__setitem__('status', 'EXECUTED'))
attacks['duplicate_last_leaf_appended'] = run_verify(lambda rr: rr.append(copy.deepcopy(rr[-1])))
attacks['duplicate_last_leaf_and_count_forged'] = run_verify(lambda rr: rr.append(copy.deepcopy(rr[-1])), lambda mm: (mm.__setitem__('leaf_count', 16), mm['leaf_order'].append(mm['leaf_order'][-1])))
assert attacks['untampered_control'] == 'PASS'
assert all(v.startswith('REJECT') for k, v in attacks.items() if k not in ('untampered_control', 'duplicate_last_leaf_and_count_forged'))
# F-01 ceiling: duplicating the last leaf AND forging leaf_count/leaf_order keeps root and passes the unsigned verifier.
attacks['F01_note'] = 'duplicate_last_leaf_and_count_forged=' + attacks['duplicate_last_leaf_and_count_forged'] + ' -> count binding must live inside a hashed leaf or a signature (fixed in fco.redteam_successor.v1 context leaf)'
# pair export attacks
def pair_attack(mut):
    with tempfile.TemporaryDirectory() as td:
        t = Path(td); (t / 'evidence/stats').mkdir(parents=True); (t / 'evidence/freeze').mkdir(parents=True)
        shutil.copy(R / 'evidence/freeze/longebench_split_manifest.json', t / 'evidence/freeze/longebench_split_manifest.json')
        pr = jsonl(R / 'evidence/stats/discovery_pair_flags.jsonl'); mut(pr)
        (t / 'evidence/stats/discovery_pair_flags.jsonl').write_text(''.join(json.dumps(x) + '\\n' for x in pr))
        try: check(t); return 'PASS'
        except AssertionError as e: return 'REJECT:' + str(e)[:40]
split = json.loads((R / 'evidence/freeze/longebench_split_manifest.json').read_text())
heldout_key = next(iter(next(iter(split['task_partitions'].values()))['heldout']))
attacks['pairs_untampered_control'] = pair_attack(lambda pr: None)
attacks['pairs_heldout_leak'] = pair_attack(lambda pr: pr[0].__setitem__('case_digest_sha256', heldout_key))
attacks['pairs_duplicate_case'] = pair_attack(lambda pr: pr.__setitem__(1, dict(pr[0])))
attacks['pairs_wrong_task_binding'] = pair_attack(lambda pr: pr[0].__setitem__('task', 'LB-0315' if pr[0]['task'] != 'LB-0315' else 'LB-0307'))
attacks['pairs_dropped_case'] = pair_attack(lambda pr: pr.pop())
assert attacks['pairs_untampered_control'] == 'PASS' and all(v.startswith('REJECT') for k, v in attacks.items() if k.startswith('pairs_') and 'control' not in k)
# supabase gate must still fail closed
sup = json.loads((R / 'evidence/sources/supabase_source_intake.json').read_text())
attacks['supabase_live_rows_as_benchmark'] = 'REJECT:state=' + sup['state'] + ';root=' + sup['snapshot_merkle_root']
emit('exp013_attacks.json', attacks); print(json.dumps(attacks, indent=2))""")])
