#!/usr/bin/env python3
"""LoRA SFT of a small open model as the frontier-forms field mapper (local only).

Lane: frontier-forms only. No data, checkpoints or results from other programs.
No hosted inference. Runs on Apple MPS, CUDA or CPU.

    python3 scripts/train_forms_sft.py --base Qwen/Qwen2.5-0.5B-Instruct --out runs/forms_sft_v1

Loss is computed on the completion tokens only. The epoch with the lowest
validation loss is kept. A receipt with dataset hashes, base model revision,
hyperparameters, losses and wall time is written next to the adapter.
"""
import argparse
import hashlib
import json
import math
import platform
import random
import time
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/forms_sft_v1"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(split):
    return [json.loads(x) for x in (DATA / f"{split}.jsonl").read_text().splitlines()]


def encode(tok, row, max_len):
    p = tok(row["prompt"], add_special_tokens=False)["input_ids"]
    c = tok(row["completion"] + tok.eos_token, add_special_tokens=False)["input_ids"]
    ids = (p + c)[-max_len:]
    labels = ([-100] * len(p) + c)[-max_len:]
    return torch.tensor([ids]), torch.tensor([labels])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-0.5B-Instruct")
    ap.add_argument("--revision", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=1536)
    ap.add_argument("--seed", type=int, default=20261102)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--dtype", default="float32", choices=["float32", "bfloat16", "float16"],
                    help="base-weight dtype; LoRA adapter weights stay float32")
    ap.add_argument("--dora", action="store_true",
                    help="DoRA (weight-decomposed low-rank adaptation, NVIDIA; Liu et al. 2024) instead of plain LoRA")
    ap.add_argument("--grad-ckpt", action="store_true", help="gradient checkpointing (less memory, slower)")
    args = ap.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(args.base, revision=args.revision)
    model = AutoModelForCausalLM.from_pretrained(args.base, revision=args.revision, torch_dtype=getattr(torch, args.dtype))
    base_rev = getattr(model.config, "_commit_hash", None)
    if args.grad_ckpt:
        model.gradient_checkpointing_enable()
        model.enable_input_require_grads()
        model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05, task_type="CAUSAL_LM", use_dora=args.dora,
                                             target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                                             "gate_proj", "up_proj", "down_proj"]))
    for p in model.parameters():
        if p.requires_grad:
            p.data = p.data.float()
    model.to(dev)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=0.0)
    train, val = load("train"), load("validation")
    total_steps = math.ceil(len(train) / args.accum) * args.epochs
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 20) * max(0.0, 1 - s / total_steps))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log, best, t0, step = [], None, time.time(), 0

    def val_loss():
        model.eval()
        tot, n = 0.0, 0
        with torch.no_grad():
            for r in val:
                ids, lab = encode(tok, r, args.max_len)
                loss = model(input_ids=ids.to(dev), labels=lab.to(dev)).loss
                tot += loss.item()
                n += 1
        model.train()
        return tot / n

    v0 = val_loss()
    log.append({"epoch": 0, "val_loss": v0})
    print(json.dumps(log[-1]), flush=True)
    model.train()
    for ep in range(1, args.epochs + 1):
        order = list(range(len(train)))
        random.Random(args.seed + ep).shuffle(order)
        run = 0.0
        for i, j in enumerate(order, 1):
            ids, lab = encode(tok, train[j], args.max_len)
            loss = model(input_ids=ids.to(dev), labels=lab.to(dev)).loss / args.accum
            loss.backward()
            run += loss.item()
            if i % args.accum == 0 or i == len(order):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                sched.step()
                opt.zero_grad()
                step += 1
                if step % 20 == 0:
                    print(json.dumps({"epoch": ep, "step": step, "train_loss": round(run * args.accum / (args.accum * 20), 4),
                                      "elapsed_s": round(time.time() - t0)}), flush=True)
                    run = 0.0
        v = val_loss()
        log.append({"epoch": ep, "val_loss": v, "elapsed_s": round(time.time() - t0)})
        print(json.dumps(log[-1]), flush=True)
        if best is None or v < best[1]:
            best = (ep, v)
            model.save_pretrained(out / "adapter")
            tok.save_pretrained(out / "adapter")
    adapter_files = {p.name: sha(p) for p in sorted((out / "adapter").glob("*")) if p.is_file()}
    receipt = {
        "run_id": out.name, "lane": "frontier-forms", "task": "field mapper SFT (prompt sft-prompt-v1)",
        "base_model": args.base, "base_revision": base_rev, "method": "DoRA" if args.dora else "LoRA", "lora_rank": args.rank,
        "hyperparameters": {"epochs": args.epochs, "lr": args.lr, "grad_accum": args.accum, "max_len": args.max_len,
                            "seed": args.seed, "dtype": args.dtype, "adapter_dtype": "float32", "gradient_checkpointing": args.grad_ckpt, "warmup_steps": 20, "schedule": "linear decay"},
        "data": {"train_sha256": sha(DATA / "train.jsonl"), "validation_sha256": sha(DATA / "validation.jsonl"),
                 "manifest_sha256": sha(DATA / "MANIFEST.json")},
        "selected_epoch": best[0], "selected_val_loss": best[1], "log": log,
        "adapter_sha256": adapter_files, "device": dev,
        "host": {"machine": platform.machine(), "platform": platform.platform(), "torch": torch.__version__},
        "wall_seconds": round(time.time() - t0), "hosted_inference": "NONE",
        "selection_rule": "lowest validation loss across epochs; test split never read",
    }
    (out / "TRAIN_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print("DONE", json.dumps({"selected_epoch": best[0], "val_loss": best[1]}), flush=True)


if __name__ == "__main__":
    main()
