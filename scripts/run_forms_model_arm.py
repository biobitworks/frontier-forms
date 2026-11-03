#!/usr/bin/env python3
"""Evaluate a local model (zero-shot base, or base + SFT adapter) as a form-filling arm.

Same server, same HTML forms, same teammate passport, same oracle and scorer
as B0. Only validation- and test-split patients are evaluated (training
patients are excluded). Greedy decoding.

    python3 scripts/run_forms_model_arm.py --base Qwen/Qwen2.5-0.5B-Instruct --adapter runs/forms_sft_v1/adapter \
        --name M1-sft-v1 --out evidence/forms_model/M1-sft-v1
    python3 scripts/run_forms_model_arm.py --base Qwen/Qwen2.5-0.5B-Instruct --name M0-zeroshot --out evidence/forms_model/M0-zeroshot
"""
import argparse
import json
import platform
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frontier_forms.forms import b0, sft_data  # noqa: E402
from frontier_forms.forms.cohort import cohort_root, load_cohort, sha256_bytes  # noqa: E402
from frontier_forms.forms.harness import jsonl, output_root, per_field_accuracy, run_arm, summarize  # noqa: E402
from frontier_forms.forms.server import FormState, serve  # noqa: E402
from frontier_forms.forms.statistics_bridge import paired_vs_b0  # noqa: E402
from frontier_forms.forms.templates import load_templates  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-0.5B-Instruct")
    ap.add_argument("--revision", default=None)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--splits", default="validation,test")
    ap.add_argument("--dtype", default="float32", choices=["float32", "bfloat16", "float16"])
    args = ap.parse_args()

    dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(args.adapter or args.base)
    model = AutoModelForCausalLM.from_pretrained(args.base, revision=args.revision, torch_dtype=getattr(torch, args.dtype))
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)
    model.to(dev).eval()
    calls = {"n": 0, "seconds": 0.0, "malformed": 0}
    answers_log = []
    adapter_sha = None
    if args.adapter:
        adapter_sha = {p.name: sha256_bytes(p.read_bytes()) for p in sorted(Path(args.adapter).glob("*")) if p.is_file()}
    model_identity = {"base_model": args.base, "base_revision": getattr(model.config, "_commit_hash", None),
                      "adapter_path": args.adapter, "adapter_sha256": adapter_sha}

    def generate(text):
        ids = tok(text, return_tensors="pt", add_special_tokens=False).to(dev)
        t = time.perf_counter()
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=192, do_sample=False, pad_token_id=tok.eos_token_id)
        dt = time.perf_counter() - t
        calls["n"] += 1
        calls["seconds"] += dt
        return tok.decode(out[0, ids["input_ids"].shape[1]:], skip_special_tokens=True), dt

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
            if not raw.strip().startswith("{"):
                calls["malformed"] += 1
            answers.append({"field_key": f["name"], "decision": dec, "value": val,
                            "evidence_fact_ids": [], "reason": args.name})
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
    # join each raw model answer to its scored outcome
    score = {(r["patient_id"], r["template_key"], k): v for r in rows for k, v in r["fields"].items()}
    tkey_of = {}
    for r in rows:
        for k in r["fields"]:
            tkey_of.setdefault((r["patient_id"], k), r["template_key"])
    for a in answers_log:
        a["template_key"] = tkey_of.get((a["patient_id"], a["field_key"]))
        sc = score.get((a["patient_id"], a["template_key"], a["field_key"]), {})
        a["outcome"] = sc.get("outcome")
        a["gold_decision"] = sc.get("gold_decision")
        a["model"] = args.name
    (out / "answers.jsonl").write_bytes(jsonl(answers_log))
    summary = {"arm": args.name, "metrics": summarize(rows), "per_field_accuracy": per_field_accuracy(rows),
               "paired_vs_B0": paired_vs_b0(b0_rows, rows)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    receipt = {"arm": args.name, **model_identity, "splits": sorted(keep), "n_patients": len(members), "n_cases": len(rows),
               "cohort_root_evaluated": cohort_root(members), "predictions_sha256": sha256_bytes(data),
               "output_root": output_root(rows), "decoding": "greedy, max_new_tokens=192", "dtype": args.dtype,
               "model_calls": calls["n"], "model_seconds": round(calls["seconds"], 1),
               "malformed_outputs": calls["malformed"], "wall_seconds": round(elapsed, 1), "device": dev,
               "host": {"machine": platform.machine(), "platform": platform.platform(), "torch": torch.__version__},
               "hosted_inference": "NONE"}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    o = summary["metrics"]
    print(json.dumps({"overall": o["overall"]["full_form_success_required"],
                      "test": o["by_split"].get("test", {}).get("full_form_success_required"),
                      "field_acc": o["overall"]["field_accuracy"],
                      "vs_B0": summary["paired_vs_B0"]["overall"]["table"]}))


if __name__ == "__main__":
    main()
