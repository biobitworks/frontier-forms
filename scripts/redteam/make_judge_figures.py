#!/usr/bin/env python3
"""Judge-facing labelled figures for the Frontier Forms red-team lane.

Every output PNG carries: a title bar "Figure N — <title>", the image or chart, and a caption footer with what it shows,
the data source path in this repo, and "SYNTHETIC DATA ONLY (MITRE Synthea sample) — not clinical". Charts are drawn
with Pillow (no plotting dependency): heat maps use one sequential blue ramp (darker = more), bars use one hue with direct
value labels, values are printed so colour never carries meaning alone. Missing inputs are skipped and listed.
Writes docs/judges/figures/*.png and docs/judges/FIGURES.md.
"""
from __future__ import annotations
import json, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

R = Path(__file__).resolve().parent.parent.parent
OUT = R / 'docs/judges/figures'
RAMP = ['#f3f8fe', '#cde2fb', '#86b6ef', '#3987e5', '#1c5cab', '#184f95', '#123a6e']
INK, MUTED, LINE, BG = (17, 24, 39), (75, 85, 99), (229, 231, 235), (255, 255, 255)
SYN = 'SYNTHETIC DATA ONLY (MITRE Synthea sample) — not clinical, no PHI, no hosted inference.'
F = lambda s: ImageFont.load_default(size=s)


ASCII = {'Δ': 'd', '−': '-', '—': '-', '–': '-', '≥': '>=', '≤': '<=', '▲': '^', '▼': 'v', '✓': 'yes', '→': '->', '×': 'x', '…': '...', '·': '|', '∧': 'AND', 'σ': 'sigma', '°': ' deg'}


def a(t):
    t = str(t)
    for k, v in ASCII.items():
        t = t.replace(k, v)
    return t


def hexrgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
def shade(v): return hexrgb(RAMP[min(len(RAMP) - 1, max(0, int(round(v * (len(RAMP) - 1)))))])
def ink_on(v): return (255, 255, 255) if v > 0.55 else INK


def frame(body: Image.Image, num: int, title: str, caption: str, source: str) -> Image.Image:
    w = max(body.width + 40, 1000)
    cap_lines = textwrap.wrap(a(caption), width=int(w / 7.4)) + textwrap.wrap('Source: ' + a(source), width=int(w / 7.4)) + [a(SYN)]
    h = 64 + body.height + 24 + 20 * len(cap_lines) + 16
    im = Image.new('RGB', (w, h), BG); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 52], fill=(243, 244, 246))
    d.text((20, 14), a(f'Figure {num} - {title}'), fill=INK, font=F(22))
    im.paste(body, (20, 64))
    y = 64 + body.height + 16
    d.line([20, y - 6, w - 20, y - 6], fill=LINE, width=1)
    for i, l in enumerate(cap_lines):
        d.text((20, y + 20 * i), l, fill=MUTED if i < len(cap_lines) - 1 else (155, 28, 28), font=F(15))
    return im


def heatmap(rows, cols, values, labels, cell=(118, 30), left=330, top=60, title_cols=None):
    w = left + cell[0] * len(cols) + 20; h = top + cell[1] * len(rows) + 10
    im = Image.new('RGB', (w, h), BG); d = ImageDraw.Draw(im)
    for j, c in enumerate(title_cols or cols):
        for k, part in enumerate(textwrap.wrap(c, 16)[:3]):
            d.text((left + j * cell[0] + 6, 4 + 16 * k), a(part), fill=INK, font=F(13))
    for i, r in enumerate(rows):
        d.text((8, top + i * cell[1] + 8), a(r)[:92], fill=INK, font=F(13))
        for j, _ in enumerate(cols):
            v = values[i][j]; x, y = left + j * cell[0], top + i * cell[1]
            d.rounded_rectangle([x + 1, y + 1, x + cell[0] - 2, y + cell[1] - 2], 4, fill=shade(v) if v is not None else BG, outline=LINE)
            d.text((x + 8, y + 8), a(labels[i][j]), fill=ink_on(v or 0), font=F(13))
    return im


def bars(items, maxv, unit='', width=900, bar_h=34):
    left = 300; h = 20 + bar_h * len(items) + 10
    im = Image.new('RGB', (width, h), BG); d = ImageDraw.Draw(im)
    for i, (name, v, note) in enumerate(items):
        y = 10 + i * bar_h
        d.text((8, y + 9), a(name), fill=INK, font=F(14))
        L = int((width - left - 160) * v / maxv)
        d.rounded_rectangle([left, y + 6, left + max(L, 2), y + bar_h - 6], 4, fill=hexrgb('#3987e5'))
        d.text((left + L + 8, y + 9), a(f'{v}{unit} {note}'), fill=INK, font=F(14))
    return im



