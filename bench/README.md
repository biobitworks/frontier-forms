# Harness benchmark (first local run)

Does a scripted harness fill forms faster and better than letting Qwen drive the form itself?

Measured 2026-11-02 on an Apple M1 Max with 64 GB, Ollama 0.40.10 and llama-server 0.4.1. Form-filling times are from warm runs. These are pilot numbers: job application forms and a fictional applicant, not medical forms and not Fireworks. Don't quote them as Frontier Forms results (spec section 2).

## Setup

- **Scripts:** the scripts call the Job Applicator engine at `/Users/reuben/github/hobby/Job-Applicator` (field extraction, resolver, filler) and need that repo's `.venv`.
- **12-field form:** `evals/fallback/form.html`.
- **65-question form:** generated from `evals/answers/cases.yaml`.
- **Tool loop:** a generous stand-in for a general agent, with three tools, a form-only view and thinking off. Pi itself was not installed or tested.
- **Speedups:** `bench.py --mode batched --groups 6 --reply lines --writes all` turns on all three. Each option also works alone, except that `--reply lines` needs `--groups`.

Rerun everything with `zsh bench/run_all.sh`, then `zsh bench/run_llama.sh`. Raw output is in `results.jsonl` and `results_llama.jsonl`.

## qwen3.8:27b

| Form | Harness | First field | All done | Correct | Model calls | Prompt tokens |
|---|---|---|---|---|---|---|
| 12 fields | browser-use agent | not recorded | timed out at 420 s | 11/12 on the page | not recorded | not recorded |
| 12 fields | tool loop | 23.7 s | 25.1 s | 11/12 | 3 | 5,536 |
| 12 fields | scripts, one fill at the end | 7.8 s | 8.3 s | 12/12 | 2 | 2,529 |
| 12 fields | scripts, fill as answers arrive | 0.1 s | 7.7 s | 12/12 | 2 | 2,529 |
| 65 questions | tool loop (one trial) | 143.9 s | 196.8 s | 60/65 | 5 | 32,832 |
| 65 questions | scripts, batches of 4 | 213–221 s | 217–225 s | 63/65 | 16 | 22,504 |
| 65 questions | scripts, batches of 4, streamed | 0.1 s | 216–224 s | 63/65 | 16 | 22,504 |
| 65 questions | scripts, one big call, streamed | 0.1 s | 84–109 s | 58/65 | 2 | 4,682 |

On the 12-field form, scripts answered 9 of the 12 fields with no model call. The browser-use run used the model's default thinking setting; the others had thinking off.

## Prompt caching and parallel requests

| Test | Result |
|---|---|
| Ollama, identical request | 0.15 s of prompt time |
| Ollama, same prompt start with new questions (1,438 tokens) | 13.57 s of prompt time, so no reuse |
| Ollama, parallel requests | Refused: "model architecture does not currently support parallel requests" (`qwen35`) |
| 16 batches, Ollama, one at a time | 237 s in total, about 28 output tokens/s |
| 16 batches, llama-server, 1 slot | 300 s in total: prompt 64 s, output 236 s |
| 16 batches, llama-server, 3 slots | 297 s in total, so no gain on this Mac |

llama-server does reuse the prompt start, but its output took about 2.8 times as long as Ollama's. The cause was not investigated.

## Tiny model: qwen3.5:0.8b

| Test | Time | Correct |
|---|---|---|
| 12 fields, scripts | 3.0 s | 11/12 |
| 12 fields, tool loop | 5–7 s | 8/12, and 2 fields never filled |
| 65 questions, scripts, batches of 4 | 28 s | 27/65 |
| 65 questions, one question per call, only the 6 most relevant profile lines | 18 s | 35/65 |
| 65 questions, the same with 10 lines | 16 s | 33/65 |

## Other local Qwen models (Ollama)

One 65-question trial per setup. `results_qwen_local.jsonl` has the raw output.

