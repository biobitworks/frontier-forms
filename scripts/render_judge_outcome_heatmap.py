#!/usr/bin/env python3
"""Render a self-contained, evidence-backed judge heatmap from immutable JSON."""
from pathlib import Path
import json,html
R=Path(__file__).resolve().parents[1]
x=json.loads((R/'docs/judges/JUDGE_OUTCOMES_SUCCESSOR_V1.json').read_text())
esc=lambda s:html.escape(str(s),quote=True)
fco=x['fco']['rows']; errors=x['injected_errors']['rows']
def status(k):
 if k=='GAIN':return 'gain'
 if k in ('LOSS','NEGATIVE_NO_GAIN'):return 'loss'
 if k=='NEUTRAL':return 'neutral'
 if k=='FIRST_EPOCH':return 'unknown'
 if 'POSITIVE' in k:return 'discovery'
 if 'NEGATIVE' in k or 'TIE' in k:return 'loss'
 return 'unknown'
styles='''body{font:14px/1.55 -apple-system,BlinkMacSystemFont,Arial,sans-serif;background:#f4f7fa;color:#223a50;margin:0}header{background:#10283d;color:#f4f8ff;padding:30px max(20px,calc((100vw - 1180px)/2))}main{max-width:1240px;margin:auto;padding:20px}h1{font-size:27px;margin:0}h2{font-size:18px}.sub{color:#c6d8e8}section{background:white;border:1px solid #d8e3ed;border-radius:10px;padding:19px;margin:14px 0}p{margin:9px 0}.keys{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}.key{padding:4px 9px;border-radius:5px;font-size:11px;font-weight:700}.gain{background:#d1e7dd;color:#155638}.loss{background:#fbdcda;color:#923b35}.neutral{background:#e3e8ee;color:#425b70}.unknown{background:#fff0c8;color:#805d17}.discovery{background:#dcebf9;color:#205780}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;min-width:850px;font-size:12px}td,th{padding:8px;border:1px solid #e1e8ed;text-align:left}th{background:#eff4f7}td.num{text-align:right;font-variant-numeric:tabular-nums}.ramp{display:grid;grid-template-columns:110px repeat(30,minmax(25px,1fr));gap:2px;overflow-x:auto}.ramp .cell{height:35px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:10px;border-radius:3px}.ramp .lab{font-size:12px;display:flex;align-items:center}.stat{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:10px}.stat div{background:#f0f5f8;border-radius:7px;padding:12px}.val{font-size:23px;font-weight:750}.mono{font:11px ui-monospace,monospace;overflow-wrap:anywhere}.small{font-size:11px;color:#51687a}footer{padding:25px}a{color:#165b9a}@media(max-width:600px){.stat{grid-template-columns:repeat(2,1fr)}}'''
out=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Frontier Forms judge evidence — gains, losses and admissions</title><style>'+styles+'</style></head><body>']
out.append('<header><h1>Figure 11 · Gains, losses, neutral epochs and promotion gates</h1><p class="sub">Frontier Forms · Synthetic evidence only · Explicit authorship attribution · 2026-11-02</p><p>Each colored tile refers to a completed test or documented non-test. <b>Green = within-run development gain</b>, red = loss or negative outcome, grey = neutral, amber = not tested, blue = discovery-only improvement. None denotes independent scientific promotion.</p></header><main>')
out.append('<section><h2>1. Judge outcome summary</h2><div class="stat">')
for name,val,caption in [
 ('Scientific promotions','0','No independent patient/template replication'),
 ('FCO discovery gain','+22.2 pp','18/54 → 30/54 form successes'),
 ('YOLO full run','3 gains · 3 losses','30 measured epochs; 23 neutral'),
 ('OCR overlay damage','58 → 0 / 70','Clean vs drawing boxes before OCR')]:
 out.append('<div><div class="small">'+esc(name)+'</div><div class="val">'+esc(val)+'</div><div class="small">'+esc(caption)+'</div></div>')
