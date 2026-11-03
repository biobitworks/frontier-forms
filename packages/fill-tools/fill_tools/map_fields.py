"""map_fields: the only step that uses a model. It returns a fill plan, never code (spec 10.2)."""
from __future__ import annotations

import concurrent.futures
import json
import os
import re
import time
from dataclasses import dataclass, field

import httpx

ENDPOINT = "https://api.fireworks.ai/inference/v1/chat/completions"
BATCH = 12
PARALLEL = 4
SYSTEM = """You complete a form for a synthetic patient. You receive the questions and the relevant lines of the patient's record.
Return JSON only: {"answers":[{"field_key":"...","decision":"fill|needs_user_input|needs_review","value":...,"evidence_fact_ids":["..."],"reason":"..."}]}, one entry per question.

Rules:
- Use only what the record supports. Do not guess.
- If the record has no answer, use needs_user_input. If the fact is conflicted or expired, use needs_review. Either way value is null.
- For current medications, list only active ones, not past ones.
- evidence_fact_ids holds the id at the start of each record line used, such as F0012 or demographics.given_name.
- Where options are given, value must copy one option exactly. For type checks, value is a list of options.
- Convert units and date formats when the question asks. Dates are YYYY-MM-DD unless the question or hint gives another format.
- For type repeat, value is a list of rows, each an object keyed by the given columns, with one row per item."""


@dataclass
class Usage:
    prices: dict
    calls: int = 0
    input: int = 0
    cached: int = 0
    output: int = 0
    failed_calls: int = 0
    model_seconds: float = 0.0

    def add(self, usage: dict, seconds: float) -> None:
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
        self.calls += 1
        self.input += usage.get("prompt_tokens", 0) - cached
        self.cached += cached
        self.output += usage.get("completion_tokens", 0)
        self.model_seconds += seconds

    def row(self) -> dict:
        cost = (self.input * self.prices["input"] + self.cached * self.prices["cacheRead"] + self.output * self.prices["output"]) / 1e6
        return {"model_calls": self.calls, "input": self.input, "cached": self.cached, "output": self.output, "cost_usd": cost,
                "failed_calls": self.failed_calls, "model_seconds": round(self.model_seconds, 2)}


def parse(text: str) -> dict:
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    start = text.find("{")
    return json.loads(text[start:text.rfind("}") + 1])


def ask(client: httpx.Client, model: str, user: str, usage: Usage) -> list[dict]:
    body = {"model": f"accounts/fireworks/models/{model}", "temperature": 0, "max_tokens": 16000, "reasoning_effort": "low",
            "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
    last = None
    for attempt in range(4):
        started = time.perf_counter()
        try:
            reply = client.post(ENDPOINT, json=body, headers={"Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY']}"})
            if reply.status_code in (429, 500, 502, 503, 529):
                raise httpx.HTTPError(f"status {reply.status_code}")
            reply.raise_for_status()
            data = reply.json()
            usage.add(data.get("usage") or {}, time.perf_counter() - started)
            return parse(data["choices"][0]["message"]["content"] or "")["answers"]
        except (httpx.HTTPError, ValueError, KeyError) as error:
            last = error
            usage.failed_calls += 1
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"model call failed: {last}")


def map_fields(fields: list, passport, model: str, usage: Usage) -> dict[str, dict]:
    """{field key: answer}. Fields go in small batches at once, each with only the facts its questions need."""
    short = {f"f{i}": f for i, f in enumerate(fields, 1)}
    batches = [list(short.items())[i:i + BATCH] for i in range(0, len(short), BATCH)]

    def one(batch) -> list[dict]:
        rows = [{**field.public(), "field_key": key} for key, field in batch]
        record = passport.retrieve([field.asked() for _, field in batch])
        user = f"Questions:\n{json.dumps(rows, indent=0)}\n\nRecord:\n{record}"
        with httpx.Client(timeout=120) as client:
            return ask(client, model, user, usage)

    plan = {}
    with concurrent.futures.ThreadPoolExecutor(PARALLEL) as pool:
        for answers in pool.map(one, batches):
            for answer in answers:
                if answer.get("field_key") in short:
                    plan[short[answer["field_key"]].key] = answer
    return plan
