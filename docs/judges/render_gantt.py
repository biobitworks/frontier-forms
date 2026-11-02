#!/usr/bin/env python3
"""Self-contained local HTML gantt; PR intervals are GitHub review time, not training runtime."""
import json,html,datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo
P=Path(__file__).resolve().parent
data=json.loads((P/'FRONTIER_FORMS_GANTT_EVIDENCE_20261102.json').read_text())
p=dt.timezone.utc;pt=ZoneInfo('America/Los_Angeles')
def t(v):return dt.datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()
def h(v):return html.escape(str(v),quote=True)
def when(v):return dt.datetime.fromtimestamp(t(v),pt).strftime('%-I:%M:%S %p PT')
events=data['events']; start=min(t(x['start_utc']) for x in events)-75;end=max(t(x['end_utc']) for x in events)+75
R=end-start
def pct(ts):return max(0,min(100,(t(ts)-start)/R*100))
lanes=['Teammate / app','Claude Code / red-team','ChatGPT / independent','Security / integration','Mixed / attribution uncertain','Dataset milestones','Model / OCR receipts','Governance / promotion']
def group(e):return 0 if e['kind']=='pull_request' and e['state']=='MERGED' else 1 if e['kind']=='pull_request' else 2
def short(e):
 return e['title'] if len(e['title'])<98 else e['title'][:95]+'...'
bars=[]
for lane in lanes:
 arr=sorted((x for x in events if x['lane']==lane),key=lambda x:(group(x),t(x['start_utc'])))
 if not arr:continue
 bars.append('<div class="lane"><div class="lane-name">'+h(lane)+' <small>'+str(len(arr))+' items</small></div>')
 for x in arr:
  pos=pct(x['start_utc'])
  span=max(.35,pct(x['end_utc'])-pos) if x['kind']!='data_model_milestone' else .7
  state=x['state'];css='is-pr' if x['kind']=='pull_request' else 'is-milestone'
  if x.get('kind')=='receipt_interval':css='is-run'
  if state in ('OPEN','CLOSED'):css+=' is-unmerged'
  if 'NEGATIVE' in state:css+=' is-negative'
  if 'HOLD' in state or 'BASELINE_ONLY' in state:css+=' is-hold'
  st='left:'+str(round(pos,3))+'%;width:'+str(round(span,3))+'%;'
  target=x.get('url') or ('../../'+x['source_path'] if x.get('source_path','').startswith(('evidence/','dashboard/','data/')) else '')
  detail=' | '.join([state,x['timestamp_basis'],when(x['start_utc'])] + ([when(x['end_utc'])] if x['start_utc']!=x['end_utc'] else []) + [x.get('note','')])
  bars.append('<div class="gantt-row"><div class="row-title"><a href="'+h(target or '#')+'">'+h(short(x))+
   '</a><small>'+h(state)+' · '+h(when(x['start_utc']))+'</small></div><div class="track" role="img" aria-label="'+
   h(detail)+'"><span class="bar '+css+'" style="'+st+'" title="'+h(detail)+'"></span></div></div>')
 bars.append('</div>')
tick=dt.datetime.fromtimestamp(start,pt).replace(minute=0,second=0,microsecond=0)
ticks=[]
while tick.timestamp()<=end:
 x=max(0,min(100,(tick.timestamp()-start)/R*100))
 ticks.append('<div class="tick" style="left:'+str(round(x,3))+'%"><span>'+tick.strftime('%-I %p')+'</span></div>')
 tick+=dt.timedelta(hours=1)
gate_rows=[]
for g in data['gates']:
 state=g['status']
 color='neg' if state.startswith('NEGATIVE') else 'positive' if state.startswith('DISCOVERY_POSITIVE') else 'unverified'
 delta=g.get('delta')
 delta_str=('+' if delta>0 else '')+f'{delta*100:.2f} pp' if isinstance(delta,(int,float)) else '—'
 gate_rows.append('<tr class="'+color+'"><td>'+h(g['id'])+'</td><td>'+h(g['family'])+'</td><td>'+
  h(state)+'</td><td class="num">'+h(delta_str)+'</td><td>'+('YES' if g.get('promoted') is True else 'NO' if g.get('promoted') is False else 'UNKNOWN')+'</td></tr>')
indexrows=[]
for x in data['indexed_existing_public_json_sources']:
 indexrows.append('<tr><td><a href="'+h('../../'+x['path'])+'">'+h(x['path'])+'</a></td><td>'+h(x['family'])+
  '</td><td><code>'+h(x['git_blob_sha1'][:12])+'</code></td></tr>')
