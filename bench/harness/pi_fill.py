"""One real Pi run on one form for one patient, scored from what the form would submit.

    pi_fill.py --form insurance_update --patient SYN-00012 [--model deepseek-v4p1-flash] [--skill browser-tools]

Dev forms pair with dev patients only. Running a held-out pair needs --heldout, which is for the frozen final run.
"""
from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
sys.path.insert(0, str(BENCH / "pi"))

import forms as form_lib  # noqa: E402
import passports as pp  # noqa: E402
import sandbox  # noqa: E402
import score as scorer  # noqa: E402
import serve  # noqa: E402
from check_forms import CHROME  # noqa: E402

TASK = """Fill out the web form at {url} for the synthetic patient whose record is ./passport.json.

Rules:
- Use only what the record supports. Do not guess.
- If the record has no answer, or the fact is missing, conflicted or expired, leave the field blank and list it under needs_review.
- For current medications, list only active ones, not past ones.
- Never sign or attest. Never fill staff-only or office-use fields.
- Never press Submit. If the form has several steps, use Next to reach each one.

When you have finished, write ./report.json:
{{"answers": [{{"label": "<field label>", "value": "<what you entered>", "evidence_fact_ids": ["<fact id, or a path such as demographics.given_name>"]}}],
 "needs_review": [{{"label": "<field label>", "reason": "<why>"}}]}}
Then reply DONE."""

SKILLS = {
    "browser-tools": (lambda port: {"BROWSER_TOOLS_PORT": str(port)},
                      lambda: ["--skill", str(BENCH / "pi/skills/browser-tools"), "-ne"],
                      "Use the browser-tools skill. Chrome is already running on port {port} with the form open."),
    "agent-browser": (lambda port: {},
                      lambda: ["-e", str(BENCH / "pi/node_modules/pi-agent-browser-native/dist/extensions/agent-browser/index.js"), "-ns", "--exclude-tools", "bash"],
                      'Use the agent_browser tool. First connect to the running browser with args ["connect","{port}"]. The form tab is already open.'),
    "computer-use": (lambda port: {"PI_COMPUTER_USE_CDP_PORT": str(port), "PI_COMPUTER_USE_HEADLESS": "1", "PI_COMPUTER_USE_CURSOR_OVERLAY": "0"},
                     lambda: ["-e", str(BENCH / "pi/skills/computer-use-cdp/index.ts"), "-ns", "--exclude-tools", "bash,launch_browser"],
                     "Use the computer-use tools. The form is already open in a browser page, and find_roots lists it."),
}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def usage_of(log: Path) -> dict:
    total = {"model_calls": 0, "input": 0, "cached": 0, "output": 0, "cost_usd": 0.0, "tool_calls": 0, "last_stop": None, "error": None}
    for line in log.read_text().splitlines():
        if not line.startswith("{"):
            continue
        event = json.loads(line)
        message = event.get("message") or {}
        if event.get("type") != "message_end" or message.get("role") != "assistant":
            continue
        usage = message.get("usage") or {}
        total["model_calls"] += 1
        total["input"] += usage.get("input", 0)
        total["cached"] += usage.get("cacheRead", 0)
        total["output"] += usage.get("output", 0)
        total["cost_usd"] += (usage.get("cost") or {}).get("total", 0) if isinstance(usage.get("cost"), dict) else 0
        total["tool_calls"] += sum(c.get("type") == "toolCall" for c in message.get("content", []))
        total["last_stop"], total["error"] = message.get("stopReason"), message.get("errorMessage")
    return total


