"""Form-fill benchmark: model-driven tool loop vs scripted fill (batched, streamed).

    bench.py --mode toolloop|batched|streamed --model qwen3.8:27b --form a|b [--batch N] [--trials 3]
    bench.py --mode batched --groups 6 --reply lines --writes all --model ... --form a|b

Form a is evals/fallback/form.html (12 fields). Form b is built from evals/answers/cases.yaml, so
every question has an expected answer. Both run offline, headless, and never press Submit.

--groups asks the model in N groups at the same time, --reply lines asks for `N: answer` lines
instead of JSON, and --writes all fills the whole form in one page.evaluate. Each can be turned on
alone, so the gain from each one can be measured separately.
"""
from __future__ import annotations

import argparse
import asyncio
import contextvars
import functools
import http.server
import json
import math
import re
import sys
import tempfile
import threading
import time
from html import escape
from pathlib import Path

import httpx
import yaml

ROOT = Path("/Users/reuben/github/hobby/Job-Applicator")
sys.path[:0] = [str(ROOT), str(ROOT / "engine")]

from auto_apply import dom  # noqa: E402
from auto_apply import resolver as resolver_module  # noqa: E402
from auto_apply.answer_cache import AnswerCache  # noqa: E402
from auto_apply.browser import async_playwright  # noqa: E402
from auto_apply.config import Settings  # noqa: E402
from auto_apply.filler import Filler  # noqa: E402
from auto_apply.models import ApplicationSchema, Ats, FieldType  # noqa: E402
from auto_apply.profile import Profile  # noqa: E402
from evals.answers.run import score  # noqa: E402
from evals.fallback.run import CHECKS, READ  # noqa: E402

OLLAMA = "http://127.0.0.1:11434"
NUM_CTX = 8192
FIREWORKS = "https://api.fireworks.ai/inference/v1"
LLAMA = "http://127.0.0.1:8099/v1"
# Which question each streamed answer belongs to, per batch, so batches can run side by side.
CURRENT_BATCH: contextvars.ContextVar[dict] = contextvars.ContextVar("current_batch")


def fireworks_key() -> str:
    for line in (Path(__file__).resolve().parents[1] / ".env").read_text().splitlines():
        match = re.match(r"\s*FIREWORKS_API_KEY\s*=\s*(.*)$", line)
        if match:
            return match[1].strip().strip("\"'")
    raise SystemExit("FIREWORKS_API_KEY is not in .env")


def fireworks_options(model: str) -> dict:
    """GLM 5.3 always thinks: it refuses effort "none", and the thinking needs room in max_tokens."""
    if "glm-5p3" in model:
        return {"reasoning_effort": "low", "max_tokens": 16000}
    return {"reasoning_effort": "none"}


ANSWERS = ROOT / "evals/answers"
PROFILE = Profile.model_validate(yaml.safe_load((ANSWERS / "profile.yaml").read_text()))
CASES = yaml.safe_load((ANSWERS / "cases.yaml").read_text())["cases"]
POSTING = (ANSWERS / "posting.txt").read_text()


def form_b_html() -> str:
    rows = []
    for c in CASES:
        label, name = escape(c["label"]), c["id"]
        if c["type"] == "select":
            opts = "".join(f"<option>{escape(o)}</option>" for o in c["options"])
            rows.append(f'<p><label>{label} <select name="{name}"><option value="">Select...</option>{opts}</select></label></p>')
        elif c["type"] == "multiselect":
            boxes = "".join(f'<label><input type="checkbox" name="{name}" value="{escape(o)}"> {escape(o)}</label>'
                            for o in c["options"])
            rows.append(f"<fieldset><legend>{label}</legend>{boxes}</fieldset>")
        elif c["type"] == "textarea":
            rows.append(f'<p><label>{label} <textarea name="{name}" rows="3"></textarea></label></p>')
        else:
            rows.append(f'<p><label>{label} <input name="{name}"></label></p>')
    return ("<!doctype html><title>Apply</title><form id=f onsubmit='window.__submitted=true;return false'>"
            + "".join(rows) + "<button type=submit>Submit application</button></form>")