| Model | 12 fields, scripts | 12 fields, tool loop | 65 questions, batches of 4 | 65 questions, one big call |
|---|---|---|---|---|
| qwen3.6:35b-a3b | 3.4 s, 12/12 | 14.9 s, 11/12 | 59.1 s, 63/65 | 40.9 s, 62/65 |
| qwen3.5:4B | 3.1 s, 12/12 | 13.6 s, 11/12 | 65.6 s, 57/65 | 30.3 s, 60/65 |

## Fireworks serverless

`accounts/fireworks/models/qwen3p8-27b` needs a dedicated deployment, so these runs use two other models. They are not Qwen3.8-27B results. Thinking is off. `bench/run_fireworks.sh` reruns them, and raw output is in `results_fireworks.jsonl`.

| Form | Harness | `qwen3p8-max` time | Correct | `qwen3p8-2p4t-a95b` time | Correct |
|---|---|---|---|---|---|
| 12 fields | tool loop | 7.6–11.9 s | 11/12 | 6.6–11.3 s | 11/12 |
| 12 fields | scripts, streamed | 1.5–1.8 s | 12/12 | 2.6–6.6 s | 12/12 |
| 65 questions | tool loop | 25.5–28.0 s | 61/65 | 27.8–30.4 s | 61/65 |
| 65 questions | streamed, batches of 4, one at a time | 23.4–30.8 s | 63/65 | 33.7–39.0 s | 63/65 |
| 65 questions | streamed, 4 batches at once | 10.1–11.6 s | 63–64/65 | 10.7–11.1 s | 63/65 |
| 65 questions | streamed, 8 batches at once | 5.8–8.5 s | 64/65 | 8.2–8.3 s | 63/65 |
| 65 questions | streamed, one big call | 13.2–14.0 s | 64/65 | 15.6–17.3 s | 64/65 |

After the first request, almost all of the 22,504 prompt tokens were cached (22,488).

### GLM 5.3

GLM 5.3 refuses `reasoning_effort: none`, so these runs use `low` with a 16,000 token limit. Two trials per setup. Raw output is in `results_glm.jsonl`, and `run_fireworks.sh` includes all three models.

| Form | Harness | `glm-5p3` | Correct | `glm-5p3-flash` | Correct | `glm-5p3-fast` | Correct |
|---|---|---|---|---|---|---|---|
| 12 fields | tool loop | 4.6–4.8 s | 11/12 | 3.4–22.2 s | 11/12 | 1.9–2.5 s | 11/12 |
| 12 fields | scripts, streamed | 3.0–3.8 s | 12/12 | 2.0–3.0 s | 12/12 | 1.0–1.4 s | 12/12 |
| 65 questions | tool loop | 16.6–20.6 s | 60–61/65 | 7.8–8.5 s | 60/65 | 5.8–6.2 s | 59/65 |
| 65 questions | streamed, 8 batches at once | 7.8–8.5 s | 64/65 | 11.5–16.1 s | 62/65 | 3.7–3.8 s | 64/65 |
| 65 questions | streamed, one big call | 13.9–16.8 s | 62–63/65 | 9.5 s | 63/65 | 5.0–5.8 s | 63/65 |

Tool loop scores in this table and the tables above are too low: see the scoring fix below.

### Each speedup alone, then together

Five trials per setup, median time, on plain HTML forms. `bench/run_ablation.sh` reruns them, and raw output is in `results_ablation.jsonl`. Six groups means the questions go out in 6 calls at the same time, with the long "why us" call alongside them. One write means one `page.evaluate` that fills the form and reads each control back. Anything it can't confirm goes through the engine's filler; no field needed that here.

