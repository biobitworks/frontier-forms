#!/usr/bin/env python3
"""Run the frozen B0 arm on a synthetic cohort through the loopback form server.

    PYTHONPATH=src python3 scripts/run_forms_b0.py --cohort data/forms_cohort_v1/bundles \
        --limit 100 --out evidence/forms_b0/run_v1

Writes predictions.jsonl, summary.json and receipt.json. predictions.jsonl
and summary.json carry no timestamps, so a replay must reproduce them byte for
byte; receipt.json records the hashes and wall-clock duration.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from frontier_forms.forms import b0, oracle  # noqa: E402
from frontier_forms.forms.cohort import cohort_root, load_cohort, sha256_bytes, sha256_file  # noqa: E402
from frontier_forms.forms.harness import jsonl, output_root, per_field_accuracy, run_arm, summarize  # noqa: E402
from frontier_forms.forms.passport import IMPORTER  # noqa: E402
from frontier_forms.forms.server import FormState, serve  # noqa: E402
from frontier_forms.forms.templates import TEMPLATE_DIR, load_templates  # noqa: E402


def code_hashes():
    pkg = ROOT / "src" / "frontier_forms" / "forms"
    files = sorted(pkg.glob("*.py")) + sorted(TEMPLATE_DIR.glob("*.json")) + [IMPORTER]
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in files}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", required=True)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    members, bundles = load_cohort(Path(args.cohort), limit=args.limit)
    templates = load_templates()
    state = FormState(members, bundles, templates)
    httpd = serve(state)
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    t0 = time.perf_counter()
    try:
        rows = run_arm(base, members, bundles, templates, b0.fill_plan, b0.B0_VERSION)
    finally:
        httpd.shutdown()
        httpd.server_close()
    elapsed = time.perf_counter() - t0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pred = jsonl(rows)
    summary = {"arm": b0.B0_VERSION, "oracle": oracle.ORACLE_VERSION,
               "metrics": summarize(rows), "per_field_accuracy": per_field_accuracy(rows)}
    summary_bytes = (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode()
    (out / "predictions.jsonl").write_bytes(pred)
    (out / "summary.json").write_bytes(summary_bytes)
    receipt = {
        "arm": b0.B0_VERSION,
        "oracle": oracle.ORACLE_VERSION,
        "n_patients": len(members),
        "n_cases": len(rows),
        "split_counts": {s: sum(m.split == s for m in members) for s in ("train", "validation", "test")},
        "cohort_root": cohort_root(members),
        "output_root": output_root(rows),
        "predictions_sha256": sha256_bytes(pred),
        "summary_sha256": sha256_bytes(summary_bytes),
        "code_sha256": code_hashes(),
        "server": "127.0.0.1 ephemeral port, loopback only",
        "hosted_inference": "NONE",
        "wall_seconds": round(elapsed, 3),
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: receipt[k] for k in ("n_patients", "n_cases", "cohort_root", "output_root")}, indent=2))
    print(json.dumps(summary["metrics"]["overall"], indent=2))


if __name__ == "__main__":
    main()
