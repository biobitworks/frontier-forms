"""Run a small matrix of arms on dev pairs and summarise it. Every row counts, including failed runs.

    pilot.py [--arms browser-tools frontier-tools] [--models deepseek-v4p1-flash] [--patients ...] [--forms ...] [--repeats 1] [--workers 3]
    pilot.py --summary

Runs go in a seeded shuffle at fixed concurrency, so neither arm gets the quieter machine. Finished runs are skipped on resume.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "results/pilot"
FORMS = ["primary_care_registration", "urgent_care_history", "insurance_update"]
PATIENTS = ["SYN-00015", "SYN-00037"]


def result_path(arm, model, form, patient, repeat) -> Path:
    return OUT / f"{arm}.{model}.{form}.{patient}.r{repeat}.json"


def one(job) -> str:
    arm, model, form, patient, repeat = job
    if result_path(*job).exists():
        return f"kept {job}"
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    done = subprocess.run([sys.executable, str(HERE / "fill.py"), "--arm", arm, "--model", model, "--form", form, "--patient", patient, "--repeat", str(repeat)],
                          capture_output=True, text=True, env=env, timeout=420)
    return f"{'ok' if done.returncode == 0 else 'FAILED'} {job} {done.stdout[-160:] if done.returncode else ''}{done.stderr[-200:]}"


def ratio(a, b):
    return f"{a}/{b} ({a / b:.0%})" if b else "n/a"


def summary(files: list[Path]) -> None:
    arms = defaultdict(list)
    for path in files:
        row = json.loads(path.read_text())
        arms[(row["arm"], row["model"])].append(row)
    for (arm, model), rows in sorted(arms.items()):
        good = [r for r in rows if not r["failed"]]
        add = lambda key: sum(r[key] for r in good)
        sens = lambda policy, key: sum(r["sensitivity"][policy][key] for r in good)
        absent = {k: sum(r["absent"][k] for r in good) for k in ("fields", "left_blank", "answered_no", "answered_otherwise")}
        print(f"\n{arm} / {model}: {len(rows)} runs, {len(rows) - len(good)} failed, {sum(r['timed_out'] for r in rows)} timed out")
        if not good:
            continue
        print(f"  field accuracy   neutral {ratio(add('correct'), add('fields'))}   closed {ratio(sens('closed', 'correct'), sens('closed', 'fields'))}   open {ratio(sens('open', 'correct'), sens('open', 'fields'))}")
        print(f"  full form        neutral {ratio(sum(r['full_form'] for r in good), len(good))}   closed {ratio(sum(r['sensitivity']['closed']['full_form'] for r in good), len(good))}   open {ratio(sum(r['sensitivity']['open']['full_form'] for r in good), len(good))}")
        print(f"  errors           wrong {add('wrong')}  missed {add('missed')}  fabricated {add('fabricated')}  unsafe {add('unsafe')}  submitted {sum(r['submitted'] for r in good)}")
        print(f"  unknowns         held {ratio(add('unknown_held'), add('unknown'))}   flagged {ratio(add('unknown_flagged'), add('unknown'))}")
        print(f"  absent facts     {absent}")
        print(f"  evidence         {ratio(add('evidence_valid'), add('evidence_needed'))}")
        seconds = sorted(r["seconds"] for r in good)
        print(f"  per form         median {statistics.median(seconds):.1f} s  worst {seconds[-1]:.1f} s  ${add('cost_usd') / len(good):.4f}  {add('model_calls') / len(good):.1f} model calls  {(add('input') + add('cached') + add('output')) / len(good):,.0f} tokens")
    print(f"\ntotal cost ${sum(json.loads(p.read_text())['cost_usd'] for p in files):.4f} across {len(files)} runs")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=["browser-tools", "frontier-tools"])
    ap.add_argument("--models", nargs="+", default=["deepseek-v4p1-flash"])
    ap.add_argument("--forms", nargs="+", default=FORMS)
    ap.add_argument("--patients", nargs="+", default=PATIENTS)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    jobs = [(arm, model, form, patient, repeat) for arm in args.arms for model in args.models for form in args.forms
            for patient in args.patients for repeat in range(1, args.repeats + 1)]
    if not args.summary:
        random.Random(args.seed).shuffle(jobs)
        with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
            for line in pool.map(one, jobs):
                print(line, flush=True)
    summary([p for job in jobs if (p := result_path(*job)).exists()])


if __name__ == "__main__":
    main()
