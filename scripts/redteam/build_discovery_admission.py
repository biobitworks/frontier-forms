#!/usr/bin/env python3
"""Red-team lane discovery admission ledger (inventory admission only; scientific promotion HOLD).

Recomputes every admitted number from committed public evidence, pins each source file by sha256, and labels each
record with what is standard practice and what this lane added. Nothing here is SUPPORTED: no record has an
independent replication cohort, so `promoted` is always false and `scientific_promotion` is always HOLD.

Admission states:
  DISCOVERY_LEDGER_ADMITTED  paired test passed the predeclared rule (Holm p<0.05, bootstrap lower CI>0); HOLD
  POSTHOC_RECORDED           paired statistics computed after the fact (not preregistered); never promotable
  DATA_ADMITTED              frozen dataset / training receipt admitted as evidence, not as a gain
  NULL_RECORDED / NEGATIVE_RECORDED / FAILED_RECORDED / NOT_TESTED_RECORDED / BLOCKED_RECORDED

  python3 scripts/redteam/build_discovery_admission.py            # writes evidence/admission/REDTEAM_DISCOVERY_ADMISSION_V1.json
  python3 scripts/redteam/build_discovery_admission.py --check    # rebuild in memory and compare with the committed file
"""
from __future__ import annotations
import argparse, hashlib, json, random, sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(R / 'src'))
from frontier_forms.redteam_stats import exact_mcnemar_p, holm  # noqa: E402

OUT = R / 'evidence/admission/REDTEAM_DISCOVERY_ADMISSION_V1.json'
FIELDS = ('Synthetic case', 'Patient first', 'Patient last', 'Birth date', 'Gender', 'Encounter date', 'Visit class')
SEED, REPS = 20261102, 10000


def sha(rel): return hashlib.sha256((R / rel).read_bytes()).hexdigest()
def ev(*rels): return [{'path': r, 'sha256': sha(r)} for r in rels]
def jl(rel): return [json.loads(x) for x in (R / rel).read_text().splitlines() if x.strip()]


def cluster_boot(base, chal, cluster, reps=REPS, seed=SEED):
    """Patient-cluster paired bootstrap of the difference in success rate (resample patients, keep all their images)."""
    groups = {}
    for k in base:
        groups.setdefault(cluster[k], []).append(int(chal[k]) - int(base[k]))
    keys = sorted(groups); rng = random.Random(seed); d = []
    for _ in range(reps):
        tot = n = 0
        for _ in keys:
            g = groups[keys[rng.randrange(len(keys))]]; tot += sum(g); n += len(g)
        d.append(tot / n)
    d.sort()
    return [d[int((reps - 1) * 0.025)], d[int((reps - 1) * 0.975)]]


def paired(base, chal, cluster):
    b = sum(1 for k in base if base[k] and not chal[k]); c = sum(1 for k in base if chal[k] and not base[k])
    return {'n': len(base), 'baseline_success': sum(base.values()), 'challenger_success': sum(chal.values()),
            'baseline_only': b, 'challenger_only': c, 'delta_rate': (sum(chal.values()) - sum(base.values())) / len(base),
            'mcnemar_p_exact_two_sided': exact_mcnemar_p(b, c), 'ci95_patient_cluster_bootstrap': cluster_boot(base, chal, cluster)}


def decide(o, holm_p):
    if holm_p < 0.05 and o['delta_rate'] > 0 and o['ci95_patient_cluster_bootstrap'][0] > 0:
        return 'PASS_DISCOVERY_RULE'
    if holm_p < 0.05 and o['delta_rate'] < 0:
        return 'NEGATIVE_WORSE'
    return 'NULL'


