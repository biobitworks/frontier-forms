"""Replay the engine's own prompts to compare batching, concurrency and prompt-prefix reuse.

    replay.py --endpoint http://127.0.0.1:11434 --model qwen3.8:27b --what sequential|concurrent|one|prefix
"""
from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
import time
from pathlib import Path

import httpx

from bench import ANSWERS, CASES, NUM_CTX, POSTING, PROFILE, resolver_module  # noqa: F401
from auto_apply.answer_cache import AnswerCache
from auto_apply.config import Settings
from auto_apply.models import ApplicationSchema, Ats, FieldType, FormField


class Capture:
    def __init__(self):
        self.calls = []

    async def answer(self, system, user, schema_model):
        self.calls.append((system, user, schema_model.model_json_schema()))
        return resolver_module._LlmAnswers()


async def prompts(batch: int):
    fields = [FormField(key=c["id"], label=c["label"], type=FieldType(c["type"]), required=True,
                        options=c.get("options", [])) for c in CASES]
    schema = ApplicationSchema(ats=Ats.GREENHOUSE, job_url="https://example.invalid/job", company="Northwind Payments",
                               job_title="Senior Backend Engineer", location="San Francisco, California (Hybrid)",
                               posting_text=POSTING, fields=fields)
    qa = Capture()
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(_env_file=None, data_dir=tmp, llm_batch_size=batch, embedding_model="")
        cache = AnswerCache(Path(tmp) / "cache.db")
        await resolver_module.Resolver(settings, PROFILE, cache, qa).resolve(schema)
        cache.close()
    return qa.calls


async def call(client, args, prompt, keep_alive="30m"):
    system, user, schema = prompt
    started = time.perf_counter()
    reply = await client.post(f"{args.endpoint}/api/chat", json={
        "model": args.model, "stream": False, "think": False, "keep_alive": keep_alive, "format": schema,
        "options": {"temperature": 0, "num_ctx": NUM_CTX},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    reply.raise_for_status()
    body = reply.json()
    return {"wall_s": round(time.perf_counter() - started, 2), "load_s": round(body.get("load_duration", 0) / 1e9, 2),
            "prompt_tokens": body.get("prompt_eval_count", 0), "prompt_s": round(body.get("prompt_eval_duration", 0) / 1e9, 2),
            "output_tokens": body.get("eval_count", 0), "output_s": round(body.get("eval_duration", 0) / 1e9, 2)}


def summary(what, rows, wall):
    print(json.dumps({"what": what, "model_calls": len(rows), "wall_s": round(wall, 1),
                      "prompt_tokens": sum(r["prompt_tokens"] for r in rows),
                      "output_tokens": sum(r["output_tokens"] for r in rows),
                      "output_tok_per_s": round(sum(r["output_tokens"] for r in rows) / max(sum(r["output_s"] for r in rows), .01), 1),
                      "calls": rows if len(rows) <= 4 else rows[:2]}), flush=True)


async def main(args):
    async with httpx.AsyncClient(timeout=600) as client:
        if args.what == "prefix":
            first = (await prompts(4))[:2]
            await call(client, args, first[0], keep_alive=0)   # leaves the model unloaded
            for label, prompt in [("cold load", first[0]), ("same prefix, new questions", first[1]),
                                  ("identical request", first[1])]:
                print(json.dumps({"what": label, **await call(client, args, prompt)}), flush=True)
            return
        batch = 0 if args.what == "one" else 4
        calls = await prompts(batch)
        await call(client, args, calls[0])  # warm
        started = time.perf_counter()
        if args.what == "concurrent":
            gate = asyncio.Semaphore(args.parallel)

            async def one(prompt):
                async with gate:
                    return await call(client, args, prompt)

            rows = await asyncio.gather(*[one(p) for p in calls])
        else:
            rows = [await call(client, args, p) for p in calls]
        summary(f"{args.what} (parallel={args.parallel})" if args.what == "concurrent" else args.what,
                rows, time.perf_counter() - started)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="qwen3.8:27b")
    ap.add_argument("--what", required=True, choices=["sequential", "concurrent", "one", "prefix"])
    ap.add_argument("--parallel", type=int, default=3)
    asyncio.run(main(ap.parse_args()))
