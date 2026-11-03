#!/usr/bin/env python3
"""Build evidence/FIGURES.html: every headline result as a static figure (inline SVG, no JS,
no network), plus evidence/FIGURES_DATA.json with the exact numbers each figure plots.

The repo's JSON-only gate rejects new PNG/PDF files, so figures are SVG inside one HTML
page. Open it in any browser (double-click it from a local clone, or use GitHub's
"view raw" and save). Everything is read from committed evidence, so rerun this after
new results land:

    python3 scripts/build_figures.py
"""
import glob
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
C = {"a": "#2a6fdb", "b": "#e0812b", "c": "#2f9e5b", "d": "#b23a48", "grid": "#d9d9d9", "ink": "#222"}


def load(p):
    p = ROOT / p
    return json.loads(p.read_text()) if p.exists() else None


def bars(title, cats, series, ymax=1.0, fmt="{:.2f}", note=""):
    """Grouped vertical bars. series = [(name, color, [values or None])]."""
    W, H, L, B, T = 760, 330, 50, 90, 40
    pw, ph = W - L - 70, H - B - T
    gw = pw / max(1, len(cats))
    bw = min(34, (gw - 10) / max(1, len(series)))
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(title)}">']
    for k in range(0, 6):
        y = T + ph - ph * k / 5
        out.append(f'<line x1="{L}" x2="{L + pw}" y1="{y:.1f}" y2="{y:.1f}" stroke="{C["grid"]}"/>'
                   f'<text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="11">{ymax * k / 5:.1f}</text>')
    for i, cat in enumerate(cats):
        x0 = L + i * gw + (gw - bw * len(series)) / 2
        for j, (_, col, vals) in enumerate(series):
            v = vals[i]
            x = x0 + j * bw
            if v is None:
                out.append(f'<text x="{x + bw / 2:.1f}" y="{T + ph - 4}" text-anchor="middle" font-size="9" fill="#888">n/a</text>')
                continue
            h = ph * min(v, ymax) / ymax
            out.append(f'<rect x="{x:.1f}" y="{T + ph - h:.1f}" width="{bw - 2:.1f}" height="{h:.1f}" fill="{col}"/>'
                       f'<text x="{x + bw / 2 - 1:.1f}" y="{T + ph - h - 3:.1f}" text-anchor="middle" font-size="10">{fmt.format(v)}</text>')
        out.append(f'<text transform="translate({L + i * gw + gw / 2:.1f},{T + ph + 12}) rotate(30)" font-size="11">{html.escape(cat)}</text>')
    lx = L
    for name, col, _ in series:
        out.append(f'<rect x="{lx}" y="12" width="12" height="12" fill="{col}"/><text x="{lx + 16}" y="22" font-size="12">{html.escape(name)}</text>')
        lx += 34 + 7 * len(name)
    out.append("</svg>")
    return f"<figure><figcaption><b>{html.escape(title)}</b>{(' · ' + html.escape(note)) if note else ''}</figcaption>{''.join(out)}</figure>"


