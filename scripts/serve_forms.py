#!/usr/bin/env python3
"""Start the loopback-only synthetic form server for manual or OCR-arm testing.

    PYTHONPATH=src python3 scripts/serve_forms.py --port 8765
    open http://127.0.0.1:8765/forms/new_patient_registration_v1
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frontier_forms.forms.cohort import load_cohort  # noqa: E402
from frontier_forms.forms.server import FormState, serve  # noqa: E402
from frontier_forms.forms.templates import load_templates  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--cohort", default=str(ROOT / "data/forms_cohort_v1/bundles"))
ap.add_argument("--port", type=int, default=8765)
args = ap.parse_args()
members, bundles = load_cohort(Path(args.cohort), limit=100)
httpd = serve(FormState(members, bundles, load_templates()), port=args.port)
print(f"serving {len(members)} synthetic patients on http://127.0.0.1:{httpd.server_address[1]}", flush=True)
try:
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    httpd.shutdown()
