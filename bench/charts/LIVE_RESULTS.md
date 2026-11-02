# Live model benchmark results

Real Pi + browser-tools versus the same model with Frontier Forms tools. Updated whenever a local run finishes. Only matched cases enter comparison bars; unfinished and failed cases remain visible below.

![Runtime, accuracy and API cost by model](combined_benchmark.png)

[Download SVG](combined_benchmark.svg) · [Speed-only chart](model_speed.png)

| Model | Runs saved | Matched cases | Median Pi → tools | Correct fields Pi → tools | Mean estimated API cost Pi → tools | Failures Pi / tools |
|---|---:|---:|---|---|---|---|
| DeepSeek V4.1 Flash | 12/12 | 6/6 | 92.0 → 16.8 s | 119/121 → 119/121 | $0.0269 → $0.0054 | 0 / 0 |
| GLM 5.3 | 12/12 | 6/6 | 70.0 → 9.2 s | 118/121 → 115/121 | $0.1221 → $0.0142 | 0 / 0 |
| Qwen Max | 12/12 | 6/6 | 81.8 → 15.0 s | 116/121 → 121/121 | $0.1898 → $0.0299 | 0 / 0 |
| GPT-OSS 120B | 12/12 | 6/6 | 8.8 → 5.8 s | 19/121 → 114/121 | $0.0034 → $0.0021 | 0 / 0 |

## Conditions and limitations

Three form types × two synthetic patients × two arms per model. Same hosted model ID per comparison, temperature zero and low reasoning effort. Shuffled cases; the first portion used three concurrent jobs, then the queue was increased to twelve for the submission deadline. This concurrency change can affect measured latency and is not a controlled speed comparison across models. Within-model bars use the exact same matched cases.

Runtime is time until the agent stops, not proof of successful form completion. GPT-OSS stopped quickly but its Pi baseline scored only 19/121 fields; do not present that baseline as successful fast completion. GLM tooling scored 115/121 versus 118/121 for Pi, so its speed gain has a quality tradeoff. No held-out validation, repetitions, statistical confidence or clinical superiority is established. A partial result can change as more cases finish. If an arm fails or times out, its elapsed time must not be described as successful completion speed. Original DeepSeek [full pilot details](README.md) and [tooling explanation](TOOLING_WRITEUP.md).

[All sanitized run metrics](live_metrics.json) include completed single-arm cases before their counterpart finishes. Patient records, predictions, raw logs, failure messages and answer keys remain local. Receipt hashes identify the local artifacts.
