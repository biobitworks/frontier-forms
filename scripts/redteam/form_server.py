#!/usr/bin/env python3
"""Local synthetic-form test server (127.0.0.1 only).

Serves a directory of frozen synthetic form renders plus a built-in viewer:
  /                      index of annotated images (from ann/*.json)
  /viewer.html?id=<id>   the form image with bounding-box overlays (renderer ground truth, Apple Vision OCR lines,
                         locally trained YOLOv8n field detector) next to an HTML intake form filled with the extracted
                         values and each field's admission verdict
  /ann/<id>.json         the annotation record behind the viewer
  any other path         static file from --root (e.g. manifest.json, inputs.jsonl, forms/*.png)
Nothing is written; no external host is contacted. Synthetic Synthea-derived data only.

  python3 scripts/redteam/form_server.py --root <dir> --port 8767
"""
from __future__ import annotations
import argparse, html, json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

FIELDS = ('Synthetic case', 'Patient first', 'Patient last', 'Birth date', 'Gender', 'Encounter date', 'Visit class')

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Synthetic Form Viewer</title><style>
:root{--bg:#ffffff;--ink:#111827;--muted:#4b5563;--line:#e5e7eb;--gt:#15803d;--ocr:#1c5cab;--det:#c2410c;--ok:#15803d;--bad:#b91c1c}
body{margin:0;padding:16px;background:var(--bg);color:var(--ink);font:14px ui-sans-serif,system-ui,sans-serif}
h1{font-size:16px;margin:0 0 4px} p{color:var(--muted);margin:0 0 12px}
.wrap{display:flex;gap:16px;flex-wrap:wrap} .fig{position:relative;width:900px;max-width:100%}
.fig img{width:100%;display:block;border:1px solid var(--line)} .fig svg{position:absolute;inset:0;width:100%;height:100%}
form{min-width:320px;flex:1} label{display:block;font-size:12px;color:var(--muted);margin-top:8px}
input{width:100%;box-sizing:border-box;padding:6px 8px;border:2px solid var(--line);border-radius:4px;font:14px ui-monospace,monospace}
input.ok{border-color:var(--ok)} input.bad{border-color:var(--bad)} .verdict{font-size:12px} .legend span{margin-right:14px}
.sw{display:inline-block;width:12px;height:12px;border:2px solid;margin-right:4px;vertical-align:-2px}
</style></head><body>
<h1>__TITLE__</h1><p>__SUB__</p>
<div class="legend"><span><i class="sw" style="border-color:var(--gt)"></i>renderer ground truth</span><span><i class="sw" style="border-color:var(--ocr)"></i>Apple Vision OCR line</span><span><i class="sw" style="border-color:var(--det)"></i>YOLOv8n field detector (conf)</span></div>
<div class="wrap"><div class="fig"><img src="__IMG__" alt="synthetic form"><svg viewBox="0 0 900 560" preserveAspectRatio="none">__BOXES__</svg></div>
<form>__FORM__</form></div></body></html>"""


MODELS = ('qwen2.5vl:3b', 'apple_vision_parser', 'qwen2.5:1.5b', 'qwen3:1.7b')


def boxes_svg(a):
    out = []
    for f, b in (a.get('gt_boxes') or {}).items():
        out.append(f'<rect x="{b[0]:.1f}" y="{b[1]:.1f}" width="{b[2]-b[0]:.1f}" height="{b[3]-b[1]:.1f}" fill="none" stroke="#15803d" stroke-width="2" stroke-dasharray="4 2"><title>GT {html.escape(f)}</title></rect>')
    for l in a.get('ocr_boxes') or []:
        b = l['box']
        out.append(f'<rect x="{b[0]:.1f}" y="{b[1]:.1f}" width="{b[2]-b[0]:.1f}" height="{b[3]-b[1]:.1f}" fill="none" stroke="#1c5cab" stroke-width="1.5"><title>OCR "{html.escape(l["text"])}" conf {l["conf"]:.2f}</title></rect>')
    for d in a.get('detector_boxes') or []:
        b = d['box']
        out.append(f'<rect x="{b[0]:.1f}" y="{b[1]:.1f}" width="{b[2]-b[0]:.1f}" height="{b[3]-b[1]:.1f}" fill="none" stroke="#c2410c" stroke-width="2"><title>{html.escape(d["class"])} {d["conf"]:.2f}</title></rect>'
                   f'<text x="{b[2]+3:.1f}" y="{b[1]+11:.1f}" font-size="10" fill="#c2410c">{d["conf"]:.2f}</text>')
    return ''.join(out)


def form_html(a, model):
    answers = (a.get('answers') or {}).get(model)
    rows = [f'<div style="font-weight:600;margin-bottom:4px">Filled by {html.escape(model)}' + ('' if answers is not None else ' — NOT_RUN for this image') + '</div>']
    correct = 0
    for f in FIELDS:
        fa = (a.get('fields') or {}).get(f, {})
        val = (answers or {}).get(f)
        ok = answers is not None and ' '.join(str(val or '').split()).lower() == ' '.join(str(fa.get('printed') or '').split()).lower()
        correct += ok
        rows.append(f'<label>{html.escape(f)} <span class="verdict">— printed "{html.escape(str(fa.get("printed")))}" · {"match" if ok else "MISMATCH"}</span></label>'
                    f'<input class="{"ok" if ok else "bad"}" value="{html.escape("" if val is None else str(val))}" readonly>')
    rows.append(f'<p style="margin-top:8px">{correct}/7 fields match the printed form</p>')
    return ''.join(rows)


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        root = Path(self.directory)
        if u.path in ('/', '/index.html'):
            items = sorted((root / 'ann').glob('*.json'))
            body = '<!doctype html><meta charset="utf-8"><title>Synthetic Form Index</title><body style="font:14px system-ui;padding:16px"><h1>Annotated synthetic forms</h1><ul>' + ''.join(
                f'<li>{p.stem} — {html.escape(json.loads(p.read_text()).get("title", ""))}: ' + ' · '.join(f'<a href="/viewer.html?id={p.stem}&model={m}">{m}</a> (<a href="/viewer.html?id={p.stem}&model={m}&boxes=0">no boxes</a>)' for m in MODELS) + '</li>' for p in items) + '</ul></body>'
            return self._send(body)
        if u.path == '/viewer.html':
            q = parse_qs(u.query)
            ident = (q.get('id') or [''])[0]
            model = (q.get('model') or ['qwen2.5vl:3b'])[0]
            show_boxes = (q.get('boxes') or ['1'])[0] != '0'
            p = root / 'ann' / f'{Path(ident).name}.json'
            if not p.exists():
                self.send_error(404, 'annotation not found'); return
            a = json.loads(p.read_text())
            body = (PAGE.replace('__TITLE__', html.escape(a.get('title', ident))).replace('__SUB__', html.escape(a.get('subtitle', '')))
                    .replace('__IMG__', '/' + a['image']).replace('__BOXES__', boxes_svg(a) if show_boxes else '').replace('__FORM__', form_html(a, model)))
            return self._send(body)
        return super().do_GET()

    def _send(self, body):
        b = body.encode('utf-8')
        self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(b))); self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--port', type=int, default=8767)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(('127.0.0.1', a.port), partial(Handler, directory=str(Path(a.root).resolve())))
    print(f'SERVING http://127.0.0.1:{a.port}/ from {a.root}', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
