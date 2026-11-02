#!/usr/bin/env python3
"""Label every figure and image in the repo for judges.

One registry (FIGURES below) is the source of truth. This script:
  1. injects an idempotent caption banner (figure number, title, how to read the
     axes/legend, source PR, evidence grade) into each analytic HTML figure;
  2. adds <title>/<desc> and a caption line to the gate-factorial SVG;
  3. writes README.md captions into image folders that had none;
  4. writes docs/figures/FIGURES.md, the judges' index of all figures and image sets.

It never edits PNG/PDF bytes (the JSON-only publication gate pins them).
Re-run after regenerating any figure:  python3 scripts/label_figures.py
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- judge-caption:start -->", "<!-- judge-caption:end -->"

# (path, title, how to read, source PR(s), evidence grade)
FIGURES = [
    ("docs/figures/accomplishment_heatmap.html",
     "Accomplishment heatmap: workstream status and mechanisms versus outcomes",
     "1a: rows = workstreams, columns = evidence stages, cell = status (icon + label). 1b: rows = mechanism or combination, "
     "columns = outcome metric 0-1, darker blue = better (lower-better columns shaded by 1 - value), printed number = raw value.",
     "This PR (status 2026-11-02); data from #10 #12 #14-#23", "Mixed; each row tagged"),
    ("docs/architecture/gate_factorial_heatmap.html",
     "Admission-gate factorial on SYNFORM2-ERR (16 mechanism combinations)",
     "Rows = combination of identity / rules / commitment / consistency gates. Columns = planted-error detection, false-admission rate, "
     "coverage, selective accuracy (0-1). Blue sequential ramp, darker = larger value; values printed in every cell.",
     "#20 #21 (red team)", "Discovery (replication NOT_TESTED)"),
    ("evidence/forms_detectors/run_v1/heatmap.html",
     "Injected-error detector gain heatmap (654 forms, 702 preregistered errors)",
     "Rows = detector combination (M1 Merkle breakpoint, M2 Lean 4 constraints, M3 source binding). Columns = recall per error type, "
     "then overall recall, false-positive rate on clean fields, form sensitivity and specificity. Greener = better; lower table lists single-leaf edges "
     "with bootstrap 95% CI and McNemar p (only these attribute a gain).",
     "#10", "Evidence grade (preregistered, synthetic)"),
    ("experiments/form_error_factorial/heatmap.html",
     "Fault-injection factorial: 16 module combinations at three scales",
     "Select a scale (10 / 30 / 100 patients). Rows = module combination, columns = overall accuracy, paired change vs the impaired baseline, "
     "then repair outcome per attack type. Legend: fully repaired / partially repaired / still failing / missing evidence.",
     "#12", "Discovery (faults target known corrections by design)"),
    ("experiments/form_error_factorial/vision_overlay.html",
     "One synthetic form: model field answers over Apple Vision OCR boxes",
     "Image = rendered synthetic PDF. Rectangles = Apple Vision text boxes (not Qwen). Box colour: green exact match, orange missing, red wrong. "
     "Pick the comparison arm (Apple OCR, qwen2.5vl image, qwen3 OCR-text) above the image.",
     "#12", "Illustration only (n = 1 form)"),
    ("dashboard/training_progress.html",
     "Training checkpoints versus FCO/FCG ablations (statistical timeline)",
     "Panel 1: x = epoch, y = validation cross-entropy loss (one real point so far). Panel 2: rows = single changed leaf, columns = delta in percentage "
     "points with 95% CI, McNemar p and Holm-adjusted p. Panel 3: training-set size versus held-out F1 (sample-size sweep, not a learning curve).",
     "#18", "Mixed; no trained-model gain admitted"),
    ("dashboard/training_heatmap.html",
     "Evidence-gate state over evidence versions",
     "Rows = gate, columns = evidence version (not equal time). Colour: green tested PASS, orange negative statistical result, amber reported/unknown, "
     "red failure, grey untested/proposed. Click a cell for its source record.",
     "#7", "Provenance dashboard, no performance claim"),
]
SVG = ("docs/architecture/gate_factorial_heatmap.svg",
       "Admission-gate factorial on SYNFORM2-ERR (16 combinations x 4 outcome metrics)",
       "Source: evidence/redteam/gate_factorial.json, PRs #20/#21. Discovery grade: replication NOT_TESTED.")

IMAGE_SETS = [
    ("data/forms_vision_v1", "Rendered synthetic form images with gold DOM boxes",
     "57 PNG renders (3 blank templates + 54 filled held-out test forms) of the three Frontier Forms templates, filled from MITRE Synthea patients. "
     "GOLD_BOXES.json holds the browser DOM box of every field. Input to V1 qwen2.5vl, T1 Tesseract and the box validators.", "#10 #19"),
    ("data/forms_vision_inject_v1", "Paired clean / prompt-injected form images",
     "18 clean and 18 injected renders of the same forms; the injected copy carries an instruction-like note. Used by V1i (qwen2.5vl followed it 0/18).", "#10 #29"),
    ("redteam/ehr/data/forms", "SYNFORM2 synthetic forms with planted-error twins",
     "Red-team form renders; *.inj.png is the planted-error or injected twin of the clean image. Input to the admission-gate factorial and the Qwen mapper lanes.", "#11 #20 #23"),
    ("evidence/forms_apple/forms", "Frozen blank PDF forms for the Apple arm",
     "The three templates as fillable PDFs; PDFKit fills them as Preview would.", "#10"),
    ("evidence/forms_apple/run_v1/samples", "Apple arm spot-check PDFs with OCR read-back",
     "Two filled PDFs per template, each with its Vision OCR read-back JSON. Shows the two failure modes: dropdown values do not render, long medication lists are cut off.", "#10"),
    ("experiments/form_error_factorial/sample_vision", "Single synthetic intake form for the vision overlay",
     "One rendered synthetic intake form (PNG + PDF) with the raw model replies in model_field_answers.json; drawn in vision_overlay.html.", "#12"),
    ("experiments/form_error_factorial/prebuilt_forms", "Prebuilt synthetic HTML intake fixtures",
     "15 synthetic HTML intake forms used as fault-injection fixtures (MANIFEST.json lists hashes).", "#12"),
]


def banner(num, title, read, src, grade):
    e = html.escape
    return (f'{START}\n<aside style="all:initial;display:block;font:13px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;'
            f'background:#fffbe6;color:#1a1a1a;border:1px solid #e0c96b;border-radius:8px;padding:10px 14px;margin:12px 16px" '
            f'aria-label="Figure caption">'
            f'<b style="font-size:14px">Figure {num}. {e(title)}</b><br>'
            f'<b>How to read:</b> {e(read)}<br>'
            f'<b>Source:</b> PR {e(src)} &middot; <b>Evidence grade:</b> {e(grade)} &middot; '
            f'Synthetic MITRE Synthea data, local inference only. Index: docs/figures/FIGURES.md</aside>\n{END}')


def label_html(path, block):
    p = ROOT / path
    t = p.read_text()
    t = re.sub(r"\n?" + re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", t, flags=re.S)
    m = re.search(r"<body[^>]*>", t)
    if not m:
        raise SystemExit(f"no <body> in {path}")
    p.write_text(t[:m.end()] + "\n" + block + "\n" + t[m.end():])


def label_svg():
    path, title, desc = SVG
    p = ROOT / path
    t = p.read_text()
    t = re.sub(r"<!-- judge-caption:start -->.*?<!-- judge-caption:end -->\n?", "", t, flags=re.S)
    m = re.match(r'(<svg[^>]*?height=")(\d+)("[^>]*viewBox="0 0 \d+ )(\d+)(")', t)
    h = int(m.group(2))
    # restore original height if previously extended
    if "data-judge-h" in t:
        h = int(re.search(r'data-judge-h="(\d+)"', t).group(1))
        t = re.sub(r' data-judge-h="\d+"', "", t)
    nh = h + 28
    t = re.sub(r'(<svg[^>]*?)height="\d+"', rf'\1height="{nh}" data-judge-h="{h}"', t, count=1)
    t = re.sub(r'(viewBox="0 0 \d+ )\d+"', rf'\g<1>{nh}"', t, count=1)
    t = re.sub(r'(<rect width="\d+" height=")\d+(" fill="#ffffff"/>)', rf'\g<1>{nh}\2', t, count=1)
    head_end = t.index(">") + 1
    block = (f"\n{START}<title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc>"
             f'<text x="16" y="{h + 18}" fill="#111827" font-weight="600">Figure. {html.escape(title)}. {html.escape(desc)}</text>{END}')
    p.write_text(t[:head_end] + block + t[head_end:])


def write_readmes():
    for d, title, cap, prs in IMAGE_SETS:
        r = ROOT / d / "README.md"
        if r.exists():
            continue
        r.write_text(f"# {title}\n\n{cap}\n\nSource: PR {prs}. All patients are synthetic (MITRE Synthea). "
                     f"Index of every figure and image set: `docs/figures/FIGURES.md`.\n")


def write_index():
    lines = ["# Figures and images: index for judges", "",
             "Every figure and image in the repository, with what it shows, how to read it, the PR that produced it and its evidence grade. "
             "All patient data is synthetic (MITRE Synthea); all inference ran locally. Regenerate with `python3 scripts/build_status_figures.py && python3 scripts/label_figures.py`.",
             "", "Evidence grades: **Evidence** = preregistered or independent run; **Discovery** = built after seeing the test data, needs replication; "
             "**Negative** = no gain over the control; **Illustration** = a single example, no statistics.", "",
             "## Analytic figures", "",
             "| # | Figure | How to read (axes, legend) | Source PR | Grade |", "|---|---|---|---|---|"]
    for i, (path, title, read, src, grade) in enumerate(FIGURES, 1):
        lines.append(f"| {i} | [{title}](../../{path}) | {read} | {src} | {grade} |")
    path, title, desc = SVG
    lines.append(f"| {len(FIGURES) + 1} | [{title} (static SVG)](../../{path}) | Same as figure 2, static. | #20 #21 | Discovery |")
    lines.append(f"| {len(FIGURES) + 2} | [Accomplishment heatmap (static PNG)](accomplishment_heatmap.png) | Static render of figure 1. | This PR | Mixed |")
    lines += ["", "## Image sets (inputs, not results)", "",
              "These are the synthetic form renders the models read. They are stimuli, not charts, so each set is captioned once here and in its folder README.", "",
              "| Folder | Title | Caption | Source PR |", "|---|---|---|---|"]
    for d, title, cap, prs in IMAGE_SETS:
        lines.append(f"| [`{d}/`](../../{d}) | {title} | {cap} | {prs} |")
    lines += ["", "## Not in the repo", "",
              "Bounding-box overlay galleries (gold / qwen2.5vl / Tesseract) are on open PR #29, not on main. "
              "V2 detector renders, model weights and raw model prompts stay on the local Macs by policy.", ""]
    (ROOT / "docs/figures/FIGURES.md").write_text("\n".join(lines))


def main():
    for i, (path, *rest) in enumerate(FIGURES, 1):
        if path == "docs/figures/accomplishment_heatmap.html":
            continue  # carries its own Figure 1a/1b captions (scripts/status_heatmap_template.html)
        label_html(path, banner(i, *rest))
    label_svg()
    write_readmes()
    write_index()
    print("labelled", len(FIGURES), "HTML figures, 1 SVG, wrote FIGURES.md")


if __name__ == "__main__":
    main()