css="""*{box-sizing:border-box}body{background:#f5f7fa;color:#172c3f;font:14px/1.45 -apple-system,system-ui,Segoe UI,sans-serif;margin:0}
main{max-width:1700px;margin:auto;padding:24px 25px 65px}h1{font-size:28px;margin:8px 0}h2{font-size:22px;margin:24px 0 8px}
p{max-width:1100px;color:#4a5f72}a{color:#195e99;text-decoration:none}a:hover{text-decoration:underline}
.hero{padding:24px 30px;color:white;border-radius:16px;background:#113550}.hero p{color:#c7dce9}.eyebrow{font-weight:800;letter-spacing:.11em;text-transform:uppercase;font-size:11px;color:#79dbc6}
.legend{display:flex;flex-wrap:wrap;gap:15px;margin:12px 0}.legend span{font-size:12px}.legend i{display:inline-block;height:11px;width:22px;margin-right:6px;vertical-align:middle;border-radius:5px}
.kpis{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}.kpi{border:1px solid #d8e3e8;border-radius:12px;background:white;min-width:130px;padding:13px}.kpi strong{display:block;font-size:25px}.kpi span{font-size:12px;color:#63788c}
.gantt{background:white;border:1px solid #d6e1e9;border-radius:14px;padding:14px 16px;margin-top:13px;overflow:hidden}
.axis{height:33px;display:flex}.axis-label{flex:0 0 330px}.axis-track{flex:1;position:relative;border-bottom:1px solid #d5e0e5}.tick{height:100%;position:absolute;top:0;border-left:1px solid #d9e3ed}.tick span{position:absolute;top:0;left:4px;color:#557188;font-size:11px;white-space:nowrap}
.lane{padding-bottom:14px;border-bottom:1px solid #e6edf2;margin-top:15px}.lane-name{padding:5px 0;background:#eaf1f5;font-weight:750;margin-bottom:5px}.lane-name small{font-weight:450;color:#53738c}
.gantt-row{display:flex;align-items:center;min-height:34px;border-bottom:1px solid #f2f4f7}.row-title{flex:0 0 330px;padding:3px 8px 3px 0;font-size:12px;overflow-wrap:anywhere}
.row-title small{display:block;font-size:10px;color:#637b8d}
.track{flex:1;height:27px;position:relative;background:repeating-linear-gradient(to right,#eef2f6 0px,#eef2f6 1px,white 1px,white 16.66%)}
.bar{height:16px;min-width:6px;position:absolute;top:5px;border-radius:4px;background:#377caa;cursor:help}
.bar.is-run{background:#34918b}.bar.is-milestone{background:#e1a13a}.bar.is-negative{background:#c75759}
.bar.is-hold{background:#8a72a7}.bar.is-unmerged{background:#8f9aa4;box-shadow:inset 0 0 0 2px #485b6a}
.info{background:#fff5df;border-left:4px solid #c68a27;padding:12px 16px;margin:15px 0;max-width:1250px}
.panel{background:white;border:1px solid #d6e1e9;border-radius:14px;padding:13px}
.scroll{max-height:620px;overflow:auto}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:7px 10px;border-bottom:1px solid #e2e9ee;text-align:left}th{background:#eaf1f5;position:sticky;top:0}
tr.neg td:nth-child(3){background:#fce2e2}tr.positive td:nth-child(3){background:#e1f1df}tr.unverified td:nth-child(3){background:#eff1f4}
.num{text-align:right;font-variant-numeric:tabular-nums}.small{font-size:11px;color:#647b8b}
@media(max-width:950px){main{padding:9px}.axis-label,.row-title{flex-basis:190px;font-size:10px}.tick span{font-size:9px}.hero{padding:17px}}
"""
html_doc="""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Frontier Forms · PR, Model & Dataset Gantt</title>
<style>@@CSS@@</style></head><body><main>
<header class="hero"><div class="eyebrow">Frontier Forms | Evidence Timeline | 2026-11-02</div>
<h1>What each lane delivered—and when</h1>
<p>Source-based GitHub PR timelines and timestamped synthetic dataset/model receipts. Actual performance and promotion statuses are separate from Git merge statuses. This is a frozen snapshot, not a live dashboard.</p>
<div class="small">GitHub snapshot cutoff: @@ASOF@@ · All bars Pacific Time (PST, UTC−08:00) · UTC evidence in companion JSON</div></header>
<div class="kpis">@@KPI@@</div>
<h2>Gantt — PRs, datasets, and local models</h2>
<div class="info"><b>How to read:</b> Blue bars run from PR creation to Git merge, gray outlined bars run from PR creation to close/snapshot, teal bars are actual source-bounded model runtime when both timestamps exist, and gold ticks denote a single recorded timestamp or a PR-created proxy. Purple means HOLD and red means a negative result. Hover over each bar for its exact clock basis. <b>No bar implies when a person started coding.</b></div>
<div class="legend"><span><i style="background:#377caa"></i>PR merged</span><span><i style="background:#8f9aa4;border:2px solid #485b6a"></i>PR unmerged</span><span><i style="background:#34918b"></i>Recorded model runtime</span><span><i style="background:#e1a13a"></i>Recorded milestone/proxy</span><span><i style="background:#c75759"></i>Negative</span><span><i style="background:#8a72a7"></i>HOLD</span></div>
<div class="gantt"><div class="axis"><div class="axis-label">Work lane / event</div><div class="axis-track">@@TICKS@@</div></div>@@BARS@@</div>
<h2>Scientific promotion and negative-result register</h2>
<div class="panel"><p><b>@@PROMOTIONS@@ actual scientific promotions</b> in 24 existing tracked ablation/training events; @@DISCOVERY@@ discovery-positive <b>not promoted</b>; @@NEGATIVE@@ negative/tie; remaining records are baseline or methodology snapshots. No new efficacy/latency/cost or clinical-superiority claim is admitted by this report.</p>
<div class="scroll"><table><thead><tr><th>Source event</th><th>Lane</th><th>Observed status</th><th>Paired metric delta</th><th>Promoted?</th></tr></thead><tbody>@@GATES@@</tbody></table></div>
<p class="small">Source: <a href="../../dashboard/training_progress_latest.json">training_progress_latest.json</a>; delta units = percentage points for reported proportion metrics; a negative/positive result is not automatically a clinically meaningful change.</p></div>
<h2>Source data inventory (all existing public JSON sources)</h2>
<div class="panel"><p>This view indexes @@SOURCES@@ existing Git-tracked JSON evidence/data files by path and Git blob identity; it <b>does not</b> copy or newly publish their content. Historical JSONL, PNG and PDFs remain separately controlled by the repository policy; private oracle and trained weights are excluded. Git blob SHA-1 establishes file identity, not truth.</p>
<div class="scroll"><table><thead><tr><th>Exact source file (open)</th><th>Evidence family</th><th>Git blob ID prefix</th></tr></thead><tbody>@@INDEX@@</tbody></table></div></div>
<h2>Immediate teammate evidence requests</h2>
<div class="panel"><p>Please add missing implementation screenshots, synthetic FHIR data source details, model name + digest, when each run was executed, and a correct/incorrect field-level readback receipt directly to an appropriate PR. Separate <b>implemented</b>, <b>executed</b>, <b>observed</b>, <b>negative</b>, and <b>not tested</b>. For anything not ready before 4:30 PM PT, mark it as pending rather than claiming completion. Do not publish weights, PHI, credentials or unapproved raw images.</p>
<p><a href="FRONTIER_FORMS_GANTT_REQUESTS_20261102.md">Copyable reviewer request and lane owners</a> · <a href="FRONTIER_FORMS_GANTT_EVIDENCE_20261102.json">Machine-readable event history and promotion register</a></p></div>
<footer class="small">Source-bound snapshot; no model trained, test re-executed, or new Merkle root computed to construct this chart. PR merge ≠ scientific promotion. Open bars are clipped to snapshot cutoff.</footer>
</main></body></html>"""
counts=data['pr_counts'];kpi=[('GitHub PRs',len([x for x in events if x['kind']=='pull_request'])),('Merged PRs',counts['MERGED']),('Open PRs',counts['OPEN']),('Closed, not merged',counts['CLOSED']),('Dataset & model milestones',len(events)-len([x for x in events if x['kind']=='pull_request'])),('Scientific promotions',data['scientific_promotions_in_24_training_events']),('Negative or ties',data['negative_or_tie_events'])]
kpi_html=''.join('<div class="kpi"><strong>'+h(v)+'</strong><span>'+h(k)+'</span></div>' for k,v in kpi)
rep={'@@CSS@@':css,'@@ASOF@@':dt.datetime.fromtimestamp(t(data['snapshot_utc']),pt).strftime('%-I:%M:%S %p PT'),'@@KPI@@':kpi_html,'@@TICKS@@':''.join(ticks),'@@BARS@@':''.join(bars),'@@PROMOTIONS@@':str(data['scientific_promotions_in_24_training_events']),'@@DISCOVERY@@':str(data['discovery_positives_not_promoted']),'@@NEGATIVE@@':str(data['negative_or_tie_events']),'@@GATES@@':''.join(gate_rows),'@@SOURCES@@':str(len(data['indexed_existing_public_json_sources'])),'@@INDEX@@':''.join(indexrows)}
for k,v in rep.items():html_doc=html_doc.replace(k,v)
assert '@@' not in html_doc
(P/'FRONTIER_FORMS_GANTT_20261102.html').write_text(html_doc)
print('RENDER_PASS',len(html_doc),'bytes,',len(events),'events,',len(gate_rows),'gate rows')