def table(rows, cols, widths, row_h=24):
    """rows: list of tuples of strings; colours the last column by decision word (text + tint, never colour alone)."""
    w = sum(widths) + 20; h = 34 + row_h * len(rows) + 8
    im = Image.new('RGB', (w, h), BG); d = ImageDraw.Draw(im)
    x = 10
    for c, cw in zip(cols, widths):
        d.text((x + 4, 8), a(c), fill=INK, font=F(14)); x += cw
    d.line([10, 30, w - 10, 30], fill=LINE, width=1)
    tint = {'PROMOTE': (205, 226, 251), 'PASS': (205, 226, 251), 'GAIN': (205, 226, 251), 'NULL': (243, 244, 246), 'NEUTRAL': (243, 244, 246),
            'NEGATIVE': (254, 226, 226), 'LOSS': (254, 226, 226), 'BLOCKED': (255, 237, 213), 'NOT_TESTED': (255, 237, 213)}
    for i, r in enumerate(rows):
        y = 34 + i * row_h; x = 10
        key = next((k for k in tint if str(r[-1]).upper().startswith(k)), None)
        if key:
            d.rectangle([10 + sum(widths[:-1]), y, 10 + sum(widths), y + row_h - 2], fill=tint[key])
        for v, cw in zip(r, widths):
            t = a(v); maxc = int(cw / 7.2)
            d.text((x + 4, y + 5), t if len(t) <= maxc else t[:maxc - 3] + '...', fill=INK, font=F(13)); x += cw
    return im