| 65 questions | `glm-5p3-fast` | Correct | `glm-5p3-flash` | Correct | `minimax-m3p1-flash` | Correct |
|---|---|---|---|---|---|---|
| Tool loop | 6.08 s | 61–63/65 | 8.98 s | 64/65 | 16.43 s | 63–64/65 |
| Six groups, JSON, field by field | 5.41 s | 62–63/65 | 6.84 s | 62/65 | 6.34 s | 63/65 |
| Six groups, lines, field by field | 5.58 s | 62/65 | 5.78 s | 63–64/65 | 5.56 s | 64/65 |
| Six groups, JSON, one write | 2.49 s | 62–63/65 | 4.20 s | 62–63/65 | 3.00 s | 63/65 |
| Six groups, lines, one write | 1.99 s | 62/65 | 3.29 s | 63–64/65 | 2.06 s | 64/65 |

| 12 fields | `glm-5p3-fast` | Correct | `glm-5p3-flash` | Correct | `minimax-m3p1-flash` | Correct |
|---|---|---|---|---|---|---|
| Tool loop | 2.26 s | 11/12 | 3.80 s | 11/12 | 5.13 s | 11/12 |
| Six groups, lines, one write | 0.73 s | 12/12 | 1.60 s | 12/12 | 1.35 s | 12/12 |

Lines cut output from about 1,700 tokens to about 670, but they save little until the field-by-field writes are gone, because those take about 3.6 s on their own. The worst single times were 45.26 s for the MiniMax tool loop and 4.91 s for MiniMax with both speedups.

Line replies carry no confidence or evidence, so every answer gets the engine's default confidence. One write sets values directly and has not been tried on custom widgets, where a value can read back correctly without the app accepting it.

### Scoring fix for the tool loop

Two bench faults made the tool loop look less accurate than it is, so don't compare its older scores with anything. The page reader kept only the last box in each checkbox group, ticked or not, and `set_field` never said how to send several choices. Both are fixed, and form b is now always scored from the page rather than from the planned answers. `results_ablation.jsonl` has the fixed scoring; `results.jsonl`, `results_fireworks.jsonl` and `results_glm.jsonl` do not. Scripted rows in those files were scored from planned answers.

### Failed runs

The resolver swallows failed model calls, so a run can finish with a believable row and no answers from the model. Rows now carry `failed` and `failed_calls`, and `bench.py` exits with 1 if any trial failed. Don't use a row with `failed: true`. Only `results_ablation.jsonl` has these fields; the older result files predate them.

## Liquid LFM (llama-server, local)

`bench/run_lfm.sh` takes `repo:file` pairs. Raw output is in `results_lfm.jsonl`.

| Model | File | 12 fields, tool loop | 12 fields, scripts | 65 questions, batches of 4 | One question per call | Only 6 relevant facts |
|---|---|---|---|---|---|---|
| LFM2.5-350M | 0.21 GB | 0/12 | 11/12, 0.7 s | 23/65, 6 s | 30/65, 10 s | 32/65, 6.5 s |
| LFM2.5-1.2B-Instruct | 0.68 GB | 0/12 | 9/12, 1 s | 29/65, 11 s | 35/65, 18.5 s | 38/65, 10.8 s |
| LFM2.5-2.6B | 1.56 GB | 10/12, 22–23 s | 12/12, 41–61 s | 57/65, 325–368 s | not run | not run |

LFM2.5-2.6B produced 25,702 output tokens on the long form, most of it hidden reasoning. Starting the server with `--reasoning off` gave the same token count and score, so reasoning was never actually turned off.

Not tested: LFM3-1.7B failed to load in llama-server 0.4.1. LFM2.5-8B-A1B and LFM2.5-24B-A2B were stopped mid-download. Liquid's extraction-focused models were not tried.

## Not covered

- Qwen3.8-27B on Fireworks.
- Medical forms, abstention on missing data, and the before-and-after fine-tuning study. The engine's prompt asks for a best guess, and `tiny.py` treats a missing fact as No. Both must change for medical forms.
- Real ATS pages, CAPTCHAs and paced input. The test forms are plain HTML.
- Fill-as-answers-arrive against conditional fields and consent rules. It exists only in `bench.py`, not in the engine.
