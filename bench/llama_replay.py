"""The same 16 engine prompts against llama-server, reading its own cache and timing counters.

    llama_replay.py --endpoint http://127.0.0.1:8099 --parallel 1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time

import httpx

from replay import prompts


async def call(client, endpoint, prompt):
    system, user, schema = prompt
    started = time.perf_counter()
    reply = await client.post(f"{endpoint}/v1/chat/completions", json={
        "model": "local", "temperature": 0, "max_tokens": 2048, "cache_prompt": True,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {"type": "json_schema", "json_schema": {"name": "answers", "schema": schema}},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    reply.raise_for_status()
    timings = reply.json().get("timings", {})
    return {"wall_s": round(time.perf_counter() - started, 2), "cached": timings.get("cache_n"),
            "prompt_evaluated": timings.get("prompt_n"), "prompt_s": round(timings.get("prompt_ms", 0) / 1000, 2),
            "output_tokens": timings.get("predicted_n"), "output_s": round(timings.get("predicted_ms", 0) / 1000, 2)}


async def main(args):
    calls = await prompts(4)
    async with httpx.AsyncClient(timeout=600) as client:
        await call(client, args.endpoint, calls[1])  # warm
        gate = asyncio.Semaphore(args.parallel)

        async def one(prompt):
            async with gate:
                return await call(client, args.endpoint, prompt)

        started = time.perf_counter()
        rows = await asyncio.gather(*[one(p) for p in calls])
        wall = time.perf_counter() - started
    print(json.dumps({"server": "llama-server", "parallel": args.parallel, "model_calls": len(rows), "wall_s": round(wall, 1),
                      "prompt_s_sum": round(sum(r["prompt_s"] for r in rows), 1),
                      "output_s_sum": round(sum(r["output_s"] for r in rows), 1),
                      "output_tokens": sum(r["output_tokens"] or 0 for r in rows), "calls": rows[:5]}), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:8099")
    ap.add_argument("--parallel", type=int, default=1)
    asyncio.run(main(ap.parse_args()))