def fit(img: Image.Image, maxw=1400):
    if img.width > maxw:
        img = img.resize((maxw, int(img.height * maxw / img.width)))
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    figs, skipped, n = [], [], 0

    def add(title, body, caption, source, slug):
        nonlocal n
        n += 1
        p = OUT / f'fig{n:02d}_{slug}.png'
        frame(body, n, title, caption, source).save(p)
        figs.append((n, title, caption, source, p.name))

    # 1 accomplishment heat map (from the PR inventory)
    inv = R / 'docs/judges/pr_inventory.json'
    if inv.exists():
        ws = json.loads(inv.read_text())['workstreams']
        stages = ['PROPOSED', 'IMPLEMENTED', 'EXECUTED', 'OBSERVED', 'SUPPORTED']
        vals, labs = [], []
        for w in ws:
            st = w.get('stages', {})
            row = [1.0 if st.get(s) else 0.0 for s in stages]
            vals.append(row + [None]); labs.append(['yes' if x else '-' for x in row] + [w.get('highest_status_reached', '')])
        names = [f"{w['name']} (#{', #'.join(str(p) for p in w.get('prs', [])[:4])})" for w in ws]
        body = heatmap(names, stages + ['Outcome'], vals, labs, cell=(112, 26), left=640, title_cols=stages + ['Outcome (highest status / result)'])
        add('What we accomplished: workstreams × evidence stage', fit(body),
            'Each row is a workstream across all 34 pull requests (27 merged, 4 open, 3 closed as superseded). Blue cells = the PRs show that stage was reached. Outcome keeps the honest result: NEGATIVE / NULL results and BLOCKED lanes (hosted inference, Snyk) are shown, not hidden. No workstream is SUPPORTED yet: that needs McNemar + bootstrap + an independent replication cohort + guardrails.',
            'docs/judges/pr_inventory.json (built from every PR in biobitworks/frontier-forms)', 'accomplishment_heatmap')
    else:
        skipped.append('accomplishment heat map (pr_inventory.json missing)')

    # 2 gate factorial
    gf = R / 'evidence/redteam/gate_factorial.json'
    if gf.exists():
        g = json.loads(gf.read_text()); cf = g['configurations']
        order = sorted(cf, key=lambda k: (sum(cf[k]['config'].values()), k))
        metrics = [('planted_detection_rate', 'Planted-error detection'), ('false_admission_rate_of_all', 'False admissions (of all cells)'), ('coverage', 'Coverage'), ('selective_accuracy', 'Selective accuracy')]
        vals = [[cf[k][m] for m, _ in metrics] for k in order]
        labs = [[('—' if v is None else f'{v:.2f}') + (' *' if j == 0 and cf[k].get('vs_none', {}).get('mcnemar_gate_holm') and cf[k].get('vs_none', {}).get('bootstrap_gate') else '') for j, v in enumerate(r)] for k, r in zip(order, vals)]
        names = [k + (' (FULL)' if k.count('+') == 3 else ' (LOMO)' if k.count('+') == 2 else ' (baseline)' if k == 'none' else '') for k in order]
        add('Which admission checks catch planted form errors (16 combinations)', fit(heatmap(names, [m for m, _ in metrics], vals, labs, cell=(150, 28), left=360, title_cols=[t for _, t in metrics])),
            f"{g['images_analyzed']} planted-error form images ({g['cells']} field cells): qwen2.5vl:3b extraction checked by identity (FCO case id), deterministic rules (Lean-checked), per-field source commitments in the FCO leaf, and agreement with Apple Vision OCR. Darker = larger. * = Holm-corrected exact McNemar p<0.05 and bootstrap lower 95% CI > 0 vs no checks. The commitment leaf alone reaches 1.00 detection with 0 false admissions; it needs the source record to exist.",
            'evidence/redteam/gate_factorial.json', 'gate_factorial')
    else:
        skipped.append('gate factorial')

    # 3 model comparison on the frozen test split
    L = R / 'evidence/redteam/lanes'
    def fid(p, key):
        rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
        return sum(sum(r[key].values()) for r in rows), 7 * len(rows), sum(1 for r in rows if all(r[key].values())), len(rows)
    items = []
    for label, p, key in (('qwen2.5vl:3b (reads image)', L / 'VLM_qwen2.5vl_3b_synform2_test_PUBLIC.jsonl', 'correct_extract'),
                          ('Apple Vision OCR + rule parser', L / 'OCR_apple-vision_synform2_test_PUBLIC.jsonl', 'correct'),
                          ('Apple OCR → qwen2.5:1.5b mapper', L / 'MAP_qwen2.5_1.5b_synform2_test_PUBLIC.jsonl', 'correct'),
                          ('Apple OCR → qwen3:1.7b mapper', L / 'MAP_qwen3_1.7b_synform2_test_PUBLIC.jsonl', 'correct')):
        if p.exists():
            c, t, a7, nimg = fid(p, key); items.append((label, c, f'/ {t} fields · all-7 correct on {a7}/{nimg} forms'))
    if items:
        add('Field accuracy by model on the frozen test forms', bars(items, max(i[1] for i in items) * 1.0),
            'Same 46 synthetic test forms (23 patients × clean + scan-like render). A field counts only if it exactly matches the printed value after normalisation. These are model (weights) comparisons, not harness gains. Qwen text mappers read the same Apple Vision OCR lines as the rule parser and do worse.',
            'evidence/redteam/lanes/{VLM,OCR,MAP}_*_synform2_test_PUBLIC.jsonl', 'model_field_accuracy')

    # 4 per-epoch training ledger
    det = R / 'evidence/redteam/detector'
    if (det / 'full/epoch_ledger.jsonl').exists():
        W_, H_ = 1000, 360; im = Image.new('RGB', (W_, H_), BG); d = ImageDraw.Draw(im)
        L0, T0, B0 = 70, 20, 300
        xs = lambda e: L0 + (e - 1) * (W_ - L0 - 40) / 29; ys = lambda v: T0 + (1 - v / 308) * (B0 - T0)
        for v in (0, 77, 154, 231, 308):
            d.line([L0, ys(v), W_ - 40, ys(v)], fill=LINE); d.text((10, ys(v) - 7), str(v), fill=MUTED, font=F(13))
        for e in (1, 5, 10, 15, 20, 25, 30):
            d.text((xs(e) - 6, B0 + 8), str(e), fill=MUTED, font=F(13))
        d.text((W_ / 2 - 30, B0 + 30), 'epoch', fill=MUTED, font=F(14))
        for run, col, lab in (('full', '#1c5cab', 'full training set'), ('no_scan', '#c2410c', 'LOMO: no scan-like images')):
            rows = [json.loads(x) for x in (det / run / 'epoch_ledger.jsonl').read_text().splitlines() if x.strip()]
            pts = [(xs(r['epoch']), ys(r['dev_fields_ok'])) for r in rows]
            d.line(pts, fill=hexrgb(col), width=3)
            for r, (x, y) in zip(rows, pts):
                if r['status'] == 'GAIN': d.polygon([(x, y - 10), (x - 6, y - 1), (x + 6, y - 1)], fill=hexrgb(col))
                elif r['status'] == 'LOSS': d.polygon([(x, y + 10), (x - 6, y + 1), (x + 6, y + 1)], fill=hexrgb(col))
            d.text((L0 + 520, B0 - 70 + (24 if run == 'no_scan' else 0)), f"{lab}: final dev {rows[-1]['dev_fields_ok']}/308 boxes", fill=hexrgb(col), font=F(14))
        d.text((L0 + 520, B0 - 22), 'filled up-triangle = GAIN epoch, down-triangle = LOSS epoch', fill=MUTED, font=F(13))
        fr = json.loads((det / 'full/final_receipt.json').read_text()); nr = json.loads((det / 'no_scan/final_receipt.json').read_text())
        add('Training over time: every epoch committed as a Merkle leaf (GAIN / LOSS / NEUTRAL)', im,
            f"Local YOLOv8n field-box detector trained on the SYNFORM2 train split; after every epoch the weights are hashed, scored on the dev split (field box IoU ≥ 0.5, 308 boxes), compared with the previous epoch (exact McNemar + stratified bootstrap) and committed to a hash chain. Test (touched once): full mAP50 {fr['test']['mAP50']:.3f}, {fr['test']['fields_ok']}/{fr['test']['fields_total']} boxes; LOMO no-scan mAP50 {nr['test']['mAP50']:.3f}, {nr['test']['fields_ok']}/{nr['test']['fields_total']}. Chain roots {fr['chain_root'][:12]}… / {nr['chain_root'][:12]}….",
            'evidence/redteam/detector/{full,no_scan}/epoch_ledger.jsonl, chain_manifest.json, final_receipt.json', 'epoch_ledger')


    # promotions and negatives: every decision in one table
    dec = []
    am = R / 'evidence/redteam/attribution_matrix.json'
    if am.exists():
        for r in json.loads(am.read_text())['records']:
            if r['kind'] in ('MODEL_LANE', 'CONTEXT_PROJECTION') and 'table' in r and r['split'] == 'heldout':
                w = r['weights']; ww = w['challenger']['name'] if r['kind'] == 'MODEL_LANE' else w['baseline']['name']
                verdict = 'NEGATIVE_WORSE' if (r['holm_p'] < 0.05 and r['delta_abs'] < 0) else ('PROMOTE (discovery)' if r['admission'] == 'PASS' else 'NULL')
                dec.append(('LongevityBench heldout (n=39)', ww, r['intervention'][:40], f"d={r['delta_abs']:+.3f}, Holm p={r['holm_p']:.3f}", verdict))
    gfp = R / 'evidence/redteam/gate_factorial.json'
    if gfp.exists():
        g = json.loads(gfp.read_text())
        for k, c in sorted(g['configurations'].items(), key=lambda kv: (sum(kv[1]['config'].values()), kv[0])):
            if k == 'none' or k.count('+') not in (0, 3):
                continue
            v = c.get('vs_none', {})
            dec.append(('Planted-error forms (135 img)', 'qwen2.5vl:3b + Apple OCR', 'checks: ' + k, f"detect {c['planted_detection_rate']:.2f}, false adm {c['false_admissions']}, Holm p={v.get('p_holm', 1):.4f}",
                        'PROMOTE (discovery; no replication yet)' if v.get('mcnemar_gate_holm') and v.get('bootstrap_gate') else 'NULL'))
    for run in ('full', 'no_scan'):
        lp = R / f'evidence/redteam/detector/{run}/epoch_ledger.jsonl'
        if lp.exists():
            st = [json.loads(x)['status'] for x in lp.read_text().splitlines() if x.strip()]
            for s_ in ('GAIN', 'LOSS'):
                eps = [i + 1 for i, x in enumerate(st) if x == s_]
                dec.append((f'Detector training ({run})', 'YOLOv8n (trained locally)', f'epoch vs previous epoch ({len(eps)} epochs)', 'epochs ' + ', '.join(map(str, eps)) if eps else 'none', s_))
            dec.append((f'Detector training ({run})', 'YOLOv8n (trained locally)', 'remaining epochs', f"{st.count('NEUTRAL')} epochs", 'NEUTRAL'))
    tgp = R / 'evidence/redteam/trained_gain/trained_gain_summary.json'
    if tgp.exists():
        t = json.loads(tgp.read_text())
        names = {'A1': 'learned OCR correction', 'A2': 'trained detector crops', 'A3': 'detector crops + correction'}
        for arm, c in t['comparisons_vs_A0'].items():
            dec.append(('Test forms (46 img, once)', 'trained local models vs page OCR', names[arm], f"all-7 {c['baseline_all7']}->{c['arm_all7']}/46, fields {c['baseline_fields_correct']}->{c['fields_correct']}/322, Holm p={c['p_holm']:.4f}", c['decision']))
    invp = R / 'docs/judges/pr_inventory.json'
    if invp.exists():
        for w in json.loads(invp.read_text())['workstreams']:
            if w['highest_status_reached'] in ('NEGATIVE', 'NULL', 'BLOCKED', 'NOT_TESTED'):
                dec.append(('All PRs (inventory)', w['name'][:34], 'workstream outcome', (w.get('blocked_or_negative') or '')[:60], w['highest_status_reached']))
    if dec:
        add('Every promotion decision, including negative and null results', fit(table(dec, ['Data', 'Weights / model', 'Intervention', 'Measured', 'Decision'], [200, 230, 290, 420, 360])),
            'One row per decision. PROMOTE requires Holm-corrected exact McNemar p<0.05 and a stratified-bootstrap lower 95% CI > 0, and is labelled discovery because the replication cohort is NOT_TESTED. NEGATIVE, NULL, LOSS, NEUTRAL, BLOCKED and NOT_TESTED rows are kept on purpose. Tint repeats the word in the Decision column (blue = promote/gain, grey = null/neutral, red = negative/loss, orange = blocked/not tested).',
            'evidence/redteam/attribution_matrix.json, gate_factorial.json, detector/*/epoch_ledger.jsonl, trained_gain/trained_gain_summary.json, docs/judges/pr_inventory.json', 'promotions_and_negatives')

    # trained local models vs untrained baseline (preregistered, test split scored once)
    if tgp.exists():
        t = json.loads(tgp.read_text()); C = t['comparisons_vs_A0']; b0 = C['A1']
        items = [('A0 page OCR + rule parser (untrained)', b0['baseline_all7'], f"/ 46 forms all 7 fields | {b0['baseline_fields_correct']}/322 fields | baseline")]
        names = {'A1': 'A1 + learned correction (fit on train)', 'A2': 'A2 trained YOLOv8n crops + OCR', 'A3': 'A3 detector crops + correction'}
        for arm in ('A1', 'A2', 'A3'):
            c = C[arm]; lo, hi = c['ci95_bootstrap_stratified']
            items.append((names[arm], c['arm_all7'], f"/ 46 | {c['fields_correct']}/322 fields | Holm p={c['p_holm']:.3f} | CI [{lo:+.2f},{hi:+.2f}] | {c['decision'].split(' ')[0]}"))
        cm = t['trained_components']['post_correction']
        rules = [f"{f}: {k}" for f, m in cm['char_map'].items() for k in m]
        add('Trained local models vs the untrained baseline (test split, scored once)', bars(items, 46, width=1300),
            'Preregistered before the test split was scored (scripts/redteam/trained_gain_eval.py, committed first). Endpoint: forms with all 7 fields correct, 46 held-out images (23 patients x clean + scan). '
            f"The learned correction was fit only on the 132 training images: strip spaces in every field (no training value contains one) plus character rules seen at least twice and never contradicted ({', '.join(rules) or 'none'}). "
            'It is the only trained arm that is promoted, at discovery grade because the replication cohort is NOT_TESTED. The trained YOLOv8n detector finds fields well (mAP50 0.912) but OCR on its crops is NULL, and so is crops plus correction.',
            'evidence/redteam/trained_gain/trained_gain_summary.json, trained_gain_rows.json', 'trained_gain')

    # 5+ labelled form images
    demo = R / 'docs/demo'
    shots = [
        ('overlay/synform2-ce08cff8d07665997ab7_clean.png', 'A clean synthetic intake form with three kinds of boxes', 'Renderer ground truth (green dashed), Apple Vision OCR text lines (blue) and the locally trained YOLOv8n detector (orange, with confidence) on a frozen SYNFORM2 test render.', 'clean_boxes'),
        ('overlay/synform2-ce08cff8d07665997ab7_scan.png', 'The same form as a scan-like image (rotation, noise, blur, JPEG)', 'Scan-like variant of the same patient; boxes as in the previous figure. Used to test robustness of OCR and the detector.', 'scan_boxes'),
        ('screenshots/synform2-ce08cff8d07665997ab7_E6_name_swap.png', 'Planted error the models cannot see: first and last names swapped', 'Local form server: the printed form swaps first/last name. qwen2.5vl:3b reads the printed values faithfully and every rule passes — only the per-field source commitment in the FCO leaf rejects it.', 'planted_name_swap'),
        ('screenshots/synform2-ce08cff8d07665997ab7_E3_case_id_swap.png', 'Planted cross-patient error: another patient\'s case id', 'The printed case id belongs to a different patient. The identity check (FCO case id) and the commitment check both reject it.', 'planted_case_swap'),
        ('screenshots/synform2-ce08cff8d07665997ab7_V2_scan_sigma25.png', 'Heavy noise variant read by the models', 'Heavier noise and rotation with no planted error; tests whether extraction stays correct under degradation.', 'heavy_noise'),
    ]
    for rel, title, cap, slug in shots:
        p = demo / rel
        if p.exists():
            add(title, fit(Image.open(p).convert('RGB')), cap, f'docs/demo/{rel}', slug)
        else:
            skipped.append(rel)
    models_dir = demo / 'screenshots/models'
    for m, nice in (('qwen2.5vl_3b', 'qwen2.5vl:3b'), ('apple_vision_parser', 'Apple Vision OCR + rule parser'), ('qwen2.5_1.5b', 'qwen2.5:1.5b mapper'), ('qwen3_1.7b', 'qwen3:1.7b mapper')):
        p = models_dir / f'synform2-ce08cff8d07665997ab7_scan__{m}__boxes.png'
        if p.exists():
            add(f'Form filled by {nice}', fit(Image.open(p).convert('RGB')), f'Local form server: the scan-like form (left, with boxes) and the HTML intake form filled with the actual answers of {nice} (right). Green = field matches the printed form; red = mismatch.', f'docs/demo/screenshots/models/{p.name}', f'filled_{m}')
        else:
            skipped.append(f'models/{m}')
    p = models_dir / 'synform2-ce08cff8d07665997ab7_scan__qwen2.5vl_3b__noboxes.png'
    if p.exists():
        add('Same filled form without bounding boxes', fit(Image.open(p).convert('RGB')), 'The viewer with overlays switched off, as a reviewer would see the plain scan next to the filled form.', f'docs/demo/screenshots/models/{p.name}', 'filled_noboxes')
    bo = demo / 'ocr_boxes_vs_clean.json'
    if bo.exists():
        b = json.loads(bo.read_text())
        add('Drawing boxes on an image breaks OCR', bars([('Apple OCR on clean images', b['clean_fields_correct'], f"/ {b['fields_total']} fields"), ('Apple OCR on images with boxes drawn', b['boxes_fields_correct'], f"/ {b['fields_total']} fields")], max(1, b['clean_fields_correct'])),
            'Same 10 forms, same OCR engine and parser; the only change is the drawn bounding boxes. Lesson: run OCR on the clean render and keep overlays for humans.', 'docs/demo/ocr_boxes_vs_clean.json', 'boxes_break_ocr')
    pv = demo / 'preview/preview_ocr.json'
    if pv.exists():
        v = json.loads(pv.read_text())
        shot = next(iter(sorted((demo / 'preview').glob('*.png'))), None)
        if shot:
            add('macOS Preview window capture, then Apple OCR', fit(Image.open(shot).convert('RGB')),
                f"Pipeline: render → one-page PDF → opened in Preview → only Preview's window captured → Apple Vision OCR → rule parser. Captured {v['captured']}/{v['images']} windows; {v['fields_correct']}/{v['fields_total']} fields correct.", 'docs/demo/preview/', 'preview_capture')
    else:
        skipped.append('preview captures')

    md = ['# Figures for judges', '', SYN, '', 'All figures are generated by `scripts/redteam/make_judge_figures.py` from files in this repository; captions state the data source.', '']
    for num, title, cap, src, name in figs:
        md += [f'## Figure {num} — {title}', '', f'![Figure {num}](figures/{name})', '', cap, '', f'*Source:* `{src}`', '']
    if skipped:
        md += ['## Not included (input missing at build time)', ''] + [f'- {s}' for s in skipped] + ['']
    (R / 'docs/judges/FIGURES.md').write_text('\n'.join(md))
    print('FIGURES', len(figs), 'SKIPPED', skipped)


if __name__ == '__main__':
    main()
