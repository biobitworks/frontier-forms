"""python -m fill_tools --cdp PORT --url URL --passport FILE --model NAME --prices JSON --out FILE"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from .passport import Passport
from .pipeline import fill_form

ap = argparse.ArgumentParser()
for name in ("cdp", "url", "passport", "model", "prices", "out"):
    ap.add_argument(f"--{name}", required=True)
args = ap.parse_args()
with sync_playwright() as pw:
    browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{args.cdp}")
    page = next(p for c in browser.contexts for p in c.pages if p.url.startswith(args.url))
    report = fill_form(page, Passport(json.loads(Path(args.passport).read_text())), args.model, json.loads(args.prices))
    browser.close()
Path(args.out).write_text(json.dumps(report, indent=1))
print("filled", len(report["answers"]), "held", len(report["needs_review"]), "blocked", len(report["blocked"]), "errors", len(report["errors"]))
