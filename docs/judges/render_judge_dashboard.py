#!/usr/bin/env python3
"""Static offline judge report from the frozen evidence matrix and figure catalog."""
import html,json
from pathlib import Path
P=Path(__file__).resolve().parent
M=json.loads((P/'ACCOMPLISHMENT_MATRIX_20261102.json').read_text())
F=json.loads((P/'JUDGE_FIGURE_CATALOG.json').read_text())
I=json.loads((P/'IMAGE_CAPTION_INVENTORY.json').read_text())
R=json.loads((P/'PR_CONTRIBUTION_LEDGER.json').read_text())
def esc(x):return html.escape(str(x),quote=True)
def tag(x):return 'tag-'+''.join(c if c.isalnum() else '-' for c in x.lower())
def prlink(n):
 return '<a href="https://github.com/biobitworks/frontier-forms/pull/'+str(n)+'">PR #'+str(n)+'</a>' if isinstance(n,int) else esc(n)
def source(p):
 return '<a href="../../'+esc(p)+'">'+esc(p)+'</a>' if p else '—'
kpis=''.join('<article class="kpi"><span class="eyebrow">'+esc(k['id'])+' · '+esc(k['claim'])+'</span><strong>'+
 esc(k['value'])+'</strong><h3>'+esc(k['title'])+'</h3><p>'+esc(k['denominator'])+'</p><small>'+
 esc(k['caveat'])+'</small><div class="ref">'+source(k['source'])+' · '+prlink(k['pr'])+'</div></article>' for k in M['metrics'])
legend=[('OBSERVED','Measured or checked'),('IMPLEMENTED','Code present; result not assured'),('DISCOVERY','Exploratory/conditional'),('NEGATIVE','No promotion or worse'),('PARTIAL','Not end-to-end'),('NOT_TESTED','No executed test'),('REPORTED','Unverified report'),('DRAFT_ONLY','Open PR; unmerged'),('UNKNOWN','No supported claim')]
legend_html=' '.join('<span class="legend"><b class="'+tag(n)+'"></b>'+esc(n)+' <small>'+esc(d)+'</small></span>' for n,d in legend)
grid='<thead><tr><th scope="col">Capability</th>'+''.join('<th scope="col">'+esc(k)+'</th>' for k in
 ['Teammate','Claude','ChatGPT / independent','Cross-lane admission'])+'</tr></thead><tbody>'
for row in M['matrix']:
 grid+='<tr><th scope="row">'+esc(row['capability'])+'</th>'
 for c in row['cells']:
  grid+='<td class="'+tag(c['state'])+'"><b>'+esc(c['state'])+'</b><span>'+esc(c['detail'])+'</span><small>'+prlink(c['reference'])+'</small></td>'
 grid+='</tr>'
grid+='</tbody>'
rank={'none':0,'M1':1,'M2':2,'M3':3,'M1+M2':4,'M1+M3':5,'M2+M3':6,'M1+M2+M3':7}
factors=sorted(M['detector_factorial'],key=lambda a:rank.get(a['combination'],99))
facrows=''
for d in factors:
 a=d['recall']*100
 facrows+='<tr><th>'+esc(d['combination'])+'</th><td><div class="progress"><i style="width:'+str(round(a,2))+'%"></i></div>'+str(round(a,2))+'%</td><td>'+str(d['false_positive_clean_fields'])+'</td><td>DISCOVERY ONLY</td></tr>'
# Existing raster resources are referenced, not copied or re-encoded.
cards=''
for f in F['figures']:
 isimg=f['asset_kind']=='image' and f['status']!='DRAFT_ONLY'
 show=('<img loading="lazy" src="'+esc(f['href'])+'" alt="'+esc(f['alt'])+'">' if isimg
       else '<div class="file-icon" aria-hidden="true">'+('DRAFT VIEWER' if f['status']=='DRAFT_ONLY' else 'OFFLINE HTML VIEW')+'</div>')
 cards+=('<figure><div class="art">'+show+'</div><figcaption><span class="eyebrow">'+esc(f['id'])+' / '+esc(f['status'])+'</span><h3>'+
 esc(f['title'])+'</h3><p>'+esc(f['caption'])+'</p><small>Work lane: '+esc(f['credited_lane'])+
 ' · '+prlink(f['source_pr'])+'</small><div class="ref"><a href="'+esc(f['href'])+'">Open source figure</a></div></figcaption></figure>')
inventory=''
for i in I['images']:
 inventory+='<tr><td>'+esc(i['image_id'])+'</td><td><a href="'+esc(i['link'])+'">'+esc(i['path'])+'</a></td><td>'+esc(i['caption'])+'</td><td>'+esc(i['credit'])+'</td><td>'+esc(i['status'])+'</td></tr>'
prs=''
for p in sorted(R['pulls'],key=lambda x:x['number']):
 prs+='<tr><td>'+prlink(p['number'])+'</td><td>'+esc(p['title'])+'</td><td>'+esc(p['state'])+'</td><td>'+esc(p['credit'])+'</td></tr>'