def run(args) -> dict:
    form = form_lib.all_forms()[args.form]
    parts = pp.splits()
    if args.patient not in parts[form.split]:
        raise SystemExit(f"{args.patient} is not a {form.split} patient, and pairs cross no split.")
    if form.split == "test" and not args.heldout:
        raise SystemExit("Held-out pair. It stays unused until the frozen final run.")
    p = pp.load()[args.patient]
    schema = json.loads((HERE / f"data/templates/{form.name}.json").read_text())

    server = serve.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/{form.name}/"
    cdp = free_port()
    profile = tempfile.mkdtemp(dir="/private/tmp")
    chrome = subprocess.Popen([str(CHROME), "--headless=new", f"--remote-debugging-port={cdp}", f"--user-data-dir={profile}", "--no-first-run",
                               "--no-default-browser-check", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{cdp}/json/version", timeout=1)
            break
        except OSError:
            time.sleep(.1)

    run_dir = Path(tempfile.mkdtemp(dir="/private/tmp"))
    (run_dir / "passport.json").write_text((HERE / f"data/passports/{args.patient}.json").read_text())
    agent = run_dir / ".agent"
    agent.mkdir()
    shutil.copy(BENCH / "pi/models.template.json", agent / "models.json")
    env, flags, hint = SKILLS[args.skill]
    out_dir = BENCH / "results/pilot"
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{args.skill}.{args.model}.{form.name}.{args.patient}"
    log, err = run_dir / "pi.jsonl", run_dir / "pi.err"  # results/ is off limits to the sandbox, so logs move there afterwards
    started = time.time()
    with log.open("w") as o, err.open("w") as e:
        code, timed_out = sandbox.run_pi(["--mode", "json", "--session-dir", str(run_dir / ".sessions"), "-nc", "--thinking", "low", "--provider", "fireworks",
                                          "--model", f"accounts/fireworks/models/{args.model}", *flags(), hint.format(port=cdp) + "\n\n" + TASK.format(url=url)],
                                         run_dir, agent, timeout=args.timeout, extra_env=env(cdp), stdout=o, stderr=e)
    elapsed = time.time() - started
    with sync_playwright() as pw:  # scored from the live page the agent left behind
        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp}")
        page = next(t for c in browser.contexts for t in c.pages if form.name in t.url)
        read = page.evaluate("() => window.__ffRead()")
        browser.close()
    chrome.kill()
    server.shutdown()
    report_path = run_dir / "report.json"
    try:
        report = json.loads(report_path.read_text())
    except (OSError, ValueError):
        report = None
    result = scorer.score(form, p, read)
    usage = usage_of(log)
    stderr = err.read_text()
    log, err = Path(shutil.move(log, out_dir / f"{tag}.jsonl")), Path(shutil.move(err, out_dir / f"{tag}.err"))
    # A run that never reached the model is a harness failure. It must never read as a low score.
    failed = (code != 0 and not timed_out) or usage["model_calls"] == 0
    row = {"arm": f"pi+{args.skill}", "pi_version": "1.5.0", "model": args.model, "form": form.name, "patient": args.patient, "split": form.split,
           "failed": failed, "failure": stderr[-400:] if failed else None, "exit_code": code, "timed_out": timed_out, "seconds": round(elapsed, 1),
           **usage, **result, **scorer.score_report(form, p, result, report, schema), "agent_report": report, "log": str(log.relative_to(BENCH))}
    (out_dir / f"{tag}.json").write_text(json.dumps(row, indent=1))
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--form", required=True)
    ap.add_argument("--patient", required=True)
    ap.add_argument("--model", default="deepseek-v4p1-flash")
    ap.add_argument("--skill", default="browser-tools", choices=sorted(SKILLS))
    ap.add_argument("--timeout", type=float, default=300)
    ap.add_argument("--heldout", action="store_true")
    row = run(ap.parse_args())
    if row["failed"]:
        raise SystemExit(f"FAILED RUN, not a result: exit {row['exit_code']}, {row['failure']}")
    show = {k: v for k, v in row.items() if k not in ("rows", "agent_report")}
    print(json.dumps(show, indent=1))
    for r in row["rows"]:
        if r["outcome"] not in ("correct", "skipped"):
            print(f'  {r["outcome"]:10} {r["fid"]:30} got={r["value"][:50]!r} expected={r["decision"]} {r["expect"][:60]}')


if __name__ == "__main__":
    main()
