#!/usr/bin/env python3
"""Render the gate-factorial heat map (16 mechanism combinations × outcome metrics) as a dependency-free SVG and an
HTML page with hover tooltips, from evidence/redteam/gate_factorial.json.

Form: heat map (magnitude on a grid) -> sequential single-hue ramp (blue, light = near zero, dark = high), per the
dataviz procedure. Two panels, one hue each in its own panel: planted-error detection rate (higher is better) and
false-admission rate (lower is better; drawn with the same ramp so darker always means "more"). Text uses ink tokens,
never the series colour. Values are printed in every cell (a table view is the same grid), so identity never rests on
colour alone.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent.parent
RAMP = ['#f3f8fe', '#cde2fb', '#86b6ef', '#3987e5', '#1c5cab', '#184f95', '#123a6e']  # blue sequential, light->dark
MECHS = ('identity', 'rules', 'commitment', 'consistency')
METRICS = [('planted_detection_rate', 'Planted-error detection rate', True), ('false_admission_rate_of_all', 'False-admission rate (of all cells)', False),
           ('coverage', 'Coverage (admitted / cells)', True), ('selective_accuracy', 'Selective accuracy (admitted correct / admitted)', True)]


def shade(v, vmax):
    if v is None:
        return '#ffffff'
    i = min(len(RAMP) - 1, int(round((v / vmax) * (len(RAMP) - 1)))) if vmax else 0
    return RAMP[i]


def ink(v, vmax):
    return '#ffffff' if v is not None and vmax and v / vmax > 0.55 else '#1f2937'


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else R / 'evidence/redteam/gate_factorial.json'
    d = json.loads(src.read_text())
    cfgs = d['configurations']
    order = sorted(cfgs, key=lambda n: (sum(cfgs[n]['config'].values()), n))
    cell_w, cell_h, left, top = 150, 26, 340, 70
    w = left + cell_w * len(METRICS) + 40; h = top + cell_h * len(order) + 90
    rows = []
    rows.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="ui-sans-serif, system-ui, sans-serif" font-size="12">')
    rows.append(f'<rect width="{w}" height="{h}" fill="#ffffff"/>')
    rows.append(f'<text x="16" y="28" font-size="16" font-weight="600" fill="#111827">Gate factorial on {d["dataset"]} ({d["images_analyzed"]} images, {d["cells"]} field cells)</text>')
    rows.append(f'<text x="16" y="46" fill="#4b5563">primary extractor {d["primary_extractor"]}; challenger {d["challenger_extractor"]}; one row per mechanism combination; darker = larger value</text>')
    for j, (_, label, _) in enumerate(METRICS):
        rows.append(f'<text x="{left + j * cell_w + cell_w / 2}" y="{top - 8}" text-anchor="middle" fill="#374151" font-weight="600">{label.split(" (")[0]}</text>')
    for i, name in enumerate(order):
        c = cfgs[name]; y = top + i * cell_h
        tag = ' (FULL)' if name == '+'.join(MECHS) else (' (LOMO)' if sum(c['config'].values()) == 3 else (' (baseline)' if name == 'none' else ''))
        rows.append(f'<text x="{left - 10}" y="{y + 17}" text-anchor="end" fill="#1f2937">{name}{tag}</text>')
        for j, (key, label, _) in enumerate(METRICS):
            v = c.get(key); x = left + j * cell_w
            vs = c.get('vs_none', {}); star = ''
            if key == 'planted_detection_rate' and vs.get('mcnemar_gate_holm') and vs.get('bootstrap_gate'):
                star = ' *'
            rows.append(f'<rect x="{x + 1}" y="{y + 1}" width="{cell_w - 2}" height="{cell_h - 2}" rx="4" fill="{shade(v, 1.0)}"><title>{name}: {label} = {v if v is None else round(v, 3)}</title></rect>')
            rows.append(f'<text x="{x + cell_w / 2}" y="{y + 17}" text-anchor="middle" fill="{ink(v, 1.0)}">{"NULL" if v is None else f"{v:.2f}"}{star}</text>')
    rows.append(f'<text x="16" y="{h - 48}" fill="#4b5563">* detection row passes Holm-corrected exact McNemar (p&lt;0.05, positive) AND stratified paired bootstrap lower 95% CI &gt; 0 versus the no-gate baseline on per-image success.</text>')
    rows.append(f'<text x="16" y="{h - 30}" fill="#4b5563">Hashes bind bytes; gates bind admission. Rates are OBSERVED on rendered synthetic forms, not scanned paper. Generated {d["generated_utc"]} on {d["host"]}.</text>')
    rows.append(f'<text x="16" y="{h - 12}" fill="#4b5563">Ramp: blue sequential 100→700 (light = near zero). Values printed in every cell; the grid is its own table view.</text>')
    rows.append('</svg>')
    svg = '\n'.join(rows)
    out_svg = R / 'docs/architecture/gate_factorial_heatmap.svg'; out_svg.write_text(svg)
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gate Factorial Heatmap</title>
<style>:root{{--bg:#ffffff;--ink:#111827}}body{{margin:0;padding:16px;background:var(--bg);color:var(--ink);font-family:ui-sans-serif,system-ui,sans-serif}}svg{{max-width:100%;height:auto}}</style></head>
<body><h1 style="font-size:18px;margin:0 0 8px">Frontier Forms red-team: admission-gate factorial</h1>
<p style="color:#4b5563;margin:0 0 12px">Hover a cell for its exact value. Source: evidence/redteam/gate_factorial.json. Mechanisms: identity (FCO case id), rules (Lean-checked deterministic field rules), commitment (salted per-field hash in the FCG leaf), consistency (Apple Vision OCR vs qwen2.5vl agreement).</p>
{svg}</body></html>'''
    (R / 'docs/architecture/gate_factorial_heatmap.html').write_text(html)
    print('WROTE', out_svg, 'rows', len(order))


if __name__ == '__main__':
    main()