out.append('</div><p class="small">Admission policy: <b>HOLD_NO_INDEPENDENT_PI_ADMISSION</b>. Vita DAISY inspired the freeze/challenge/replicate/admit method, but contributed no model weights, performance gains or Merkle roots.</p></section>')
out.append('<section><h2>2. Trained YOLOv8n checkpoints over time (actual 30-epoch × 2-arm record)</h2><p>Columns = training epoch, rows = full synthetic clean+scan training or no-scan LOMO. Each cell shows G (gain), L (loss), = (neutral), or 1 (first epoch). The plotted state uses exact paired McNemar and stratified 2,000-replicate bootstrap <b>on 44 development renders</b>, not independent patients or prospective holdout.</p><div class="keys"><span class="key gain">Development gain</span><span class="key loss">Development loss</span><span class="key neutral">Neutral</span><span class="key unknown">Initial</span></div><div class="ramp"><div class="lab">Training arm</div>')
for i in range(1,31):out.append('<div class="cell neutral">'+str(i)+'</div>')
for r in x['yolo_training']:
 out.append('<div class="lab">'+esc(r['lane'])+'</div>')
 for q in r['epochs']:
  k=status(q['state']);symbol={'GAIN':'G','LOSS':'L','NEUTRAL':'=','FIRST_EPOCH':'1'}.get(q['state'],'?')
  title='Epoch '+str(q['epoch'])+' | '+q['state']+' | dev pass '+str(q['dev_image_pass'])+'/44 | Δ '+str(q['gain_vs_prev'])+' | McNemar '+str(q['mcnemar_p'])+' | weights '+q['weights_sha256']
  out.append('<div class="cell '+k+'" title="'+esc(title)+'">'+symbol+'</div>')
out.append('</div><p class="small">Full root: <span class="mono">'+esc(x['yolo_training'][0]['root'])+'</span> · No-scan root: <span class="mono">'+esc(x['yolo_training'][1]['root'])+'</span>. Both roots independently replayed from epoch receipts. Existing checkpoint weight SHA-256s are <b>recorded</b>; original .pt bytes were not rehashed by this audit. Multiple comparisons and development set exposure preclude blanket promotion.</p></section>')
out.append('<section><h2>3. FCO/FCG leave-one-module-out paired effects</h2><p>Rows = single changed mechanism/leaf on exactly 54 synthetic test forms from 18 patients; outcome = entire form correct. McNemar is descriptive and patient-cluster 95% CI is primary. Holm adjusts 12 comparisons. Positive findings remain discovery-grade.</p><div class="table-wrap"><table><tr><th>One-leaf contrast</th><th>Δ full-form pp</th><th>McNemar</th><th>Holm p</th><th>95% patient CI</th><th>State / promotion</th></tr>')
for y in fco:
 c=y['ci95_patient_cluster']; out.append('<tr><td>'+esc(y['arm'])+'<div class="small">'+esc(y['leaf'])+'</div></td><td class="num">'+f'{100*y["delta"]:+.1f}'+'</td><td class="num">'+f'{y["mcnemar_p"]:.5g}'+'</td><td class="num">'+f'{y["holm_p"]:.5g}'+'</td><td class="num">'+('['+f'{100*c[0]:+.1f}, {100*c[1]:+.1f}'+'] pp' if c else 'NOT_COMPUTED')+'</td><td><span class="key '+status(y['state'])+'">'+esc(y['state'])+'</span><div class="small">PROMOTED = false</div></td></tr>')
