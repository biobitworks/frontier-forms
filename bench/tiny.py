"""Can a very small model work if a script narrows its job first?

    tiny.py --model qwen3.5:0.8b [--facts 6]

One question per call. A script picks the few profile lines that share words with the question and
sends only those, and single choices are limited to their options by the decoding grammar.
Scored with the same checks as evals/answers/run.py.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import time

import httpx

from bench import CASES, LLAMA, OLLAMA, PROFILE, score

STOP = set("a an and are at do does for have has how in is it of on or the to what which with you your".split())


def words(text: str) -> set[str]:
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9+#]+", text.lower()) if w not in STOP}


FACTS = [line.strip("- ").strip() for line in PROFILE.prompt_block().splitlines() if len(line.strip()) > 8]


def narrow(label: str, k: int) -> list[str]:
    asked = words(label)
    ranked = sorted(FACTS, key=lambda line: len(asked & words(line)) / (1 + len(words(line)) ** 0.5), reverse=True)
    return ranked[:k]


def reply_schema(case: dict) -> dict:
    if case["type"] == "select":
        value = {"type": "string", "enum": case["options"]}
    elif case["type"] == "multiselect":
        value = {"type": "array", "items": {"type": "string", "enum": case["options"]}}
    else:
        value = {"type": "string"}
    return {"type": "object", "properties": {"answer": value}, "required": ["answer"]}


async def main(args):
    rows, started = [], time.perf_counter()
    async with httpx.AsyncClient(timeout=120) as client:
        for case in CASES:
            facts = "\n".join(f"- {f}" for f in narrow(case["label"], args.facts))
            messages = [{"role": "system", "content": "Answer the question about the applicant using only these facts. "
                         "If the facts do not say yes, the answer is No. Be brief."},
                        {"role": "user", "content": f"FACTS:\n{facts}\n\nQUESTION: {case['label']}"}]
            if args.llama:
                reply = await client.post(f"{LLAMA}/chat/completions", json={
                    "model": args.model, "temperature": 0, "max_tokens": 120, "messages": messages,
                    "chat_template_kwargs": {"enable_thinking": False},
                    "response_format": {"type": "json_schema", "json_schema": {"name": "answer", "schema": reply_schema(case)}}})
            else:
                reply = await client.post(f"{OLLAMA}/api/chat", json={
                    "model": args.model, "stream": False, "think": False, "keep_alive": "30m", "format": reply_schema(case),
                    "options": {"temperature": 0, "num_ctx": 2048, "num_predict": 120}, "messages": messages})
            reply.raise_for_status()
            body = reply.json()
            try:
                text = body["choices"][0]["message"]["content"] if args.llama else body["message"]["content"]
                value = json.loads(text)["answer"]
            except (ValueError, KeyError, TypeError):
                value = None
            tokens = (body.get("usage") or {}).get("prompt_tokens", 0) if args.llama else body.get("prompt_eval_count", 0)
            rows.append({"id": case["id"], "type": case["type"], "ok": score(case, value), "value": value,
                         "prompt_tokens": tokens})
    def rate(kinds):
        picked = [r for r in rows if r["type"] in kinds]
        return f"{sum(r['ok'] for r in picked)}/{len(picked)}"
    print(json.dumps({"model": args.model, "facts": args.facts, "overall": rate({"select", "multiselect", "text", "textarea"}),
                      "select": rate({"select"}), "multiselect": rate({"multiselect"}), "free_text": rate({"text", "textarea"}),
                      "seconds": round(time.perf_counter() - started, 1),
                      "mean_prompt_tokens": sum(r["prompt_tokens"] for r in rows) // len(rows),
                      "wrong": [(r["id"], str(r["value"])[:50]) for r in rows if not r["ok"]]}), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3.5:0.8b")
    ap.add_argument("--facts", type=int, default=6)
    ap.add_argument("--llama", action="store_true", help="use the llama-server on port 8099 instead of Ollama")
    asyncio.run(main(ap.parse_args()))