def lines(title, xs, series, ymax=1.0, note=""):
    W, H, L, B, T = 760, 280, 50, 40, 40
    pw, ph = W - L - 70, H - B - T
    xmax = max(xs) if xs else 1
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(title)}">']
    for k in range(0, 6):
        y = T + ph - ph * k / 5
        out.append(f'<line x1="{L}" x2="{L + pw}" y1="{y:.1f}" y2="{y:.1f}" stroke="{C["grid"]}"/>'
                   f'<text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="11">{ymax * k / 5:.2f}</text>')
    for e in range(0, int(xmax) + 1, max(1, int(xmax) // 8)):
        out.append(f'<text x="{L + pw * e / xmax:.1f}" y="{T + ph + 16}" text-anchor="middle" font-size="11">{e}</text>')
    lx = L
    for name, col, ys in series:
        pts = " ".join(f"{L + pw * x / xmax:.1f},{T + ph - ph * min(y, ymax) / ymax:.1f}" for x, y in zip(xs, ys) if y is not None)
        out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"/>')
        out.append(f'<rect x="{lx}" y="12" width="12" height="12" fill="{col}"/><text x="{lx + 16}" y="22" font-size="12">{html.escape(name)}</text>')
        lx += 34 + 7 * len(name)
    out.append(f'<text x="{L + pw / 2}" y="{H - 4}" text-anchor="middle" font-size="11">epoch</text></svg>')
    return f"<figure><figcaption><b>{html.escape(title)}</b>{(' · ' + html.escape(note)) if note else ''}</figcaption>{''.join(out)}</figure>"


def main():
    figs, data = [], {}

    # 1. form-filling arms on the frozen test split
    arms = []
    fcg = load("evidence/forms_arms/run_v1/FCG_ARMS_V1.json")
    for n in (fcg or {}).get("nodes", []):
        t = n["metrics"]["by_split"].get("test")
        if t:
            arms.append((n["arm"], t["full_form_success_required"], t["field_accuracy"], "rule modules (discovery phase)"))
    for f in sorted(glob.glob(str(EV / "forms_model/*/summary.json"))):
        s = json.loads(Path(f).read_text())
        t = s["metrics"]["by_split"].get("test")
        if t:
            arms.append((s["arm"].split("-qwen")[0], t["full_form_success_required"], t["field_accuracy"], "local Qwen model"))
    data["form_arms_test"] = [{"arm": a, "full_form_success_required": f, "field_accuracy": g, "kind": k} for a, f, g, k in arms]
    figs.append(bars("Fig 1. Form filling on the frozen 54-form test split", [a[0] for a in arms],
                     [("full-form success (required fields)", C["a"], [a[1] for a in arms]),
                      ("field accuracy", C["b"], [a[2] for a in arms])],
                     note="B0 = frozen baseline; L1-L3 = deterministic rule modules; M* = local Qwen2.5-0.5B arms"))

    # 2. vision arms on the screenshots
    t1 = load("evidence/forms_vision/T1-tesseract-redteam/summary.json") or {}
    v1 = load("evidence/forms_vision/V1-qwen2.5vl-3b/summary.json") or {}
    v1i = load("evidence/forms_vision/V1i-qwen2.5vl-3b-injection/summary.json") or {}
    v2 = load("evidence/forms_detector/V2-yolov8n/summary.json") or {}
    seen, held = v2.get("seen_templates_test", {}), v2.get("held_out_layout_test", {})
    vis = [("T1 Tesseract", None, None, t1.get("value_read_match_nonblank")),
           ("V1 qwen2.5vl:3b", v1.get("box_recall_iou50"), v1.get("mean_iou_matched"), v1.get("value_read_match_nonblank")),
           ("V1i injected", v1i.get("box_recall_iou50"), v1i.get("mean_iou_matched"), v1i.get("value_read_match_nonblank")),
           ("V2 YOLOv8n seen", seen.get("box_recall_iou50"), seen.get("mean_iou_matched"), seen.get("ocr_value_agreement_clean_fields")),
           ("V2 YOLOv8n held-out", held.get("box_recall_iou50"), held.get("mean_iou_matched"), held.get("ocr_value_agreement_clean_fields"))]
    data["vision_arms"] = [{"arm": a, "box_recall_iou50": r, "mean_iou": i, "value_read": v} for a, r, i, v in vis]
    figs.append(bars("Fig 2. Finding and reading form fields from screenshots", [v[0] for v in vis],
                     [("box recall IoU>=0.5", C["a"], [v[1] for v in vis]),
                      ("mean IoU (matched)", C["c"], [v[2] for v in vis]),
                      ("value read", C["b"], [v[3] for v in vis])],
                     note="V2 value read = Tesseract on the detected crop; V2 is scored on its own 108 randomized test renders"))

    # 3. V2 validator
    if v2:
        sv, hv = seen.get("validator", {}), held.get("validator", {})
        data["v2_validator"] = {"seen": {k: sv.get(k) for k in ("flag_recall", "false_flag_rate", "abstain_or_unverifiable_rate")},
                                "held_out": {k: hv.get(k) for k in ("flag_recall", "false_flag_rate", "abstain_or_unverifiable_rate")}}
        figs.append(bars("Fig 3. V2 value validator: catches wrong values, but flags too many right ones",
                         ["seen layouts", "held-out layout"],
                         [("flag recall (wrong values caught)", C["c"], [sv.get("flag_recall"), hv.get("flag_recall")]),
                          ("false-flag rate (right values flagged)", C["d"], [sv.get("false_flag_rate"), hv.get("false_flag_rate")]),
                          ("abstain / unverifiable", "#888", [sv.get("abstain_or_unverifiable_rate"), hv.get("abstain_or_unverifiable_rate")])],
                         note=f"mismatch fields: {sv.get('mismatch_fields')} seen, {hv.get('mismatch_fields')} held-out"))
        ep = v2.get("losses_per_epoch", [])
        xs = [e["epoch"] for e in ep]
        data["v2_training_curve"] = ep
        figs.append(lines("Fig 4. V2 detector training (validation split)", xs,
                          [("mAP50", C["a"], [e.get("metrics/mAP50(B)") for e in ep]),
                           ("mAP50-95", C["c"], [e.get("metrics/mAP50-95(B)") for e in ep])],
                          note="held-out urgent-care layout never seen in training; see Fig 2"))

    # 5. SFT selection attempts (validation only), if any
    sel = []
    for f in sorted(glob.glob(str(EV / "forms_model/selection_v1/*/summary.json"))):
        s = json.loads(Path(f).read_text())
        v = s["metrics"]["by_split"].get("validation", {})
        sel.append((s["arm"], v.get("full_form_success_required"), v.get("field_accuracy")))
    if sel:
        data["sft_selection_validation"] = [{"attempt": a, "full_form_success_required": f, "field_accuracy": g} for a, f, g in sel]
        figs.append(bars("Fig 5. SFT attempts, validation split only (selection)", [s[0] for s in sel],
                         [("full-form success", C["a"], [s[1] for s in sel]), ("field accuracy", C["b"], [s[2] for s in sel])],
                         note="post-deadline (host-approved); test split is scored once for the chosen attempt only"))

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Frontier Forms figures</title><style>
body{{font:14px system-ui,sans-serif;margin:16px auto;max-width:800px;color:{C['ink']};background:#fff}}
figure{{margin:24px 0}}figcaption{{margin-bottom:6px}}svg{{width:100%;height:auto;font-family:system-ui,sans-serif}}
</style></head><body><h1>Frontier Forms: results at a glance</h1>
<p>Synthetic patients only (MITRE Synthea). All inference local. Numbers are read from committed evidence by
<code>scripts/build_figures.py</code>; the exact values are in <code>evidence/FIGURES_DATA.json</code>.</p>
{''.join(figs)}</body></html>
"""
    (EV / "FIGURES.html").write_text(page)
    (EV / "FIGURES_DATA.json").write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    print(len(figs), "figures -> evidence/FIGURES.html")


if __name__ == "__main__":
    main()
