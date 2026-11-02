# Benchmark supervision status

Updated 2026-11-02. A 12-run development pilot is complete: real Pi `browser-tools` against our tools, same model and forms. It shows a large efficiency gap and no quality gap. It is dev data on one model, not a benchmark result, and no held-out pair has been run.

## Dev pilot (12 runs, 0 failed, 0 timed out, $0.19)

`deepseek-v4p1-flash`, 3 dev forms × 2 dev patients × 2 arms, 1 repeat, shuffled order, 3 at a time, one sandbox and one scorer. Raw rows and logs are local in `bench/results/pilot/`. Reproduce the table with `bench/.venv/bin/python bench/harness/pilot.py --summary`.

| Mean per form (n=6 each) | Pi + browser-tools | Our tools | Ratio |
|---|---|---|---|
| Time | 97.8 s | 17.3 s | 5.7× |
| Cost | $0.0269 | $0.0054 | 5.0× |
| Model calls | 16.0 | 3.0 | 5.3× |
| All tokens, including cached | 509,160 | 10,963 | 46× |
| Input + output, excluding cached | 59,798 | 7,591 | 7.9× |

| Quality (totals) | Pi + browser-tools | Our tools |
|---|---|---|
| Field accuracy, neutral | 119/121 | 119/121 |
| Field accuracy, closed world | 119/135 | 120/135 |
| Field accuracy, open world | 133/135 | 132/135 |
| Full forms, neutral | 4/6 | 4/6 |
| Wrong / fabricated / unsafe / submitted | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Unknowns held and flagged | 14/14 | 14/14 |
| Evidence valid | 98/100 | 98/100 |

| Mean time by form | Pi + browser-tools | Our tools |
|---|---|---|
| `primary_care_registration` | 71.7 s | 15.6 s |
| `urgent_care_history` | 98.0 s | 20.7 s |
| `insurance_update` | 123.7 s | 15.6 s |

Claims this supports: on these dev forms with this one model, our tools matched Pi's quality with about 5× less time and cost. Claims it does not support: better accuracy or safety, any result across models, any held-out or generalisation result, or improvement over time. Quality is tied, and open world slightly favours Pi by one field, because our tools answered one absent fact "No".

Limits on these numbers:
- n is 6 per arm with 1 repeat, so no confidence intervals are justified.
- All tokens counts Pi's repeated cached context, so show it only beside the uncached figure.
- `SYN-00015` was used to debug the tools, which fixed a retrieval bug before the pilot. `SYN-00037` was not. The patterns match on both.
- Our tools have not run on any held-out form. Their handling of held-out widgets is tested only on `packages/fill-tools/tests/widgets.html`.
- The author of the forms also wrote the tools, so held-out generalisation will be softer than a third-party test.
- Both arms' only 2 neutral misses are the same field: `referring_physician` on `primary_care_registration`. Gold maps it to the PCP, which is an assumption, so blank is defensible. It affects both arms equally and has not been changed.

Local run folders: `bench/results/pilot/` holds the 12 pilot rows only. `bench/results/dev-debug/` holds 15 earlier files, including the two pre-pilot Pi runs and the debug tool runs. Do not count those in the pilot. The two pre-pilot Pi runs used older scoring.

## Scoring decision: absent facts

Resolved in `bench/harness/score.py`. A yes/no question whose only basis for "no" is a missing record entry is now gold decision `absent`, covering conditions, allergies, medications, vaccines and family history: 74 dev and 676 held-out field instances. Each run is scored three ways: neutral (primary: "Yes" is wrong, "No" and blank are left out), closed world ("no" correct, blank missed), and open world (blank correct, "no" fabricated). Comparisons must show all three or name the one used. Evidence checks are also stricter: a cited fact must exist and be one the answer rests on. Refrozen before any held-out run; 280/280 oracle and blank pairs pass and `freeze.py --check` passes.

## Commit checkpoint

- Claude paused edits for Codex to commit and push the source.
- Codex independently ran `check_forms.py --patients 100`: 280 oracle pairs and 280 blank pairs, all interaction/negative probes passed, zero failures; leak scan clean. `freeze.py --check` passed.
- Saved Pi/browser-tools runs with `deepseek-v4p1-flash` for one dev patient: `insurance_update` 16/16 in 122.8 seconds (19 calls); `urgent_care_history` 17/23 in 89.7 seconds (13 calls). Neither failed or timed out; neither was marked unsafe or fabricated. These are two integration runs, not a model/harness comparison.
- Scoring limitation at that checkpoint: absent conditions became "No" in the gold and evidence validation was lenient. Both are now resolved, as described above.
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
- Spec 10.3 fill tools now exist as a pipeline in `packages/fill-tools`, uncommitted. An agent-mode Pi extension using them, form memory for over-time results, and the PDF and scan paths are not built.
- Epic: checked only the public API listing and search results. No usable blank questionnaire found. Sandbox probes were declined, so sandbox contents are unverified.
- `qwen3p8-27b` needs a dedicated Fireworks deployment and is not serverless.

## Next

Source edits are paused for Codex's snapshot. No more runs or tuning until Codex says it is safe.

Proposed held-out run, needing approval first: 6 models × 3 arms (Pi `browser-tools`, Pi `agent-browser`, our tools) × 8 held-out forms × 3 patients × 1 repeat = 432 runs. Dev pilot rates are only a floor, because held-out forms are longer and some models cost far more than DeepSeek. Estimate from the dev mean, on DeepSeek pricing: about $6 for Pi `browser-tools` and $1 for our tools across 144 runs each. Expect several times that across all six models; a one-repeat run of each model on one dev form should firm this up before approval.
