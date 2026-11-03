#!/usr/bin/env python3
"""Frozen, source-backed PR Gantt and per-epoch training timeline.

--write: create immutable JSON + two PNGs using Pillow (local build).
--verify (default): stdlib-only check of the committed source JSON and PNG headers.

Read the PR calendar as a *GitHub administrative timeline* rather than the
amount of time a person or training job worked. Epoch chart x=epoch, not clock.
"""
from __future__ import annotations
import argparse,collections,datetime,hashlib,json,struct
from pathlib import Path
from zoneinfo import ZoneInfo
R=Path(__file__).resolve().parents[1]
F=R/'docs/judges/figures'
PR='docs/judges/FINAL_PR_SNAPSHOT_20261102_V3.json'
OUT='docs/judges/FINAL_JUDGE_LANE_TRAINING_TIMELINE_V1.json'
GANTT='docs/judges/figures/fig18_pr_contributor_gantt_20261102.png'
TRAIN='docs/judges/figures/fig19_actual_training_epochs_20261102.png'
SOURCE=[
 PR,
 'evidence/forms_detector/V2-yolov8n/summary.json',
 'evidence/forms_detector/V2-yolov8n/receipt.json',
 'evidence/redteam/detector/full/epoch_ledger.jsonl',
 'evidence/redteam/detector/full/chain_manifest.json',
 'evidence/redteam/detector/no_scan/epoch_ledger.jsonl',
 'evidence/redteam/detector/no_scan/chain_manifest.json',
 'docs/judges/JUDGE_OUTCOMES_SUCCESSOR_V1.json',
 'docs/judges/OCR_CORRECTION_SUCCESSOR_V2.json'
]
SHA=lambda b:hashlib.sha256(b).hexdigest()
READ=lambda p:(R/p).read_bytes()
JSON=lambda p:json.loads(READ(p))
PST=ZoneInfo('America/Los_Angeles')
def stamp(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(PST)
CLAUDE={50,51,57,58,62,63,69,70,72,75}
CHATGPT={14,15,16,18,55,59,64,71,74}
TEAM={4}
LANES=['Teammate / app','Claude Code / models','ChatGPT / independent','Mixed / attribution unknown']
def lane(n):
    if n in TEAM:return LANES[0]
    if n in CLAUDE:return LANES[1]
    if n in CHATGPT:return LANES[2]
    return LANES[3]
def construct():
    p=JSON(PR)
    prs=p['prs']
    assert len(prs)>=60
    assert len({a['number'] for a in prs})==len(prs)
    assert all(a['createdAt'] for a in prs)
    state_count=dict(collections.Counter(a['state'] for a in prs))
    v2=JSON('evidence/forms_detector/V2-yolov8n/summary.json')
    receipt=JSON('evidence/forms_detector/V2-yolov8n/receipt.json')
    assert len(v2['losses_per_epoch'])==receipt['epochs_run']==40
    assert receipt['images_by_split']['test']==108 and receipt['device']=='mps'
    assert [int(a['epoch']) for a in v2['losses_per_epoch']]==list(range(1,41))
    old={}
    for key in ('full','no_scan'):
        base='evidence/redteam/detector/'+key+'/'
        events=[json.loads(line) for line in READ(base+'epoch_ledger.jsonl').decode().splitlines()]
        m=JSON(base+'chain_manifest.json')
        assert len(events)==30 and [e['epoch'] for e in events]==list(range(1,31))
        assert all(e.get('utc') for e in events)
        old[key]={
          'chain_root_recorded':m['root'],
          'epochs':[{'epoch':e['epoch'],'utc':e['utc'],
              'dev_image_pass':e['dev_pass'],'dev_image_total':e['dev_images'],
              'status':e['status'],'weights_sha256_recorded':e['weights_sha256']}
             for e in events],
          'state_counts':dict(collections.Counter(e['status'] for e in events)),
          'metric':'complete_dev_image_pass_rate (44 synthetic development renders)',
          'not_patient_replication':True
        }
    fco=JSON('docs/judges/JUDGE_OUTCOMES_SUCCESSOR_V1.json')['fco']['strongest_discovery']
    ocr=JSON('docs/judges/OCR_CORRECTION_SUCCESSOR_V2.json')
    arms={a['arm']:a for a in ocr['arms']}
    assert (fco['baseline'],fco['candidate'],fco['n'])==(18,30,54)
    assert (arms['A1']['baseline_all7'],arms['A1']['challenger_all7'])==(14,22)
    assert arms['A1']['p_holm_3_comparisons']==0.0234375
    return {
      'schema':'frontier-forms.judge-contributors-and-training-results.v1',
      'synthetic_only':True,
      'snapshot_utc':p['observed_at_utc'],
      'source_parent_main_sha':p['main_parent_git_sha'],
      'deadline_pacific':p['event_deadline_pacific'],
      'deadline_claim':'Review successor. PR merges after cutoff are not evidence of an eligible submitted version.',
      'source_file_sha256':{s:SHA(READ(s)) for s in SOURCE},
      'github_pr_count':len(prs),'github_pr_status_counts':state_count,
      'pr_time_basis':'actual GitHub PR createdAt to mergedAt/closedAt; NOT actual human work or GPU time',
      'contributor_attribution_basis':'known PR description / observed ChatGPT tool session only; all other work mixed/unverified',
      'pr_events':[{'number':a['number'],'created_utc':a['createdAt'],
        'merged_utc':a['mergedAt'],'closed_utc':a['closedAt'],'state':a['state'],
        'lane':lane(a['number']),'title':a['title'],'url':a['url']}
        for a in prs],
      'older_yolo_30_epochs':old,
      'new_yolo_v2_40_epochs':{
        'metric':'validation mAP50-95(B), by integer training epoch; NOT wall-clock duration',
        'epochs':[{'epoch':int(a['epoch']),'map50_95':a['metrics/mAP50-95(B)'],
          'map50':a['metrics/mAP50(B)'],
          'val_box_loss':a['val/box_loss']} for a in v2['losses_per_epoch']],
        'device':'MacBookPro Apple Silicon MPS (per source receipt)',
        'train_images':receipt['images_by_split']['train'],
        'validation_images':receipt['images_by_split']['validation'],
        'test_images':receipt['images_by_split']['test'],
        'weights_sha256_recorded':receipt['trained_weights_sha256'],
        'checkpoint_file_not_published':receipt['weights_published'] is False,
        'per_epoch_utc':'NOT_RECORDED_IN_V2_SUMMARY',
        'held_out_layout_test':{
           'box_recall_iou50':v2['held_out_layout_test']['box_recall_iou50'],
           'class_accuracy_matched':v2['held_out_layout_test']['class_accuracy_matched'],
           'false_flag_rate':v2['held_out_layout_test']['validator']['false_flag_rate'],
           'flag_recall':v2['held_out_layout_test']['validator']['flag_recall'],
           'images':v2['held_out_layout_test']['images']
        }
      },
      'fco_full_form':{'baseline':fco['baseline'],'challenger':fco['candidate'],'n':54,
          'delta_pp':100*(fco['candidate']-fco['baseline'])/54,
          'type':'deterministic source-context leaf ablation, not new neural weights'},
      'ocr_all_seven_fields':{'baseline':14,'correction':22,
          'detector_crops':arms['A2']['challenger_all7'],
          'crops_plus_correction':arms['A3']['challenger_all7'],
          'n':46,'holm_p':arms['A1']['p_holm_3_comparisons'],
          'type':'fitted OCR post-correction table, not neural SFT'},
      'qwen_lora_comparative_gain':'NOT_COMPUTED_FROM_FROZEN_PAIRED_CHECKPOINTS',
      'scientific_promotions':0,
      'model_claims':'V2 trained detector high box recall BUT held-out class accuracy and high validator false flags; do not conflate bounding boxes with field-value correctness',
      'reference_roots':{
         'older_30_epoch_full':old['full']['chain_root_recorded'],
         'older_30_epoch_no_scan':old['no_scan']['chain_root_recorded'],
         'ocr_three_arm_successor':ocr['ocr_event_root']
      },
      'figure_files':[GANTT,TRAIN],
      'png_sha256':{},
    }

def png_ok(path):
    raw=READ(path)
    if raw[:8]!=bytes([137,80,78,71,13,10,26,10]):raise AssertionError('BAD_PNG_SIGNATURE:'+path)
    if raw[12:16]!=b'IHDR':raise AssertionError('PNG_IHDR_MISSING')
    w,h=struct.unpack('>II',raw[16:24])
    if w<1400 or h<700:raise AssertionError('PNG_TOO_SMALL:'+path)
    return w,h

def verify():
    saved=JSON(OUT)
    actual=construct()
    for k in saved:
        if k!='png_sha256':
            assert saved[k]==actual[k], 'FROZEN_SOURCE_DRIFT_'+k
    assert saved['scientific_promotions']==0
    assert saved['new_yolo_v2_40_epochs']['per_epoch_utc']=='NOT_RECORDED_IN_V2_SUMMARY'
    assert saved['github_pr_count']==len(saved['pr_events'])
    for path in (GANTT,TRAIN):
        assert SHA(READ(path))==saved['png_sha256'][path], 'PNG_SHA_DRIFT_'+path
        png_ok(path)
    return {'status':'PASS','prs':saved['github_pr_count'],
        'training_epochs':40+30+30,'scientific_promotions':0,
        'snapshot_utc':saved['snapshot_utc'],
        'figure_sha256':saved['png_sha256']}

def graphics(d):
    from PIL import Image,ImageDraw,ImageFont
    DARK='#112944';NAVY='#173552';BLU='#307cb5';CYAN='#0c9baf'
    GREEN='#16916e';ORANGE='#d98634';RED='#bd4766';GREY='#8196aa'
    BG='#f7faff';TXT='#193047';GRID='#dfe7f1';PURPLE='#6f65b9'
    ARIAL='/System/Library/Fonts/Supplemental/Arial.ttf'
    BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
    def font(n,bold=False):
        path=BOLD if bold else ARIAL
        return ImageFont.truetype(path,n)
    def text(draw,xy,s,n=22,color=TXT,bold=False):
        draw.text(xy,str(s),font=font(n,bold),fill=color)
    # Figure 18 — actual PR windows, 4 lanes
    W,H=1920,1020
    im=Image.new('RGB',(W,H),BG);q=ImageDraw.Draw(im)
    q.rounded_rectangle((24,20,W-24,H-22),radius=24,fill='white',outline=GRID,width=2)
    q.rounded_rectangle((24,20,W-24,144),radius=23,fill=DARK)
    q.rectangle((24,100,W-24,144),fill=DARK)
    text(q,(55,47),'Frontier Forms | Contributor & PR timeline',37,'#ffffff',True)
    text(q,(56,108),'Source: exact GitHub PR created → merged timestamps | after-cutoff commits are review successors, not submission proof',19,'#cbdbe9')
    x0,x1=306,1735;y0=215;step=105
    start=datetime.datetime(2026,11,2,11,45,tzinfo=PST)
    end=datetime.datetime(2026,11,2,16,45,tzinfo=PST)
    cutoff=datetime.datetime(2026,11,2,16,30,tzinfo=PST)
    def xpos(dt):
        return int(x0+(x1-x0)*(dt-start).total_seconds()/(end-start).total_seconds())
    q.rectangle((xpos(cutoff),175,x1,725),fill='#fff3f3')
    for h in [12,13,14,15,16]:
        for minute in [0,30]:
            dt=datetime.datetime(2026,11,2,h,minute,tzinfo=PST)
            if dt<start or dt>end:continue
            x=xpos(dt)
            q.line((x,192,x,727),fill=GRID,width=2)
            text(q,(x-24,167),dt.strftime('%I:%M').lstrip('0'),16,GREY)
    q.line((xpos(cutoff),180,xpos(cutoff),735),fill=RED,width=3)
    text(q,(xpos(cutoff)-148,738),'4:30 PM deadline',19,RED,True)
    colors=[PURPLE,CYAN,GREEN,ORANGE]
    labels=[
     ('Teammate / app','Source app/spec + Supabase lane'),
     ('Claude Code / models','Local model, OCR, screenshots, red team'),
     ('ChatGPT / independent','Paired stats, negative controls, receipts'),
     ('Mixed / attribution unknown','Joint development or no reliable agent attribution'),
    ]
    ps=d['pr_events']
    for i,(lab,sub) in enumerate(labels):
        y=y0+step*i
        q.rounded_rectangle((55,y-16,1870,y+80),radius=12,fill='#f3f6fb' if i%2==0 else '#fafbfe')
        text(q,(66,y+2),lab,20,colors[i],True)
        text(q,(66,y+33),sub,13,GREY)
        lane_events=sorted((p for p in ps if p['lane']==lab),key=lambda p:p['created_utc'])
        for j,p in enumerate(lane_events):
            st=stamp(p['created_utc'])
            et=stamp(p['merged_utc'] or p['closed_utc'] or d['snapshot_utc'])
            a=max(x0,min(x1,xpos(st)));b=max(x0,min(x1,xpos(et)))
            yy=y+5+((j%4)*17)
            color=colors[i] if p['state']=='MERGED' else GREY
            q.rounded_rectangle((a,yy,max(a+7,b),yy+10),radius=4,fill=color)
            if p['state']!='MERGED':q.rectangle((a,yy,max(a+7,b),yy+10),outline=RED,width=2)
        text(q,(1742,y+7),str(len(lane_events))+' PRs',17,colors[i],True)
    text(q,(62,662),'Colored bars = PR creation-to-merge window; not GPU runtime or measured engineering effort.',18,TXT)
    text(q,(62,693),'Unverified agent ownership stays in Mixed. Open/closed-unmerged PRs are outlined, not counted as shipped.',16,GREY)
    q.line((55,801,1870,801),fill=GRID,width=2)
    text(q,(60,820),'Named milestones (actual merge time, Pacific)',23,DARK,True)
    key_ids=[4,10,18,51,64,69,71,75]
    short={4:'Team project spec',10:'Synthetic forms + B0',18:'Longitudinal stats',51:'OCR trained correction',
      64:'Independent audit',69:'Red-team admission',71:'89-leaf evidence',75:'V2 trained YOLO'}
    lookup={p['number']:p for p in ps}
    for i,n in enumerate(key_ids):
        p=lookup.get(n)
        if not p or not p['merged_utc']:continue
        col=i%4;row=i//4
        xx=62+460*col;yy=864+55*row
        q.rounded_rectangle((xx,yy,xx+446,yy+42),radius=8,fill='#edf4fa')
        text(q,(xx+12,yy+8),'#'+str(n)+'  '+stamp(p['merged_utc']).strftime('%H:%M')+'  '+short[n],17,DARK,True)
    im.save(R/GANTT,optimize=True)
    # Figure 19 — same dataset comparisons are separate from training epochs.
    W,H=1920,1380
    im=Image.new('RGB',(W,H),BG);q=ImageDraw.Draw(im)
    q.rounded_rectangle((24,20,W-24,H-18),radius=23,fill='white',outline=GRID,width=2)
    q.rounded_rectangle((24,20,W-24,142),radius=22,fill=DARK)
    q.rectangle((24,110,W-24,142),fill=DARK)
    text(q,(56,47),'Frontier Forms | Training results through checkpoints',35,'#ffffff',True)
    text(q,(58,104),'Different runs have different units: do not connect epoch mAP, form success, or diagnostic flag rates.',19,'#cbdbe9')
    def panel(xa,ya,xb,yb,title,subtitle):
        q.rounded_rectangle((xa,ya,xb,yb),radius=16,fill='#f6f9fd',outline=GRID,width=2)
        text(q,(xa+25,ya+19),title,23,DARK,True)
        text(q,(xa+25,ya+55),subtitle,16,GREY)
    panel(55,170,1860,535,'A. New 40-epoch YOLOv8n (MacBookPro MPS)','X = recorded epoch index (not wall-clock); Y = validation mAP50–95 for field boxes')
    def lineplot(pts,xmin,xmax,ymin,ymax,rect,color):
        ax,ay,bx,by=rect
        for i in range(6):
            xx=ax+(bx-ax)*i/5
            q.line((xx,ay,xx,by),fill=GRID,width=1)
        for i in range(5):
            yy=by-(by-ay)*i/4
            q.line((ax,yy,bx,yy),fill=GRID,width=1)
            text(q,(ax-59,yy-12),str(round(ymin+(ymax-ymin)*i/4,2)),15,GREY)
        points=[(int(ax+(bx-ax)*(x-xmin)/(xmax-xmin)),
                 int(by-(by-ay)*(y-ymin)/(ymax-ymin))) for x,y in pts]
        for a,b in zip(points,points[1:]):q.line((a[0],a[1],b[0],b[1]),fill=color,width=4)
        for x,y in points:
            q.ellipse((x-3,y-3,x+3,y+3),fill=color)
        return points
    ep=d['new_yolo_v2_40_epochs']['epochs']
    xy=lineplot([(e['epoch'],e['map50_95']) for e in ep],1,40,0,1,(155,281,1300,473),BLU)
    for tick in [1,5,10,15,20,25,30,35,40]:
        xx=int(155+(1300-155)*(tick-1)/39)
        text(q,(xx-12,487),str(tick),15,GREY)
    q.rounded_rectangle((1360,261,1820,488),radius=11,fill='#e6f3f8')
    hl=d['new_yolo_v2_40_epochs']['held_out_layout_test']
    text(q,(1380,281),'108 synthetic test renders',23,DARK,True)
    text(q,(1380,323),'Held-out layout (36 images):',18,TXT)
    text(q,(1380,354),'Box recall  '+format(hl['box_recall_iou50']*100,'.2f')+'%',21,GREEN,True)
    text(q,(1380,388),'Class accuracy  '+format(hl['class_accuracy_matched']*100,'.2f')+'%',21,ORANGE,True)
    text(q,(1380,422),'False-flag rate  '+format(hl['false_flag_rate']*100,'.2f')+'%',21,RED,True)
    text(q,(1380,456),'OCR value validation remains PARTIAL',16,RED)
    panel(55,555,1860,890,'B. Older 30-epoch full and no-scan detector ablations','X = epoch; Y = complete development-image success (44 synthetic renders per epoch). Gains and losses both retained.')
    def curve_for(key):
        return [(e['epoch'],e['dev_image_pass']/e['dev_image_total']) for e in d['older_yolo_30_epochs'][key]['epochs']]
    top=(155,658,1374,828)
    # Draw two curves with same axes; first curve includes grid
    a=lineplot(curve_for('full'),1,30,0,1,top,CYAN)
    # Draw second only lines (avoid overdrawing grid)
    xy2=curve_for('no_scan');ax,ay,bx,by=top
    arr=[(int(ax+(bx-ax)*(x-1)/29),int(by-(by-ay)*y)) for x,y in xy2]
    for aa,bb in zip(arr,arr[1:]):q.line((aa[0],aa[1],bb[0],bb[1]),fill=PURPLE,width=4)
    for x,y in arr:q.ellipse((x-3,y-3,x+3,y+3),fill=PURPLE)
    for tick in [1,5,10,15,20,25,30]:
        xx=int(155+(1374-155)*(tick-1)/29)
        text(q,(xx-12,842),str(tick),15,GREY)
    q.rounded_rectangle((1422,654,1810,830),radius=11,fill='#eaf2fc')
    text(q,(1442,669),'Full arm: 3 gains / 3 losses',19,CYAN,True)
    text(q,(1442,704),'No-scan: 3 gains / 1 loss',19,PURPLE,True)
    text(q,(1442,746),'Neutral epochs are retained.',17,TXT)
    text(q,(1442,782),'These are DEV checks, not clinical gains.',16,GREY)
    panel(55,917,1860,1225,'C. Paired synthetic discoveries (not YOLO training improvements)','Separate outcomes: same-case full-form success vs seven-field OCR completion. Do not combine denominators.')
    def contrast(y,label,b,a,den,color):
        text(q,(90,y),label,20,DARK,True)
        text(q,(90,y+30),f'{b}/{den} baseline',16,GREY)
        left,right=530,1395;width=right-left
        q.rounded_rectangle((left,y+5,right,y+28),radius=9,fill='#e3e9f0')
        q.rounded_rectangle((left,y+5,left+int(width*b/den),y+28),radius=9,fill=GREY)
        q.rounded_rectangle((left,y+40,right,y+63),radius=9,fill='#e3e9f0')
        q.rounded_rectangle((left,y+40,left+int(width*a/den),y+63),radius=9,fill=color)
        text(q,(1420,y+10),f'{a}/{den} challenger',18,color,True)
        text(q,(1420,y+41),f'+{(a-b)/den*100:.2f} pp',21,color,True)
    contrast(1000,'FCO L1×L3 clinical filtering',18,30,54,GREEN)
    contrast(1107,'Fitted OCR text correction',14,22,46,BLU)
    text(q,(65,1250),'No DAISY model/data transfer. Qwen-LoRA paired gain NOT_COMPUTED. FCAR scientific admission: HOLD (0 promotions).',20,RED,True)
    text(q,(65,1286),'All cohorts synthetic. Source receipts, exact PR times, test splits, checkpoint SHA and null/negative results: FINAL_JUDGE_LANE_TRAINING_TIMELINE_V1.json',16,GREY)
    text(q,(65,1324),'Snapshot assembled AFTER 4:30 PM deadline; no inference about what was submitted for judging.',16,ORANGE,True)
    im.save(R/TRAIN,optimize=True)

def write_successor():
    # Retain first PNG and its JSON as a FAILED_DISPLAY_LABEL predecessor.
    global GANTT,TRAIN
    d=construct()
    frozen=JSON(OUT)
    assert frozen['pr_events']==d['pr_events'] and frozen['source_file_sha256']==d['source_file_sha256']
    old_gantt=GANTT
    before=SHA(READ(old_gantt))
    corrected='docs/judges/figures/fig20_contributor_gantt_corrected_v2.png'
    target=R/corrected
    receipt=R/'docs/judges/FINAL_JUDGE_TIMELINE_PRESENTATION_CORRECTION_V2.json'
    assert not target.exists() and not receipt.exists(),'APPEND_ONLY_SUCCESSOR_COLLISION'
    GANTT=corrected
    TRAIN='/tmp/ff_fig19_discard_recomputed.png'
    graphics(d)
    (R/TRAIN).unlink(missing_ok=True)
    GANTT=old_gantt
    TRAIN='docs/judges/figures/fig19_actual_training_epochs_20261102.png'
    counts=dict(collections.Counter(e['lane'] for e in frozen['pr_events']))
    assert counts['Mixed / attribution unknown']>0
    result={
      'schema':'frontier-forms.judge-pr-contributor-gantt-correction.v2',
      'predecessor_source_sha256':SHA(READ(OUT)),
      'predecessor_gantt_sha256':before,
      'predecessor_gantt_state':'FAILED_DISPLAY_LABEL_MISMATCH_MIXED_LANE_SHOWN_ZERO',
      'corrected_gantt_path':corrected,
      'corrected_gantt_sha256':SHA(READ(corrected)),
      'pr_count_unchanged':len(frozen['pr_events']),
      'attribution_counts_verified_from_pr_events':counts,
      'frozen_training_figure_sha256_unchanged':SHA(READ(TRAIN)),
      'source_data_changed':False,
      'scientific_promotions':0,
      'status':'PASS_CORRECTED_PRESENTATION'
    }
    receipt.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    return result

def verify_successor():
    result=JSON('docs/judges/FINAL_JUDGE_TIMELINE_PRESENTATION_CORRECTION_V2.json')
    d=JSON(OUT)
    assert SHA(READ(OUT))==result['predecessor_source_sha256']
    assert SHA(READ(GANTT))==result['predecessor_gantt_sha256']
    assert SHA(READ(result['corrected_gantt_path']))==result['corrected_gantt_sha256']
    assert SHA(READ(TRAIN))==result['frozen_training_figure_sha256_unchanged']
    counts=dict(collections.Counter(e['lane'] for e in d['pr_events']))
    assert result['attribution_counts_verified_from_pr_events']==counts
    assert sum(counts.values())==result['pr_count_unchanged']
    assert counts['Mixed / attribution unknown']>0
    assert result['scientific_promotions']==0
    return {'state':'PASS','corrected_image':result['corrected_gantt_path'],
       'prs':sum(counts.values()),'mixed_untagged':counts['Mixed / attribution unknown']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');p.add_argument('--write-successor',action='store_true')
    x=p.parse_args()
    if x.write:
        if (R/OUT).exists() or (R/GANTT).exists() or (R/TRAIN).exists():
            raise FileExistsError('APPEND_ONLY_JUDGE_FINAL_TIMELINE_COLLISION')
        d=construct()
        F.mkdir(parents=True,exist_ok=True)
        graphics(d)
        d['png_sha256']={p:SHA(READ(p)) for p in (GANTT,TRAIN)}
        (R/OUT).write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
    if x.write_successor:write_successor()
    print(json.dumps({'frozen':verify(),'presentation_successor':verify_successor() if (R/'docs/judges/FINAL_JUDGE_TIMELINE_PRESENTATION_CORRECTION_V2.json').exists() else 'NOT_YET'},sort_keys=True,indent=2))
if __name__=='__main__':main()