def build():
    recs = []

    def add(**k):
        k.setdefault('promoted', False); k.setdefault('scientific_promotion', 'HOLD'); k.setdefault('replication', 'NOT_TESTED')
        recs.append(k)

    # 1. Preregistered trained-model gain (A1-A3 vs A0), recomputed from per-image rows, with patient-cluster CI added.
    tg = 'evidence/redteam/trained_gain/trained_gain_rows.json'
    rows = json.loads((R / tg).read_text())
    cl = {r['input_fco_id']: r['case_id'] for r in rows}
    base = {r['input_fco_id']: r['arms']['A0']['all7'] for r in rows}
    outs = {a: paired(base, {r['input_fco_id']: r['arms'][a]['all7'] for r in rows}, cl) for a in ('A1', 'A2', 'A3')}
    hp = holm({a: o['mcnemar_p_exact_two_sided'] for a, o in outs.items()})
    names = {'A1': ('learned OCR post-correction', 'character/space correction table fit on the 132 SYNFORM2 train images only'),
             'A2': ('trained YOLOv8n crops + OCR', 'YOLOv8n fine-tuned on the train split; OCR on x3-upscaled value crops'),
             'A3': ('crops + learned correction', 'A2 followed by the A1 correction table')}
    for a, o in outs.items():
        o['holm_p'] = hp[a]['p_holm'] if isinstance(hp[a], dict) else hp[a]
        d = decide(o, o['holm_p'])
        add(id=f'RT-ADM-TRAINED-{a}', family='trained_model_gain', preregistered=True,
            preregistration={'path': 'scripts/redteam/trained_gain_eval.py', 'commit': '5615a07', 'sha256': sha('scripts/redteam/trained_gain_eval.py')},
            question=f'Does {names[a][0]} improve all-7-field extraction over untrained page OCR on the held-out test split?',
            weights={'baseline': 'Apple Vision OCR (.accurate) + deterministic rule parser, no learned parameters',
                     'challenger': names[a][1] + ('' if a == 'A1' else '; detector best.pt sha256 d7bc1a0487a41831cda89c0af6809a58c2744ba8aeccdcac9faa101054776eba')},
            mechanism={'changed': 'LEARNED_COMPONENT_ADDED', 'ocr_engine_held_constant': True},
            outcome=dict(o, unit='image (23 patients x clean + scan)', endpoint='all 7 fields equal the printed value'),
            decision=d, admission_state='DISCOVERY_LEDGER_ADMITTED' if d == 'PASS_DISCOVERY_RULE' else ('NEGATIVE_RECORDED' if d.startswith('NEG') else 'NULL_RECORDED'),
            evidence=ev(tg, 'evidence/redteam/trained_gain/trained_gain_summary.json'),
            primary_source_pr='#51 (commit 4a52345); #58 re-plotted these numbers',
            novelty={'standard': 'post-OCR correction tables and fine-tuned object detectors are standard techniques',
                     'this_lane': 'train-only fit, test split touched once, preregistered arms and endpoint, OCR engine held constant so only the trained component differs',
                     'claim_ceiling': 'discovery on one synthetic template family; the correction is small (space stripping + O->0 in case ids)'})

    # 2. Commitment / rules / consistency / identity gate factorial (paired, Holm-corrected in the lane analysis).
    am = json.loads((R / 'evidence/redteam/attribution_matrix.json').read_text())
    by = {r['experiment_id']: r for r in am['records']}
    for rid, name in (('RT-096', 'commitment'), ('RT-099', 'rules'), ('RT-097', 'consistency'), ('RT-098', 'identity'), ('RT-110', 'identity+rules+commitment+consistency')):
        r = by[rid]; o = r['outcome']
        passed = r.get('claim_status') == 'PASS' and o['holm_p'] < 0.05 and isinstance(o['bootstrap_ci95'], list) and o['bootstrap_ci95'][0] > 0
        add(id=f'RT-ADM-GATE-{name.upper().replace("+", "-")}', family='admission_gate_factorial', preregistered=False,
            question=f'Does the {name} check catch planted field errors that the unchecked extractor admits?',
            weights={'baseline': 'qwen2.5vl:3b extraction with Apple Vision OCR fallback (unchanged)', 'challenger': 'same weights; deterministic check added'},
            mechanism={'changed': 'MECHANISM_ONLY', 'enabled': name.split('+')},
            outcome={k: o.get(k) for k in ('planted_detection_rate', 'false_admission_rate_of_all', 'coverage', 'mcnemar_p', 'holm_p', 'bootstrap_ci95')},
            decision='PASS_DISCOVERY_RULE' if passed else 'NULL', admission_state='DISCOVERY_LEDGER_ADMITTED' if passed else 'NULL_RECORDED',
            evidence=ev('evidence/redteam/gate_factorial.json', 'evidence/redteam/attribution_matrix.json'),
            caveat=('The commitment check compares each extracted value with a salted hash of the source value, so it detects any printed value '
                    'that differs from the source by construction. The finding is that the other checks miss most of these errors, not that hashing is new.')
            if 'commitment' in name else 'Planted errors were designed by the same lane that wrote the checks.',
            novelty={'standard': 'validation rules, cross-field consistency and hash commitments are standard building blocks',
                     'this_lane': 'per-field salted source commitments bound into the FCO leaf, a full 2^4 factorial with leave-one-mechanism-out, planted-error set with opaque image ids and a private planted list',
                     'claim_ceiling': 'synthetic planted errors on one template family; requires access to the source record at admission time'})

    # 3. Post-hoc model comparisons on the same 46 test images (not preregistered; never promotable).
    fa = 'evidence/redteam/db/field_answers.jsonl'
    test = [r for r in jl(fa) if r['dataset'] == 'synform2' and r['split'] == 'test']
    cl2 = {r['input_fco_id']: r['case_id'] for r in test}
    flag = lambda m: {r['input_fco_id']: all(r['fields'][f]['answers'][m]['correct_vs_printed'] for f in FIELDS) for r in test}
    b0 = flag('apple_vision_ocr')
    assert sum(b0.values()) == outs['A1']['baseline_success'], 'BASELINE_MISMATCH_BETWEEN_DB_AND_TRAINED_GAIN_ROWS'
    ph = {m: paired(b0, flag(m), cl2) for m in ('qwen2.5vl:3b:extract', 'qwen2.5:1.5b:ocr_mapper', 'qwen3:1.7b:ocr_mapper')}
    hph = holm({m: o['mcnemar_p_exact_two_sided'] for m, o in ph.items()})
    for m, o in ph.items():
        o['holm_p'] = hph[m]['p_holm'] if isinstance(hph[m], dict) else hph[m]
        o['fields_correct'] = sum(r['fields'][f]['answers'][m]['correct_vs_printed'] for r in test for f in FIELDS)
        o['baseline_fields_correct'] = sum(r['fields'][f]['answers']['apple_vision_ocr']['correct_vs_printed'] for r in test for f in FIELDS)
        add(id='RT-ADM-POSTHOC-' + m.split(':')[0].upper().replace('.', '_'), family='model_weight_comparison', preregistered=False,
            question=f'All-7-field extraction: {m} vs Apple Vision OCR + rule parser on the same test images',
            weights={'baseline': 'Apple Vision OCR + rule parser', 'challenger': f'{m} (pretrained Ollama weights, not trained by this lane)'},
            mechanism={'changed': 'WEIGHTS_ONLY'}, outcome=dict(o, unit='image', endpoint='all 7 fields equal the printed value'),
            decision=decide(o, o['holm_p']) + '_POSTHOC', admission_state='POSTHOC_RECORDED', evidence=ev(fa),
            novelty={'standard': 'off-the-shelf pretrained model inference', 'this_lane': 'per-field answers exported with model name and paired against the same images',
                     'claim_ceiling': 'post hoc, not preregistered; cannot be promoted'})

    # 4. Data and training receipts admitted as evidence (not as gains).
    for run in ('full', 'no_scan'):
        fr = json.loads((R / f'evidence/redteam/detector/{run}/final_receipt.json').read_text())
        ts = json.loads((R / f'evidence/redteam/detector/{run}/test_scores.json').read_text())
        st = fr['statuses']
        add(id=f'RT-ADM-DATA-DETECTOR-{run.upper()}', family='actual_training_snapshot', preregistered=False,
            question='Per-epoch Merkle-chained training ledger of the YOLOv8n field detector',
            weights={'trained': f"YOLOv8n best weights sha256 {fr['best_weights_sha256']} (raw weights not published)", 'framework': fr['framework']},
            mechanism={'lomo': run},
            outcome={'epochs': fr['epochs_committed'], 'GAIN': st.count('GAIN'), 'LOSS': st.count('LOSS'), 'NEUTRAL': st.count('NEUTRAL'),
                     'chain_root': fr['chain_root'], 'test_summary': {k: v for k, v in ts.items() if isinstance(v, (int, float, str))}},
            decision='OBSERVED', admission_state='DATA_ADMITTED',
            evidence=ev(f'evidence/redteam/detector/{run}/final_receipt.json', f'evidence/redteam/detector/{run}/epoch_ledger.jsonl',
                        f'evidence/redteam/detector/{run}/chain_manifest.json', f'evidence/redteam/detector/{run}/test_scores.json'),
            caveat='Detector quality is not an extraction gain: crop OCR from this detector was NULL (RT-ADM-TRAINED-A2).',
            novelty={'standard': 'ultralytics YOLOv8n fine-tuning with default hyperparameters; per-epoch validation',
                     'this_lane': 'each epoch committed as a hash-chained leaf (weights sha256, paired McNemar + bootstrap vs the previous epoch, GAIN/LOSS/NEUTRAL), plus a leave-one-mechanism-out run without scan variants',
                     'claim_ceiling': 'training provenance; best epoch selected on dev, never test'})
    for name, rel, root in (('SYNFORM2', 'evidence/redteam/synform2', 'aa447934df5267349386fd0c5053a63a5ec140b05c504d221591e4ddd4b7580e'),
                            ('SYNFORM2-ERR', 'evidence/redteam/synform2_err', '790a7dc6f9641fa6c09df8ac951d8456f9ab2685326e4eb67012cd0e87d68944')):
        files = sorted(str(p.relative_to(R)) for p in (R / rel).rglob('*.json*'))
        add(id=f'RT-ADM-DATA-{name}', family='frozen_dataset', preregistered=False, question=f'Frozen synthetic form dataset {name}',
            weights=None, mechanism=None, outcome={'merkle_root': root}, decision='OBSERVED', admission_state='DATA_ADMITTED', evidence=ev(*files),
            novelty={'standard': 'MITRE Synthea synthetic patients rendered to images', 'this_lane': 'frozen Merkle root, patient-level splits, opaque image ids, per-field salted commitments',
                     'claim_ceiling': 'synthetic only; one template family'})

    # 5. Negative, null, failed, blocked and not-tested results kept on purpose.
    for rid in ('RT-001', 'RT-002', 'RT-004', 'RT-005', 'RT-007', 'RT-008'):
        r = by[rid]
        add(id=f'RT-ADM-NULL-CONTEXT-{rid}', family='fco_context_projection', preregistered=False, question=f"{r['baseline']} vs {r['challenger']} on LongevityBench discovery split",
            weights={'model': (r.get('weights') or {}).get('challenger', {}).get('name')}, mechanism={'changed': 'MECHANISM_ONLY'},
            outcome={k: r['outcome'].get(k) for k in ('delta_abs', 'mcnemar_p', 'holm_p', 'bootstrap_ci95')}, decision='NULL', admission_state='NULL_RECORDED',
            evidence=ev('evidence/redteam/attribution_matrix.json'), novelty={'standard': 'context in prompt', 'this_lane': 'same weights and cases with and without FCO/FCG context', 'claim_ceiling': 'no gain observed'})
    for rid in ('RT-003', 'RT-006', 'RT-011', 'RT-014'):
        r = by[rid]
        add(id=f'RT-ADM-NEG-MODEL-{rid}', family='model_weight_comparison', preregistered=False, question=f"{r['baseline']} vs {r['challenger']} on LongevityBench",
            weights={'baseline': r['baseline'], 'challenger': r['challenger']}, mechanism={'changed': 'WEIGHTS_ONLY'},
            outcome={k: r['outcome'].get(k) for k in ('delta_abs', 'mcnemar_p', 'holm_p', 'bootstrap_ci95')}, decision='NEGATIVE_WORSE', admission_state='NEGATIVE_RECORDED',
            evidence=ev('evidence/redteam/attribution_matrix.json'), novelty={'standard': 'model swap', 'this_lane': 'paired on identical frozen cases', 'claim_ceiling': 'small general Qwen models are much worse on this benchmark'})
    bo = json.loads((R / 'docs/demo/ocr_boxes_vs_clean.json').read_text())
    add(id='RT-ADM-NEG-BOXES-BREAK-OCR', family='ocr_interference', preregistered=False, question='Does drawing bounding boxes on the image change Apple Vision OCR accuracy?',
        weights={'model': 'Apple Vision OCR'}, mechanism={'changed': 'INPUT_ONLY (overlay drawn)'},
        outcome={'clean_fields_correct': bo['clean_fields_correct'], 'boxes_fields_correct': bo['boxes_fields_correct'], 'fields_total': bo['fields_total'], 'images': bo['images']},
        decision='NEGATIVE_WORSE_DESCRIPTIVE', admission_state='NEGATIVE_RECORDED', evidence=ev('docs/demo/ocr_boxes_vs_clean.json'),
        novelty={'standard': 'OCR', 'this_lane': 'isolated overlay interference on identical forms', 'claim_ceiling': '10 forms, descriptive; OCR must run on the clean render'})
    pv = json.loads((R / 'docs/demo/preview/preview_ocr.json').read_text())
    add(id='RT-ADM-FAILED-PREVIEW-CAPTURE', family='harness', preregistered=False, question='macOS Preview window capture then Apple OCR',
        weights=None, mechanism=None, outcome={'captured': pv['captured'], 'images': pv['images']}, decision='FAILED', admission_state='FAILED_RECORDED',
        evidence=ev('docs/demo/preview/preview_ocr.json'), caveat='could not create image from window; Screen Recording permission likely missing',
        novelty={'standard': 'screen capture', 'this_lane': 'none', 'claim_ceiling': 'no result'})
    for rid, state in (('RT-111', 'BLOCKED_RECORDED'), ('RT-112', 'BLOCKED_RECORDED'), ('RT-113', 'NOT_TESTED_RECORDED'), ('RT-114', 'NOT_TESTED_RECORDED')):
        r = by[rid]
        add(id=f'RT-ADM-{state.replace("_RECORDED", "").replace("_", "")}-{rid}', family='not_run', preregistered=False, question=r.get('intervention') or r.get('kind'),
            weights=None, mechanism=None, outcome={'claim_status': r.get('claim_status')}, decision=r.get('claim_status'), admission_state=state,
            evidence=ev('evidence/redteam/attribution_matrix.json'), novelty={'standard': 'n/a', 'this_lane': 'n/a', 'claim_ceiling': 'not run'})

    counts = {}
    for r in recs:
        counts[r['admission_state']] = counts.get(r['admission_state'], 0) + 1
    return {'schema': 'frontier_forms.redteam_discovery_admission.v1', 'program_id': 'frontier-forms', 'lane': 'claude-redteam',
            'status': 'ADMITTED_TO_DISCOVERY_LEDGER_ONLY; SCIENTIFIC_PROMOTION=HOLD',
            'rule': 'DISCOVERY_LEDGER_ADMITTED requires Holm-corrected exact McNemar p<0.05, delta>0 and bootstrap lower 95% CI>0 on a predeclared paired comparison. '
                    'Scientific promotion additionally requires an independently frozen replication cohort and PI approval; none exists, so every record is HOLD.',
            'statistics': {'mcnemar': 'exact two-sided', 'bootstrap': f'patient-cluster paired, {REPS} reps, seed {SEED} (trained-gain and post-hoc rows); lane-native stratified bootstrap for gate rows'},
            'counts_by_admission_state': dict(sorted(counts.items())), 'records': recs,
            'synthetic_only': True, 'weights_published': False, 'phi': False}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--check', action='store_true'); a = ap.parse_args()
    raw = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    if a.check:
        ok = OUT.exists() and OUT.read_text() == raw
        print('ADMISSION_LEDGER', 'MATCH' if ok else 'MISMATCH'); sys.exit(0 if ok else 1)
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(raw)
    d = json.loads(raw); print(d['counts_by_admission_state'])
    for r in d['records']:
        o = r['outcome'] or {}
        print(r['id'], r['admission_state'], r['decision'], o.get('baseline_success'), o.get('challenger_success'), o.get('holm_p'), o.get('ci95_patient_cluster_bootstrap'))


if __name__ == '__main__':
    main()