css="""*{box-sizing:border-box}body{margin:0;background:#f5f7fa;color:#142238;font:15px/1.48 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1420px;margin:auto;padding:30px 26px 90px}header{background:#0b263e;color:white;border-radius:18px;padding:30px 34px}
header p{max-width:930px;color:#d3e0ed}.eyebrow{font-size:11px;letter-spacing:.09em;text-transform:uppercase;font-weight:700;color:#6382a2}
header .eyebrow{color:#9be6d3}h1{font-size:30px;line-height:1.2;margin:7px 0}h2{font-size:22px;margin:32px 0 13px}
h3{font-size:15px;margin:5px 0}p{margin:6px 0 13px}small{font-size:12px}a{color:#125f9e;text-decoration:none}a:hover{text-decoration:underline}
header .meta{font-size:12px;color:#d2dce4}.sub{color:#526476;max-width:1000px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:11px}
.kpi,figure,.panel{background:white;border:1px solid #d9e3eb;border-radius:13px;padding:16px}
.kpi strong{font-size:31px;display:block;line-height:1.4;color:#102f4a}.kpi p,.kpi small{color:#526476}.ref{font-size:11px;margin-top:10px;overflow-wrap:anywhere}
.legend{display:inline-flex;align-items:center;gap:6px;margin:5px 15px 8px 0;font-size:11px}.legend b{width:13px;height:13px;display:inline-block;border-radius:3px}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:12px}td,th{padding:11px;border-bottom:1px solid #e4e9ed;text-align:left;vertical-align:top}
th{background:#eaf1f6;color:#23455f}thead th{position:sticky;top:0;z-index:1}
.scroll{overflow:auto;max-height:850px;border:1px solid #d9e3eb;border-radius:10px;background:white}
.heatmap{min-width:1020px}.heatmap td{width:23%;border-right:2px solid white}.heatmap td b{display:block;font-size:12px}
.heatmap td span{display:block;margin:6px 0}.heatmap th:first-child{width:22%;min-width:188px}
.tag-observed,.tag-reviewed{background:#d8f0e7}.tag-implemented{background:#dcebf9}
.tag-discovery,.tag-partial,.tag-in-progress,.tag-exploratory{background:#fff0ce}
.tag-negative,.tag-failed{background:#fbdcdb}.tag-not-tested,.tag-unknown{background:#e8ebef}
.tag-reported,.tag-historical{background:#e7e7f4}.tag-draft-only{background:#eadcf7}
.progress{display:inline-block;width:190px;height:9px;vertical-align:middle;margin-right:10px;border-radius:10px;background:#e6eaf0}
.progress i{display:block;background:#2d8d87;height:9px;border-radius:10px}
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(285px,1fr));gap:14px}
figure{margin:0;padding:0;overflow:hidden}figcaption{padding:15px}figcaption p{color:#526476;font-size:13px}
.art{height:210px;background:#eef3f6;display:flex;align-items:center;justify-content:center;overflow:hidden}
.art img{max-width:100%;max-height:100%;object-fit:contain}.file-icon{color:#57708a;font-size:13px;font-weight:700;letter-spacing:.08em}
.note{border-left:4px solid #e29c33;background:#fff7e8;padding:13px 17px;margin-top:14px}
details{background:white;border:1px solid #d9e3eb;border-radius:10px;margin-top:15px;padding:14px}
summary{font-weight:700;cursor:pointer}footer{color:#617186;font-size:12px;margin-top:35px}
@media(max-width:690px){main{padding:10px}header{border-radius:0;padding:24px 17px}h1{font-size:24px}}
@media print{main{max-width:none}header{background:#e5edf5!important;color:black!important}.scroll{max-height:none}.heatmap{font-size:9px}details{display:none}figure{break-inside:avoid}}
"""
body="""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Frontier Forms | Judge evidence and contribution heatmap</title><style>@@CSS@@</style></head><body><main>
<header><div class="eyebrow">Frontier Forms · Judge reference · Frozen PR snapshot</div>
<h1>What was built, what was tested, and what still needs proof</h1>
<p>A source-linked map of the synthetic form-filling program. This visualization separates Claude Code, ChatGPT/independent research, teammate implementation and cross-lane acceptance. An artifact existing in GitHub is not itself evidence of a model gain.</p>
<div class="meta">As-of 2026-11-02 · Main source snapshot: <code>@@SHA@@</code> · @@PRCNT@@ PRs (@@MERGED@@ merged, @@OPEN@@ open, @@CLOSED@@ closed without merge). Does not imply current real-time CI success.</div></header>
<section aria-label="Key measured evidence"><h2>Selected results with denominator and claim ceiling</h2><div class="kpis">@@KPI@@</div></section>
<section><h2>Accomplishment heatmap — contributor × capability</h2><p class="sub">Each cell is an evidence status, not a numerical effect size. The last column is an admission gate, not another contributor.</p><div>@@LEGEND@@</div><div class="scroll"><table class="heatmap">@@GRID@@</table></div>
<div class="note"><strong>Contribution provenance:</strong> PR author handles are often the same shared GitHub account. The Claude and ChatGPT distinctions below reflect documented agent/work lanes and attributable PR descriptions. Unknown authorship is left unknown. No merged code is claimed as work from this report's author unless it was explicitly built in the ChatGPT lane.</div></section>
<section><h2>Merkle × Lean 4 × FCO: detector ablations</h2><p class="sub">Previously stored source numbers: 702 injected synthetic errors; 5,731 clean fields. Bars indicate fault-recall on injected errors, while the third column shows false-positive clean fields. The three mechanisms are not independent causal effects.</p>
<div class="scroll"><table><thead><tr><th>Detector combination</th><th>Fault recall (702 injected)</th><th>False-positive fields (of 5,731)</th><th>Admission</th></tr></thead><tbody>@@FACTOR@@</tbody></table></div>
<p class="sub">M1 = Merkle breakpoint; M2 = Lean constraints; M3 = FCO source binding. Full stack: 98.86% recall and 236 clean-field false positives; adding M1/M2 does not independently improve recall conditional on M3 in this constructed fixture. <a href="../../evidence/forms_detectors/run_v1/DETECTOR_RESULTS_V1.json">Source JSON</a>.</p></section>
<section><h2>Judge figure gallery — explicit captions</h2><p class="sub">All displayed images are pre-existing synthetic artifacts; this gallery references them without modifying or re-uploading pixel bytes. Figure labels identify their experiment owner and limitation. Claude draft viewers are linked but not shown as merged output.</p><div class="gallery">@@GALLERY@@</div></section>
<section><h2>What remains before a defensible demonstration</h2><div class="panel">
<ol><li>Freeze an independent new Synthea cohort and unseen template set before opening answers; score all arms once.</li>
<li>Capture exact local Qwen weights/checkpoints, per-field predictions and FCO evidence bindings; compare B0, Qwen base and completed fine-tuning separately.</li>
<li>Verify HTML/CSS and PDF field placement with geometric OCR or bounding-box matching, not only text appearing somewhere in the PDF.</li>
<li>Complete local trained-vision and prompted-injection validation, including false positives, abstentions, and template holdout.</li>
<li>Reconcile teammate's reported Supabase 100 patients/8,252 facts against an actual read-only snapshot, or label that lane out of scope.</li>
<li>Preserve legacy publication exceptions as historical policy debt. Check required CI status and owner sign-offs before any new merge.</li>
<li>Keep actual Epic writeback and real-world clinical efficacy labeled NOT_TESTED until authorized and separately validated. No hosted inference in this lane.</li></ol></div></section>
<details><summary>Complete labeled image inventory (@@IMGCOUNT@@ main assets)</summary><p class="sub">Auto-labeled using file path and workflow provenance, not manual pixel inspection. Each image has an individual stable ID and caption. Historic PNG files may be grandfathered by the repository's exact-byte policy, but they are not newly published by this report.</p><div class="scroll"><table><thead><tr><th>Figure ID</th><th>Original image</th><th>Label / scientific limitation</th><th>Source lane</th><th>State</th></tr></thead><tbody>@@INVENTORY@@</tbody></table></div></details>
<details><summary>Full PR ledger (@@PRCNT@@ snapshot PRs)</summary><p class="sub">A PR marked MERGED means code reached a branch, not that every experiment passed. Click a PR to inspect its exact source and commits.</p><div class="scroll"><table><thead><tr><th>PR</th><th>Title</th><th>GitHub state</th><th>Documented work lane</th></tr></thead><tbody>@@PRROWS@@</tbody></table></div></details>
<footer>Sources: frozen repository JSON and GitHub PR head snapshots; no new scientific experiments or cryptographic roots computed for this dashboard. Publication: local-only images and weights remain unchanged. Figure/asset inventories and matrix JSON ship with this report.</footer>
</main></body></html>"""
replacements={'@@CSS@@':css,'@@SHA@@':esc(M['parent_main_sha']),'@@PRCNT@@':str(M['pr_count']),
 '@@MERGED@@':str(M['pr_snapshot']['MERGED']),'@@OPEN@@':str(M['pr_snapshot']['OPEN']),
 '@@CLOSED@@':str(M['pr_snapshot']['CLOSED']),'@@KPI@@':kpis,'@@LEGEND@@':legend_html,
 '@@GRID@@':grid,'@@FACTOR@@':facrows,'@@GALLERY@@':cards,'@@INVENTORY@@':inventory,
 '@@IMGCOUNT@@':str(I['main_images']),'@@PRROWS@@':prs}
for k,v in replacements.items():body=body.replace(k,v)
assert '@@' not in body
(P/'JUDGES_EVIDENCE_HEATMAP_20261102.html').write_text(body)
print('RENDERED',len(body),'bytes','assets',len(I['images']),'figures',len(F['figures']),'prs',len(R['pulls']))
