"""Run an arm against the local form server and score it with the gold oracle.

Every case is (patient, template) where the template is allowed in the
patient's declared split. The arm talks to the server over loopback HTTP the
way a browser-side filler would: GET the HTML form, GET the passport, POST a
fill plan, then the harness checks the server echo (post-fill validation).

Output rows are content-addressed and contain no timestamps, so two runs on
the same inputs produce byte-identical predictions and the same output root.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.request

from .cohort import cohort_root, merkle_root, sha256_bytes
from .oracle import ORACLE_VERSION, gold_answers

NUM_TOL = 0.05


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().casefold()


def value_matches(gold: dict, pred_value) -> bool:
    if gold["kind"] == "number":
        try:
            return abs(float(pred_value) - float(gold["value"])) <= NUM_TOL
        except (TypeError, ValueError):
            return False
    if gold["kind"] == "list":
        items = {norm(x) for x in str(pred_value).split(";") if norm(x)}
        return items == {norm(x) for x in gold["value"]}
    return norm(pred_value) == norm(gold["value"])


def score_field(gold: dict, pred: dict | None) -> dict:
    pdec = (pred or {}).get("decision", "missing")
    pval = (pred or {}).get("value")
    if pdec != gold["decision"]:
        correct = False
    elif pdec == "fill":
        correct = value_matches(gold, pval)
    else:
        correct = True
    if correct:
        outcome = "correct"
    elif pdec == "fill" and gold["decision"] != "fill":
        outcome = "unsupported_fill"
    elif pdec == "fill":
        outcome = "wrong_value"
    elif gold["decision"] == "fill":
        outcome = "missed_fill"
    else:
        outcome = "wrong_abstention"
    return {"correct": correct, "outcome": outcome, "gold_decision": gold["decision"],
            "pred_decision": pdec, "required": gold["required"]}


def _http(base, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(base + path, data=data,
                                 headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        return json.loads(body) if r.headers.get_content_type().endswith("json") else body.decode()


def run_arm(base_url, members, bundles, templates, arm_fn, arm_name):
    rows = []
    for m in members:
        passport = _http(base_url, f"/api/passport/{m.patient_id}")
        for tkey in sorted(templates):
            t = templates[tkey]
            if m.split not in t["splits"]:
                continue
            html = _http(base_url, f"/forms/{tkey}")
            plan = arm_fn(html, passport)
            echo = _http(base_url, f"/forms/{tkey}/submit", {"patient_id": m.patient_id, "answers": plan["answers"]})
            sent = sorted(plan["answers"], key=lambda a: a["field_key"])
            echo_ok = bool(echo.get("accepted")) and echo.get("answers") == json.loads(json.dumps(sent))
            gold = gold_answers(bundles[m.patient_id], t)
            pred = {a["field_key"]: a for a in plan["answers"]}
            fields = {k: score_field(g, pred.get(k)) for k, g in sorted(gold.items())}
            req_ok = all(f["correct"] for f in fields.values() if f["required"])
            case_key = f"{m.patient_id}|{tkey}"
            row = {
                "case_key": case_key,
                "case_digest_sha256": sha256_bytes(f"{case_key}|{m.sha256}|{ORACLE_VERSION}".encode()),
                "patient_id": m.patient_id,
                "split": m.split,
                "template_key": tkey,
                "task": tkey,
                "arm": arm_name,
                "echo_validated": echo_ok,
                "fields": fields,
                "required_fields_correct": req_ok,
                "all_fields_correct": all(f["correct"] for f in fields.values()),
                "plan_sha256": sha256_bytes(json.dumps(sent, sort_keys=True).encode()),
            }
            rows.append(row)
    return rows


def summarize(rows):
    def agg(rs):
        fs = [f for r in rs for f in r["fields"].values()]
        filled = [f for f in fs if f["pred_decision"] == "fill"]
        unknown = [f for f in fs if f["gold_decision"] != "fill"]
        outcomes = {}
        for f in fs:
            outcomes[f["outcome"]] = outcomes.get(f["outcome"], 0) + 1
        n = len(rs)
        return {
            "forms": n,
            "fields": len(fs),
            "field_accuracy": round(sum(f["correct"] for f in fs) / len(fs), 6) if fs else None,
            "full_form_success_required": round(sum(r["required_fields_correct"] for r in rs) / n, 6) if n else None,
            "full_form_success_all_fields": round(sum(r["all_fields_correct"] for r in rs) / n, 6) if n else None,
            "unsupported_answer_rate": round(sum(f["outcome"] == "unsupported_fill" for f in filled) / len(filled), 6) if filled else None,
            "missing_data_recall": round(sum(f["pred_decision"] == f["gold_decision"] for f in unknown) / len(unknown), 6) if unknown else None,
            "echo_validation_failures": sum(not r["echo_validated"] for r in rs),
            "outcomes": dict(sorted(outcomes.items())),
            "evidence_correctness": "NOT_COMPUTED: B0 emits no evidence ids",
        }
    out = {"overall": agg(rows), "by_split": {}, "by_template": {}, "by_split_template": {}}
    for key, groups in (("by_split", lambda r: r["split"]), ("by_template", lambda r: r["template_key"]),
                        ("by_split_template", lambda r: f"{r['split']}|{r['template_key']}")):
        buckets = {}
        for r in rows:
            buckets.setdefault(groups(r), []).append(r)
        out[key] = {k: agg(v) for k, v in sorted(buckets.items())}
    return out


def per_field_accuracy(rows):
    acc = {}
    for r in rows:
        for k, f in r["fields"].items():
            a = acc.setdefault(f"{r['template_key']}.{k}", [0, 0])
            a[0] += f["correct"]
            a[1] += 1
    return {k: {"correct": c, "n": n, "accuracy": round(c / n, 6)} for k, (c, n) in sorted(acc.items())}


def output_root(rows) -> str:
    return merkle_root([sha256_bytes(json.dumps(r, sort_keys=True).encode()) for r in rows])


def jsonl(rows) -> bytes:
    return b"".join(json.dumps(r, sort_keys=True).encode() + b"\n" for r in rows)


__all__ = ["run_arm", "summarize", "per_field_accuracy", "output_root", "jsonl", "cohort_root"]
