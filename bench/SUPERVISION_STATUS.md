# Benchmark supervision status

Updated 2026-11-02. Two medical development-form integration runs are saved locally. No comparative benchmark or demonstrated improvement exists yet.

## Commit checkpoint

- Claude paused edits for Codex to commit and push the source.
- Codex independently ran `check_forms.py --patients 100`: 280 oracle pairs and 280 blank pairs, all interaction/negative probes passed, zero failures; leak scan clean. `freeze.py --check` passed.
- Saved Pi/browser-tools runs with `deepseek-v4p1-flash` for one dev patient: `insurance_update` 16/16 in 122.8 seconds (19 calls); `urgent_care_history` 17/23 in 89.7 seconds (13 calls). Neither failed or timed out; neither was marked unsafe or fabricated. These are two integration runs, not a model/harness comparison.
- Scoring limitation: absent problem-list conditions currently become "No" in the gold. Pi left six such urgent-care answers blank. That closed-world assumption remains unresolved and must be decided before comparative claims. Evidence validation for demographic fields is also lenient.
- Source definitions and gold-generating code are public; actual patient exports, derived gold, freeze manifests, rendered fixtures and raw logs stay local and are ignored by Git. Log paths below refer to local artifacts, not published receipts.

## Real Pi versus the older pilot

- **Real Pi:** only the smoke runs below. Pi 1.5.0 (`@earendil-works/pi-coding-agent`), pinned in `bench/pi/package.json`.
- **Simplified tool loop:** every `toolloop` row in `bench/results*.jsonl` and `bench/README.md`. It is a stand-in, not Pi. Those rows are job forms, some predate failure tracking, and older scores have known bugs. Do not compare them with anything below.

## Pi skill smoke tests

One 4-field form, `deepseek-v4p1-flash`, sandboxed. These show the skills run. They say nothing about relative quality.

| Skill | Filled correctly | Time | Cost | Log |
|---|---|---|---|---|
| `browser-tools` (Pi author's skill) | 4/4 | 20 s | $0.005 | `bench/logs/smoke/browser-tools.deepseek-v4p1-flash.jsonl` |
| `pi-agent-browser-native` 0.7.1 | 4/4 | 32 s | $0.011 | `bench/logs/smoke/agent-browser.deepseek-v4p1-flash.jsonl` |
| `pi-computer-use` 0.5.1 | 4/4 | 75 s | $0.031 | `bench/logs/smoke/computer-use.deepseek-v4p1-flash.jsonl` |

Failed attempts, all caused by setup and not by the skills: `--ignore-scripts` left the agent-browser binary non-executable and its launcher unpatched, `--no-session` disabled its code tool, the sandbox blocked setuid `/bin/ps`, and computer-use needed its macOS helper. Those logs were overwritten by the reruns.

## Baseline adapters to disclose

- Pi has no first-party browser or computer-use tool. All three are packages.
- `browser-tools`: port made configurable, and a private headless Chromium replaces its visible Chrome launch.
- `pi-computer-use`: runs through its CDP browser path with the desktop backend turned off (`bench/pi/skills/computer-use-cdp/index.ts`) and `launch_browser` excluded. It does not drive the desktop or take pixel-only actions. Desktop mode needs macOS Accessibility and Screen Recording grants, which only Reuben can give.
- Containment (`bench/pi/sandbox.py`): only the Fireworks key is passed, a throwaway HOME is used, and reads of `.env`, credentials and gold are denied.

## Blockers

- An auto-mode check blocked one unsandboxed run. The sandboxed version has been allowed since.
- `frontier-forms` has no spec 10.3 fill tools yet, so "our tools" cannot be benchmarked on medical forms until they exist.
- Epic: checked only the public API listing and search results. No usable blank questionnaire found. Sandbox probes were declined, so sandbox contents are unverified.
- `qwen3p8-27b` needs a dedicated Fireworks deployment and is not serverless.

## Next

Smallest comparative medical pilot, run on dev data only: 2 dev forms (`primary_care_registration`, and multistep `insurance_update` or conditional `urgent_care_history`), 2 dev patients, 1 model, real Pi `browser-tools` versus our tools once built. Scoring reads what the form would submit, with the same code for every arm, and counts failures, evidence and unknowns. Pilot results, run count and estimated cost get reported here before any full run.
