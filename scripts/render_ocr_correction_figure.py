#!/usr/bin/env python3
"""Figure 12 is a static, source-backed judge view of independent OCR readback."""
import html,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
j=json.loads((R/'docs/judges/OCR_CORRECTION_SUCCESSOR_V2.json').read_text())
path=R/'docs/judges/FIG12_OCR_CORRECTION_ABLATION_V1.html'
if path.exists():raise FileExistsError('APPEND_ONLY_COLLISION')
css='''body{font:14px/1.55 -apple-system,Arial,sans-serif;margin:0;background:#f2f6f9;color:#19374c}
header{background:#153047;color:#fff;padding:30px max(24px,calc((100vw - 950px)/2))}
main{max-width:1050px;margin:auto;padding:20px}section{background:#fff;padding:18px;margin:12px 0;border-radius:10px;border:1px solid #d9e4ea}
.row{display:grid;grid-template-columns:240px 1fr 100px;gap:12px;align-items:center;margin:14px 0}
.bar{background:#eff3f6;border-radius:10px;height:22px;overflow:hidden}
.fill{height:22px;background:#4785ab}.green{background:#238465}.red{background:#bb6c67}
table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:9px;border:1px solid #dce6ed;text-align:left}
th{background:#eef5f8}.fine{font-size:12px;color:#5b7386}.mono{font:11px ui-monospace,monospace;overflow-wrap:anywhere}'''
out=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Figure 12: learned OCR correction</title><style>'+css+'</style></head><body>']
out.append('<header><h1>Figure 12 · Learned OCR correction versus detector crops</h1><p>Frontier Forms | 46 synthetic images, 23 cases × clean/scan | Claude experiment, independent ChatGPT patient-cluster reanalysis</p></header><main>')
out.append('<section><h2>All seven form fields correct</h2>')
names=[('A0','Page OCR + deterministic rules',14),('A1','Train-fitted text correction',22),('A2','YOLO crops before OCR',9),('A3','YOLO crops + text correction',15)]
for arm,name,n in names:
 col=' green' if arm=='A1' else (' red' if arm=='A2' else '')
 out.append('<div class="row"><span>'+html.escape(name)+'</span><div class="bar"><div class="fill'+col+'" style="width:'+str(round(n/46*100,2))+'%"></div></div><strong>'+str(n)+'/46</strong></div>')
out.append('<p class="fine">A1 fits OCR text-correction table parameters on 132 SYNFORM2 training images. This is not a trained Qwen checkpoint. All test images were synthetic. Same template family and repeated renders limit generalization.</p></section>')
out.append('<section><h2>Paired statistical effects versus A0</h2><table><tr><th>Arm</th><th>Difference</th><th>Wins/losses</th><th>Exact McNemar p</th><th>Holm p</th><th>Patient-cluster 95% CI</th><th>Evidence state</th></tr>')
for v in j['arms']:
 ci=v['patient_cluster_bootstrap95']
 out.append('<tr><td>'+v['arm']+'</td><td>'+f'{100*v["delta_all7"]:+.1f} pp'+'</td><td>'+str(v['discordant_challenger_only'])+'/'+str(v['discordant_baseline_only'])+'</td><td>'+f'{v["mcnemar_exact"]:.7f}'+'</td><td>'+f'{v["p_holm_3_comparisons"]:.7f}'+'</td><td>['+f'{100*ci[0]:+.2f}, {100*ci[1]:+.2f}'+'] pp</td><td>'+('Discovery positive; NOT promoted' if v['discovery_positive'] else 'NULL / NEGATIVE; NOT promoted')+'</td></tr>')
out.append('</table><p class="fine">Independent patient-level 10,000 bootstrap replicates resample complete clean+scan pairs together, not images independently. Source reported a clean/scan image-stratified bootstrap. No independent untouched second-cohort replication.</p></section>')
out.append('<section><h2>Model identity, source roots and admission ceiling</h2>')
for label,val in [('Fitted correction-table parameters SHA256',j['correction_parameters_sha256']),('Original 82-event judge root',j['predecessor_judge_outcome_root']),('OCR 3-arm successor root',j['ocr_event_root']),('Original source outputs SHA256',j['source_file_sha256']['evidence/redteam/trained_gain/trained_gain_rows.json'])]:
 out.append('<p class="mono"><strong>'+html.escape(label)+':</strong> '+html.escape(val)+'</p>')
out.append('<p>Only the Vita DAISY freeze–challenge–replicate–admit method was used; DAISY-specific performance remains NOT_COMPUTED. The experiment script declares preregistration, but no separate pre-test timestamped signed record has been verified. Scientific admission: HOLD pending new patient/template replication and independent checkpoint/source confirmation.</p><p class="fine"><a href="OCR_CORRECTION_SUCCESSOR_V2.json">Inspect exact paired evidence receipt</a>. Original Claude test data are unchanged. All figures and data are synthetic.</p></section></main></body></html>')
path.write_text(''.join(out))
print('FIG12',path.stat().st_size,'bytes')
