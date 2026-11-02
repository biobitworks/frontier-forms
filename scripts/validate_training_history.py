#!/usr/bin/env python3
"""Validate public-safe append-only FCG training history. No network or DB access."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from urllib.parse import urlparse

STATES = {"PROPOSED", "IMPLEMENTED", "EXECUTED", "OBSERVED", "SUPPORTED",
          "FAILED", "FAIL", "PASS", "NEGATIVE", "NULL", "DEFERRED", "NOT_TESTED",
          "NOT_COMPUTED", "UNKNOWN", "REPORTED", "BLOCKED"}
GATES = {"source_bytes", "deterministic_replay", "split_isolation", "inference",
         "evaluation", "independent_replication", "supabase", "github_writeback"}
FORBIDDEN = ("password", "secret_key", "DATABASE_URL=", "service_role=", "postgresql://")

def validate(doc: dict) -> list[str]:
    errors = []
    if doc.get("schema") != "frontier_forms.training_history.v1":
        errors.append("invalid schema")
    if set(doc.get("gate_order", [])) != GATES:
        errors.append("incomplete or duplicate gates")
    seen = {}
    events = doc.get("events", [])
    if not isinstance(events, list) or not events:
        return errors + ["empty event list"]
    for i, e in enumerate(events):
        prefix = f"event[{i}]"
        ident = e.get("id")
        if not isinstance(ident, str) or not ident or ident in seen:
            errors.append(prefix + " missing/duplicate id")
        if e.get("sequence") != i + 1:
            errors.append(prefix + " sequence must be append-only and consecutive")
        if e.get("state") not in STATES:
            errors.append(prefix + " invalid state")
        parent = e.get("parent")
        if parent is not None and parent not in seen:
            errors.append(prefix + " unknown/forward predecessor")
        if set(e.get("gates", {})) != GATES:
            errors.append(prefix + " missing gate or extra gate")
        if any(v not in STATES for v in e.get("gates", {}).values()):
            errors.append(prefix + " invalid gate value")
        url = urlparse(e.get("evidence_url", ""))
        if url.scheme != "https" or url.netloc != "github.com":
            errors.append(prefix + " non-GitHub evidence URL")
        metrics = e.get("metrics", {})
        if any(not isinstance(v, (int,float)) or not math.isfinite(v) for k,v in metrics.items()
               if k in ("mcnemar_p","paired_delta_pp","paired_n","baseline_correct","challenger_correct")):
            errors.append(prefix + " invalid numeric metric")
        if "paired_n" in metrics:
            n = metrics["paired_n"]
            b = metrics.get("baseline_correct")
            c = metrics.get("challenger_correct")
            if not isinstance(n, int) or n <= 0 or not isinstance(b,int) or not isinstance(c,int):
                errors.append(prefix + " invalid paired denominators")
            elif not (0 <= b <= n and 0 <= c <= n):
                errors.append(prefix + " out of range correctness counts")
            elif not math.isclose(metrics.get("paired_delta_pp",float("nan")),100*(c-b)/n,abs_tol=1e-7):
                errors.append(prefix + " incorrect paired effect")
            if "mcnemar_p" not in metrics or not (0<=metrics["mcnemar_p"]<=1):
                errors.append(prefix + " missing/invalid exact McNemar p")
            ci=metrics.get("bootstrap_ci")
            if not isinstance(ci,list) or len(ci)!=2 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in ci) or ci[0]>ci[1]:
                errors.append(prefix + " missing/invalid confidence interval")
        if e.get("state") == "SUPPORTED":
            ci=metrics.get("bootstrap_ci")
            if not ("paired_n" in metrics and metrics.get("mcnemar_p",2)<0.05 and
                    isinstance(ci,list) and len(ci)==2 and ci[0]>0 and
                    e.get("gates",{}).get("independent_replication")=="PASS"):
                errors.append(prefix + " unsupported promotion claim")
        if e.get("merkle_root") is not None and not e.get("root_verification_receipt"):
            errors.append(prefix + " root asserted without verification receipt")
        if not isinstance(metrics,dict):
            errors.append(prefix + " metrics must be object")
        seen[ident]=True
    text=json.dumps(doc,ensure_ascii=False)
    for token in FORBIDDEN:
        if token in text:
            errors.append("potential credential or connection string: "+token)
    return errors

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("path",nargs="?",default="dashboard/training_history.json")
    args=parser.parse_args()
    doc=json.loads(Path(args.path).read_text(encoding="utf-8"))
    errors=validate(doc)
    if errors:
        for error in errors: print("FAIL:",error)
        return 1
    print(f"PASS: {len(doc['events'])} validated events; no unsupported training promotion or credential fields")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