out.append('</table></div></section>')
out.append('<section><h2>4. Synthetic error detectors, independent negative controls</h2><p>Rows = 6 matched M1 Merkle/M2 Lean4/M3 source-binding detector contrasts on 702 planted error instances. Error-instance outcomes are correlated by source and cannot be treated as model training gains.</p><div class="table-wrap"><table><tr><th>Leaf</th><th>Δ recall pp</th><th>McNemar</th><th>Holm p</th><th>State</th></tr>')
for y in errors:out.append('<tr><td>'+esc(y['leaf'])+'</td><td class="num">'+f'{100*y["delta"]:+.1f}'+'</td><td class="num">'+f'{y["mcnemar_p"]:.5g}'+'</td><td class="num">'+f'{y["holm_p"]:.5g}'+'</td><td><span class="key '+status(y['state'])+'">'+esc(y['state'])+'</span></td></tr>')
out.append('</table></div></section>')
out.append('<section><h2>5. Model weights versus controls — negative and neutral results</h2><div class="table-wrap"><table><tr><th>Model</th><th>Reported metric</th><th>Control</th><th>Outcome</th></tr>')
for y in x['vision_models']['random_forest']:
 out.append('<tr><td>Random Forest / '+str(y['train_patients'])+' synthetic training patients</td><td>'+f'F1 = {y["f1"]:.4f}'+'</td><td>Deterministic F1 = 1.000</td><td><span class="key loss">NEGATIVE</span></td></tr>')
out.append('<tr><td>Trained local logistic box predictor</td><td>540/540 localized</td><td>Contour predictor also 540/540</td><td><span class="key loss">NO GAIN (p = 1)</span></td></tr>')
out.append('<tr><td>Qwen 0.5B LoRA</td><td>Only epoch-zero loss observed in merged timeline</td><td>No paired adapter readback</td><td><span class="key unknown">NOT_COMPUTED</span></td></tr>')
out.append('</table></div><p class="small">Other model/reader results are in <a href="../figures/accomplishment_heatmap.html">the original judge accomplishment heatmap</a> and <a href="FIGURES.md">Claude’s ten labeled figures</a>. Do not equate localization, OCR field accuracy, or clinical form success.</p></section>')
out.append('<section><h2>6. Attribution and proof boundaries</h2><div class="table-wrap"><table><tr><th>Contributor lane</th><th>Observed deliverables</th><th>Proof and limits</th></tr>')
for a,b,c in [('Claude Code — PR #50/#51','Labeled Figure 1–10, synthetic demo server, visual OCR/YOLO overlays, PDF and screenshots','No scientific promotions claimed; PR #51 media were separately audited'),
('ChatGPT — independent audit','Original local logistic model PR #14; checkpoint timeline PR #18; judge demo hash reconciliation and this 82-event statistical successor','Cross-checked JSON sources, failure receipts, exact Merkle root and CI; no new external model training'),
('Teammate — PR #4','Initial project spec and Supabase schema','GitHub login attribution by PR author; Supabase live row counts not independently verified'),
('Other multi-agent work','FCO/FCG ablations, YOLO epoch runs, Lean-gate experiments, FCAR admission','Only source-specific records establish provenance; shared GitHub login cannot identify a single agent')]:
 out.append('<tr><td>'+esc(a)+'</td><td>'+esc(b)+'</td><td>'+esc(c)+'</td></tr>')
out.append('</table></div><p>FIGURE NOTE: Demonstration files and annotation assets are entirely synthetic. A historical judge manifest mismatched 10 annotation hashes; the original is preserved, repaired successor is independently verified, and CI enforces all 62/62 asset hashes.</p></section>')
out.append('<footer><div class="mono">Judge outcome root (SHA-256 event commitment, not proof of causality): '+esc(x['outcome_event_root'])+'</div><p>Source evidence and each exact model/epoch checksum: <a href="JUDGE_OUTCOMES_SUCCESSOR_V1.json">JUDGE_OUTCOMES_SUCCESSOR_V1.json</a> · Figures 1–10 and captions: <a href="FIGURES.md">FIGURES.md</a></p></footer></main></body></html>')
path=R/'docs/judges/JUDGE_OUTCOME_HEATMAP_V1.html'
if path.exists():raise FileExistsError('IMMUTABLE_FIGURE_ALREADY_EXISTS')
path.write_text(''.join(out))
print('FIGURE',path.relative_to(R),path.stat().st_size,'BYTES; EPOCHS',sum(len(q['epochs']) for q in x['yolo_training']))
