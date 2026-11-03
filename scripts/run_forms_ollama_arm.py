#!/usr/bin/env python3
"""Local Ollama model as a form-filling arm (text). Standard library only.

Same server, HTML forms, teammate passport, prompt (sft-prompt-v1), oracle and
scorer as the other arms. Validation + test patients only. Temperature 0,
fixed seed. Every raw model answer is written to answers.jsonl with the model
digest, so each outcome is traceable to exact local weights.

    python3 scripts/run_forms_ollama_arm.py --model qwen3:1.7b --name M2-qwen3-1.7b --out evidence/forms_model/M2-qwen3-1.7b
"""
import argparse
import json
import platform
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frontier_forms.forms import b0, sft_data  # noqa: E402
from frontier_forms.forms.cohort import cohort_root, load_cohort, sha256_bytes  # noqa: E402
from frontier_forms.forms.harness import jsonl, output_root, per_field_accuracy, run_arm, summarize  # noqa: E402
from frontier_forms.forms.server import FormState, serve  # noqa: E402
from frontier_forms.forms.statistics_bridge import paired_vs_b0  # noqa: E402
from frontier_forms.forms.templates import load_templates  # noqa: E402

OLLAMA = "http://127.0.0.1:11434"


def post(path, body, timeout=600):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def model_identity(model):
    tags = json.loads(urllib.request.urlopen(OLLAMA + "/api/tags", timeout=30).read())
    full = model if ":" in model else model + ":latest"  # Ollama lists untagged pulls as name:latest
    t = next((m for m in tags["models"] if m["name"] in (model, full) or m["model"] in (model, full)), None)
    show = post("/api/show", {"model": model})
    det = show.get("details", {})
    return {"runtime": "ollama", "model": model, "digest": t and t.get("digest"),
            "parameter_size": det.get("parameter_size"), "quantization": det.get("quantization_level"),
            "family": det.get("family")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--splits", default="validation,test")
    ap.add_argument("--seed", type=int, default=20261102)
    args = ap.parse_args()
    ident = model_identity(args.model)
    calls = {"n": 0, "seconds": 0.0}
    answers_log = []

    def generate(text):
        body = {"model": args.model, "prompt": text, "stream": False, "think": False,
                "options": {"temperature": 0, "seed": args.seed, "num_predict": 192}}
        t = time.perf_counter()
        try:
            r = post("/api/generate", body)
        except urllib.error.HTTPError:
            body.pop("think")  # model without a thinking switch
            r = post("/api/generate", body)
        dt = time.perf_counter() - t
        calls["n"] += 1
        calls["seconds"] += dt
        return r.get("response", ""), dt

    def fill_plan(html, passport):
        ptxt = sft_data.passport_text(passport)
        answers = []
        for f in b0.inspect_form(html):
            field = {"label": f["label"], "type": f["type"] if f["type"] in ("textarea", "select", "number") else "text",
                     "options": f["options"]}
            prompt_text = sft_data.prompt(field, ptxt)
            raw, dt = generate(prompt_text)
            dec, val = sft_data.parse_completion(raw)
            answers_log.append({"patient_id": passport["patient_id"], "field_key": f["name"], "label": f["label"],
                                "prompt_sha256": sha256_bytes(prompt_text.encode()), "raw_output": raw,
                                "parsed_decision": dec, "written_value": val, "latency_s": round(dt, 3)})
            answers.append({"field_key": f["name"], "decision": dec, "value": val, "evidence_fact_ids": [], "reason": args.name})
        return {"arm": args.name, "answers": answers}

    keep = set(args.splits.split(","))
    members, bundles = load_cohort(ROOT / "data/forms_cohort_v1/bundles")
    members = [m for m in members if m.split in keep]
    templates = load_templates()
    httpd = serve(FormState(members, bundles, templates))
    t0 = time.perf_counter()
    try:
        rows = run_arm(f"http://127.0.0.1:{httpd.server_address[1]}", members, bundles, templates, fill_plan, args.name)
    finally:
        httpd.shutdown()
        httpd.server_close()
    elapsed = time.perf_counter() - t0
    b0_rows = [json.loads(x) for x in (ROOT / "evidence/forms_b0/run_v1/predictions.jsonl").read_text().splitlines()]
    b0_rows = [r for r in b0_rows if r["split"] in keep]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data = jsonl(rows)
    (out / "predictions.jsonl").write_bytes(data)
    tkey = {}
    score = {}
    for r in rows:
        for k, v in r["fields"].items():
            tkey.setdefault((r["patient_id"], k), r["template_key"])
            score[(r["patient_id"], r["template_key"], k)] = v
    for a in answers_log:
        a["template_key"] = tkey.get((a["patient_id"], a["field_key"]))
        sc = score.get((a["patient_id"], a["template_key"], a["field_key"]), {})
        a.update({"outcome": sc.get("outcome"), "gold_decision": sc.get("gold_decision"), "model": args.name})
    (out / "answers.jsonl").write_bytes(jsonl(answers_log))
    summary = {"arm": args.name, "metrics": summarize(rows), "per_field_accuracy": per_field_accuracy(rows),
               "paired_vs_B0": paired_vs_b0(b0_rows, rows)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    receipt = {"arm": args.name, "base_model": f"ollama:{args.model}", "base_revision": ident["digest"],
               "adapter_path": None, "adapter_sha256": None, "model_identity": ident,
               "splits": sorted(keep), "n_patients": len(members), "n_cases": len(rows),
               "cohort_root_evaluated": cohort_root(members), "predictions_sha256": sha256_bytes(data),
               "output_root": output_root(rows), "decoding": f"temperature 0, seed {args.seed}, num_predict 192, think false",
               "model_calls": calls["n"], "model_seconds": round(calls["seconds"], 1), "wall_seconds": round(elapsed, 1),
               "host": {"machine": platform.machine(), "platform": platform.platform()}, "hosted_inference": "NONE"}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    o = summary["metrics"]
    print(json.dumps({"overall": o["overall"]["full_form_success_required"],
                      "test": o["by_split"].get("test", {}).get("full_form_success_required"),
                      "field_acc": o["overall"]["field_accuracy"], "vs_B0": summary["paired_vs_B0"]["overall"]["table"]}))


if __name__ == "__main__":
    main()
