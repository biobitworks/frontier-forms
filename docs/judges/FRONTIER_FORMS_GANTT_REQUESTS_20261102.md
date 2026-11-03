# Frontier Forms — teammate evidence requests

**Time boundary:** Monday, November 2, 2026, 4:30 PM PST build cutoff. Gantt snapshot at 3:46:01 PM PST is a historical capture, not a live clock.

> Team: I compiled a Gantt of every PR lane, the synthetic datasets, and local model runs. Please review your contributions and provide any missing PR, model digest, dataset manifest, screenshot or real field-level writeback evidence. Mark each item IMPLEMENTED, EXECUTED, OBSERVED, NEGATIVE, PROMOTED or NOT_TESTED. Include failures and unresolved cases. Please prioritize a reproducible demo and labeled judge figures before cutoff rather than starting a new training experiment. Publish approved synthetic JSON only; no real patient data, private model weights, credentials, or unapproved images.

| Lane | What we need |
|---|---|
| Teammates / Supabase | Actual 100-patient database readback/count or explicitly NOT_TESTED; don't confuse its source with the frozen Synthea v3.4.0 cohort |
| Claude forms | Original form and new additions, local model name/digest, labeled HTML/CSS / PDF / original-versus-annotated screenshots, exact source PR |
| Claude vision / red-team | YOLO full vs no-scan, Qwen VLM and Apple Vision results; show negative OCR-with-boxes result and note PR #51/#55 draft and hash-correction boundary |
| ChatGPT / independent | Local B0, D1/D2, logistic and RF negative/successor results, source hashes; open PR #22 100-patient loopback run remains unmerged |
| PI / scientific review | Approve or leave pending oracle rules in issue #32; independent replication is NOT_TESTED |
| Integration / security | Show exact CI SHA/status, historical policy exceptions and submission eligibility gaps |

**Important:** At frozen 3:46 PM snapshot, 33 PRs were merged, but **zero scientific model promotions** were supported in the 24 tracked training/ablation events.