def serve(directory: Path):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class Meter:
    def __init__(self):
        self.calls = self.prompt_tokens = self.output_tokens = self.errors = 0
        self.prompt_ms = self.output_ms = 0.0
        self.cached_tokens = 0
        self.first_token: list[float] = []

    def add_usage(self, usage: dict, first_token_s: float | None, total_s: float) -> None:
        """OpenAI-style usage. The wait for the first token stands in for prompt time."""
        self.calls += 1
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.output_tokens += usage.get("completion_tokens", 0)
        self.cached_tokens += (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
        if first_token_s is not None:
            self.first_token.append(first_token_s)
            self.prompt_ms += first_token_s * 1000
            self.output_ms += (total_s - first_token_s) * 1000

    def add(self, final: dict) -> None:
        self.calls += 1
        self.prompt_tokens += final.get("prompt_eval_count", 0)
        self.output_tokens += final.get("eval_count", 0)
        self.prompt_ms += final.get("prompt_eval_duration", 0) / 1e6
        self.output_ms += final.get("eval_duration", 0) / 1e6

    def row(self) -> dict:
        return {"model_calls": self.calls, "prompt_tokens": self.prompt_tokens, "output_tokens": self.output_tokens,
                "prompt_s": round(self.prompt_ms / 1000, 2), "output_s": round(self.output_ms / 1000, 2),
                "cached_tokens": self.cached_tokens, "failed_calls": self.errors}


class AnswerStream:
    """Yields each complete {...} answer object from a growing {"answers":[{...},...]} reply."""

    def __init__(self):
        self.depth = 0
        self.in_string = self.escaped = False
        self.start = None
        self.text = ""

    def feed(self, chunk: str) -> list[str]:
        done = []
        for ch in chunk:
            self.text += ch
            if self.in_string:
                if self.escaped:
                    self.escaped = False
                elif ch == "\\":
                    self.escaped = True
                elif ch == '"':
                    self.in_string = False
            elif ch == '"':
                self.in_string = True
            elif ch == "{":
                self.depth += 1
                if self.depth == 2:
                    self.start = len(self.text) - 1
            elif ch == "}":
                if self.depth == 2 and self.start is not None:
                    done.append(self.text[self.start:])
                    self.start = None
                self.depth -= 1
        return done


class StreamQA:
    """Same request the app's ProviderQA sends, streamed, with token counts kept."""

    def __init__(self, model: str, meter: Meter, on_answer=None, provider: str = "ollama"):
        self.model, self.meter, self.on_answer, self.provider = model, meter, on_answer, provider

    async def _fireworks(self, system, user, schema_model):
        cloud = self.provider == "fireworks"
        payload = {"model": self.model, "stream": True, "stream_options": {"include_usage": True}, "temperature": 0,
                   "max_tokens": 4096, **(fireworks_options(self.model) if cloud else
                                          {"chat_template_kwargs": {"enable_thinking": False}}),
                   **({"response_format": {"type": "json_schema", "json_schema": {
                       "name": "answers", "schema": schema_model.model_json_schema()}}} if schema_model else {}),
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        stream, text, usage, first, started = AnswerStream(), "", {}, None, time.perf_counter()
        headers = {"Authorization": f"Bearer {fireworks_key()}"} if cloud else {}
        async with httpx.AsyncClient(timeout=600) as client:
            async with client.stream("POST", f"{FIREWORKS if cloud else LLAMA}/chat/completions",
                                     json=payload, headers=headers) as reply:
                if reply.status_code != 200:
                    raise RuntimeError(f"{self.provider} {reply.status_code}: {(await reply.aread())[:300]!r}")
                async for line in reply.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    part = json.loads(line[6:])
                    usage = part.get("usage") or usage
                    choices = part.get("choices") or [{}]
                    piece = (choices[0].get("delta") or {}).get("content") or ""
                    if piece:
                        if first is None:
                            first = time.perf_counter() - started
                        text += piece
                        if self.on_answer:
                            for raw in stream.feed(piece):
                                self.on_answer(raw)
        self.meter.add_usage(usage, first, time.perf_counter() - started)
        return schema_model.model_validate_json(text) if schema_model else text

    async def answer(self, system, user, schema_model):
        """The resolver swallows failed calls, so they are counted here or the row looks like a real run."""
        send = self._ollama if self.provider == "ollama" else self._fireworks
        try:
            return await send(system, user, schema_model)
        except (RuntimeError, httpx.HTTPError):
            self.meter.errors += 1
            raise

    async def _ollama(self, system, user, schema_model):
        payload = {"model": self.model, "stream": True, "think": False, "keep_alive": "30m",
                   **({"format": schema_model.model_json_schema()} if schema_model else {}),
                   "options": {"temperature": 0, "num_ctx": NUM_CTX},
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        stream, text = AnswerStream(), ""
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("POST", f"{OLLAMA}/api/chat", json=payload) as reply:
                reply.raise_for_status()
                async for line in reply.aiter_lines():
                    part = json.loads(line)
                    piece = (part.get("message") or {}).get("content") or ""
                    text += piece
                    if self.on_answer:
                        for raw in stream.feed(piece):
                            self.on_answer(raw)
                    if part.get("done"):
                        self.meter.add(part)
        return schema_model.model_validate_json(text) if schema_model else text


class LineQA(StreamQA):
    """Asks for one `N: answer` line per question. The model gives no confidence or topic this way."""

    async def answer(self, system, user, schema_model):
        if schema_model is resolver_module.motivation.MotivationAnswers:
            return await super().answer(system, user, schema_model)
        batch = CURRENT_BATCH.get()["batch"]
        rows = []
        for n, field in enumerate(batch, 1):
            options = f" | options: {' | '.join(field.options)}" if field.options else ""
            rows.append(f"{n}. [{field.type.value}] {field.label}{options}")
        asked = (user.split("Respond as JSON:")[0]
                 + "Reply with exactly one line per question, formatted `N: answer` and nothing else. For select, "
                 "copy one option verbatim. For multiselect, copy options verbatim separated by semicolons. Keep "
                 "free text to one short sentence.\n\n" + "\n".join(rows))
        text = await super().answer(
            system.replace("Respond with strict JSON only.", "Respond in the exact line format requested."),
            asked, None)
        answers = []
        for line in text.splitlines():
            match = re.match(r"\s*(\d+)\s*[:.]\s*(.*)$", line)
            if match and 0 < int(match[1]) <= len(batch):
                answers.append(resolver_module._LlmAnswer(key=batch[int(match[1]) - 1].key, answer=match[2].strip()))
        return resolver_module._LlmAnswers(answers=answers)


class GroupResolver(resolver_module.Resolver):
    """Asks the model in N groups at the same time, with the long "why us" call alongside them."""

    groups = 6
    motivation_call = None

    async def _write_motivation(self, schema, fields):
        self.motivation_call = asyncio.create_task(super()._write_motivation(schema, fields))
        return {}

    async def _ask_llm(self, schema, pending, offers=None):
        ask, size = super()._ask_llm, math.ceil(len(pending) / self.groups)

        async def one(batch):
            CURRENT_BATCH.set({"batch": batch, "seen": 0})
            return await ask(schema, batch, offers)

        parts = await asyncio.gather(*[one(pending[i:i + size]) for i in range(0, len(pending), size)])
        return {k: v for part in parts for k, v in part.items()}


class EagerResolver(resolver_module.Resolver):
    """Hands over each answer the moment it is known; the long "why us" call runs last."""

    on_ready = None
    deferred: list = []

    def _deterministic(self, field, *args, **kwargs):
        result = super()._deterministic(field, *args, **kwargs)
        if result is not None and self.on_ready:
            self.on_ready(result)
        return result

    async def _write_motivation(self, schema, fields):
        self.deferred = fields
        return {}

    parallel, chunk = 1, 4

    async def _ask_llm(self, schema, pending, offers=None):
        if self.parallel > 1 and len(pending) > self.chunk:
            gate = asyncio.Semaphore(self.parallel)

            async def one(batch):
                async with gate:
                    return await self._ask_llm(schema, batch, offers)

            parts = await asyncio.gather(*[one(pending[i:i + self.chunk])
                                           for i in range(0, len(pending), self.chunk)])
            return {k: v for part in parts for k, v in part.items()}
        CURRENT_BATCH.set({"batch": pending, "seen": 0})
        return await super()._ask_llm(schema, pending, offers)


# Fills plain HTML controls and reads each one back. Returns the keys it could not confirm.
WRITE_ALL = """(plan) => {
  const fire = (el) => { for (const name of ['input', 'change']) el.dispatchEvent(new Event(name, {bubbles: true}));
    el.dispatchEvent(new FocusEvent('blur')); el.dispatchEvent(new FocusEvent('focusout', {bubbles: true})); };
  const setValue = (el, value) => Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value').set.call(el, value);
  const missed = [];
  for (const [key, value] of plan) {
    const named = [...document.getElementsByName(key)];
    const els = named.length ? named : [document.getElementById(key)].filter(Boolean);
    const el = els[0];
    if (!el) { missed.push(key); continue; }
    if (el.type === 'checkbox' || el.type === 'radio') {
      const wanted = [].concat(value).map(String);
      let hits = 0;
      for (const box of els) {
        const on = wanted.includes(box.value) || wanted.includes((box.labels?.[0]?.textContent || '').trim());
        hits += on;
        if (box.checked !== on) { box.checked = on; fire(box); }
      }
      if (hits !== wanted.length) missed.push(key);
      continue;
    }
    if (el.tagName === 'SELECT') {
      const option = [...el.options].find(o => o.label.trim() === String(value) || o.value === String(value));
      if (!option) { missed.push(key); continue; }
      setValue(el, option.value);
      fire(el);
      if (el.value !== option.value) missed.push(key);
      continue;
    }
    setValue(el, String(value));
    fire(el);
    if (el.value !== String(value)) missed.push(key);
  }
  return missed;
}"""


class Fills:
    """One worker, because a page takes one fill at a time; answers queue up as they arrive."""

    def __init__(self, page, t0):
        self.page, self.filler, self.t0 = page, Filler(page), t0
        self.queue: asyncio.Queue = asyncio.Queue()
        self.at: dict[str, float] = {}
        self.ok: dict[str, bool] = {}
        self.values: dict[str, object] = {}
        self.write_s = 0.0
        self.fell_back = 0

    def put(self, result) -> None:
        if result.is_answered and self.values.get(result.key) != result.value:
            self.values[result.key] = result.value
            self.queue.put_nowait(result)

    async def write_all(self, results) -> None:
        """The whole form in one call. Anything it can't confirm goes through the filler, one at a time."""
        plan = [r for r in results if r.is_answered and r.type != FieldType.FILE]
        started = time.perf_counter()
        missed = set(await self.page.evaluate(WRITE_ALL, [[r.key, r.value] for r in plan]))
        self.write_s = time.perf_counter() - started
        done = time.perf_counter() - self.t0
        for r in plan:
            if r.key not in missed:
                self.values[r.key], self.ok[r.key], self.at[r.key] = r.value, True, done
        self.fell_back = len(missed)
        for r in results:
            self.put(r)

    async def run(self) -> None:
        while True:
            result = await self.queue.get()
            if result is None:
                return
            try:
                ok, _ = await self.filler._fill_one(result)
            except Exception:
                ok = False
            self.ok[result.key] = ok
            self.at[result.key] = time.perf_counter() - self.t0


async def scripted(page, args, meter, t0, *, eager: bool) -> tuple[dict, dict]:
    fields = await dom.extract_form_fields(page)
    schema = ApplicationSchema(ats=Ats.GREENHOUSE, job_url=page.url, company="Northwind Payments",
                               job_title="Senior Backend Engineer", location="San Francisco, California (Hybrid)",
                               posting_text=POSTING, fields=fields)
    by_key = {f.key: f for f in fields}
    fills = Fills(page, t0)
    worker = asyncio.create_task(fills.run())
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(_env_file=None, data_dir=tmp, embedding_model="",
                            llm_batch_size=0 if args.parallel > 1 or args.groups else args.batch)
        cache = AnswerCache(Path(tmp) / "cache.db")
        cls = GroupResolver if args.groups else EagerResolver if eager else resolver_module.Resolver
        qa = (LineQA if args.reply == "lines" else StreamQA)(args.model, meter, provider=args.provider)
        resolver = cls(settings, PROFILE, cache, qa)
        if args.groups:
            resolver.groups = args.groups
        if eager:
            resolver.on_ready = fills.put
            resolver.parallel, resolver.chunk = args.parallel, args.batch or 4

            def on_answer(raw: str) -> None:
                # The reply schema has one slot per question, in order, and a key with a default
                # can be left out, so position identifies the question.
                state = CURRENT_BATCH.get()
                index, state["seen"] = state["seen"], state["seen"] + 1
                data = json.loads(raw)
                data.setdefault("key", state["batch"][index].key if index < len(state["batch"]) else "")
                field = by_key.get(data["key"])
                if field is not None:
                    fills.put(resolver._from_llm(field, resolver_module._LlmAnswer.model_validate(data)))

            qa.on_answer = on_answer
        results = await resolver.resolve(schema)
        if eager and resolver.deferred:
            qa.on_answer = None
            written = await resolver_module.Resolver._write_motivation(resolver, schema, resolver.deferred)
            results = [written.get(r.key, r) for r in results]
        if args.groups and resolver.motivation_call:
            written = await resolver.motivation_call
            results = [written.get(r.key, r) for r in results]
        if args.writes == "all":
            await fills.write_all(results)
        for result in results:
            fills.put(result)
        cache.close()
    fills.queue.put_nowait(None)
    await worker
    return {r.key: r.value for r in results}, {"at": fills.at, "ok": fills.ok, "write_s": fills.write_s,
                                                "fell_back": fills.fell_back,
                                                "from_model": sum(r.source.value in ("llm", "generated") for r in results)}


TOOLS = [
    {"type": "function", "function": {"name": "read_form", "description": "Read the form's current HTML.",
                                      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "set_field", "description": "Set one form field by its name attribute. For a group of checkboxes, "
                                           "send every value to tick in one call, separated by semicolons.",
        "parameters": {"type": "object", "required": ["name", "value"],
                       "properties": {"name": {"type": "string"}, "value": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "finish", "description": "Call when every field is filled.",
                                      "parameters": {"type": "object", "properties": {}}}},
]
SET = """([name, value]) => { const els = [...document.getElementsByName(name)]; if (!els.length) return false;
  for (const el of els) { if (el.type === 'radio' || el.type === 'checkbox') {
    if (value.split(';').map(s => s.trim()).includes(el.value)) el.checked = true; } else el.value = value; }
  return true; }"""


async def toolloop(page, args, meter, t0) -> tuple[dict, dict]:
    """A generous stand-in for a general agent: three tools, a form-only view, thinking off."""
    system = ("You fill out job application forms for the applicant below. Use read_form, then set_field for "
              "every field, then finish. Never submit. Never invent facts.\n\n" + PROFILE.prompt_block())
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": f"Fill the form for Senior Backend Engineer at Northwind Payments.\n<posting>{POSTING[:2000]}</posting>"}]
    at: dict[str, float] = {}
    cloud = args.provider != "ollama"
    url = f"{FIREWORKS if args.provider == 'fireworks' else LLAMA}/chat/completions"
    headers = {"Authorization": f"Bearer {fireworks_key()}"} if args.provider == "fireworks" else {}
    extra = fireworks_options(args.model) if args.provider == "fireworks" else {}
    async with httpx.AsyncClient(timeout=600) as client:
        for _ in range(args.max_turns):
            if cloud:
                started = time.perf_counter()
                reply = await client.post(url, headers=headers, json={
                    "model": args.model, "temperature": 0, "max_tokens": 4096, **extra,
                    "tools": TOOLS, "messages": messages})
                if reply.status_code != 200:
                    raise RuntimeError(f"{args.provider} {reply.status_code}: {reply.content[:300]!r}")
                body = reply.json()
                meter.add_usage(body.get("usage") or {}, time.perf_counter() - started, time.perf_counter() - started)
                message = body["choices"][0]["message"]
            else:
                reply = await client.post(f"{OLLAMA}/api/chat", json={
                    "model": args.model, "stream": False, "think": False, "keep_alive": "30m", "tools": TOOLS,
                    "options": {"temperature": 0, "num_ctx": 32768}, "messages": messages})
                reply.raise_for_status()
                body = reply.json()
                meter.add(body)
                message = body["message"]
            messages.append(message)
            calls = message.get("tool_calls") or []
            if not calls:
                break
            finished = False
            for call in calls:
                name, params = call["function"]["name"], call["function"].get("arguments") or {}
                if isinstance(params, str):
                    params = json.loads(params or "{}")
                if name == "read_form":
                    out = await page.evaluate("() => document.querySelector('form').outerHTML")
                elif name == "set_field":
                    done = await page.evaluate(SET, [str(params.get("name")), str(params.get("value"))])
                    at.setdefault(str(params.get("name")), time.perf_counter() - t0)
                    out = "ok" if done else "no such field"
                else:
                    out, finished = "done", True
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": out} if cloud
                                else {"role": "tool", "tool_name": name, "content": out})
            if finished:
                break
    return {}, {"at": at, "ok": {k: True for k in at}, "from_model": len(at)}


# The eval's READ keeps one value per name, so a checkbox group reads as its last box, ticked or not.
READ_ALL = """() => { const o = {}; for (const el of document.querySelectorAll('input,select,textarea')) {
  if (el.type === 'checkbox') { (o[el.name] ||= []); if (el.checked) o[el.name].push(el.value); }
  else if (el.type === 'radio') { if (el.checked) o[el.name] = el.value; } else o[el.name] = el.value; }
  o.__submitted = !!window.__submitted; return JSON.stringify(o); }"""


async def trial(pw, url, args) -> dict:
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto(url)
    meter, t0 = Meter(), time.perf_counter()
    if args.mode == "toolloop":
        values, info = await toolloop(page, args, meter, t0)
    else:
        values, info = await scripted(page, args, meter, t0, eager=args.mode == "streamed")
    total = time.perf_counter() - t0
    page_values = json.loads(await page.evaluate(READ if args.form == "a" else READ_ALL))
    await browser.close()
    times = sorted(info["at"].values())
    row = {"mode": args.mode, "model": args.model, "provider": args.provider, "form": args.form, "batch": args.batch,
           "parallel": args.parallel, "groups": args.groups, "reply": args.reply, "writes": args.writes,
           "write_s": round(info.get("write_s", 0), 4), "fell_back": info.get("fell_back", 0), "total_s": round(total, 2),
           "first_fill_s": round(times[0], 2) if times else None,
           "half_filled_s": round(times[len(times) // 2], 2) if times else None,
           "fields_touched": len(times), "from_model": info["from_model"], "submitted": page_values.get("__submitted"),
           "failed": meter.errors > 0, **meter.row()}
    if args.form == "a":
        good = {k: bool(page_values.get(k) and check(str(page_values[k]))) for k, check in CHECKS.items()}
        row.update(correct=f"{sum(good.values())}/{len(good)}", wrong=[k for k, v in good.items() if not v])
    else:
        good = {c["id"]: score(c, page_values.get(c["id"])) for c in CASES}
        row.update(correct=f"{sum(good.values())}/{len(good)}", wrong=[k for k, v in good.items() if not v])
    return row


async def main_async(args) -> None:
    site = Path(tempfile.mkdtemp())
    (site / "form.html").write_text((ROOT / "evals/fallback/form.html").read_text())
    (site / "form_b.html").write_text(form_b_html())
    srv = serve(site)
    url = f"http://127.0.0.1:{srv.server_address[1]}/{'form.html' if args.form == 'a' else 'form_b.html'}"
    failed = False
    async with async_playwright() as pw:
        for n in range(args.trials):
            try:
                row = await trial(pw, url, args)
            except (RuntimeError, httpx.HTTPError) as error:  # the tool loop has no fallback, so the trial stops
                row = {"mode": args.mode, "model": args.model, "provider": args.provider, "form": args.form,
                       "failed": True, "error": str(error)[:300]}
            failed = failed or row["failed"]
            print(json.dumps({"trial": n + 1, **row}), flush=True)
    srv.shutdown()
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["toolloop", "batched", "streamed"])
    ap.add_argument("--model", default="qwen3.8:27b")
    ap.add_argument("--provider", default="ollama", choices=["ollama", "fireworks", "llama"])
    ap.add_argument("--parallel", type=int, default=1, help="batches sent at once (streamed mode only)")
    ap.add_argument("--form", default="a", choices=["a", "b"])
    ap.add_argument("--batch", type=int, default=0)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--groups", type=int, default=0, help="ask in this many groups at the same time (batched mode)")
    ap.add_argument("--reply", default="json", choices=["json", "lines"], help="lines needs --groups")
    ap.add_argument("--writes", default="each", choices=["each", "all"], help="all needs batched mode")
    parsed = ap.parse_args()
    if parsed.mode != "batched" and (parsed.groups or parsed.writes == "all"):
        ap.error("--groups and --writes all only work with --mode batched")
    if parsed.reply == "lines" and not parsed.groups:
        ap.error("--reply lines needs --groups")
    asyncio.run(main_async(parsed))
