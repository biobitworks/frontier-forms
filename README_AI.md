# README for AI agents (Claude, Codex, ChatGPT, local assistants)

You are working in an append-only evidence repository. Read this before touching anything.

## Non-negotiable vocabulary
PROPOSED ≠ IMPLEMENTED ≠ EXECUTED ≠ OBSERVED ≠ SUPPORTED. Preserve NEGATIVE, NULL, FAILED, NOT_TESTED, NOT_COMPUTED,
BLOCKED and NOT_OBSERVED exactly as written. Never invent a root, hash, execution outcome, registration ID or statistic.
A Merkle root proves byte identity; it never proves causality, clinical truth or model competence.

## Lanes and what they may claim
| Lane | Branch | May claim |
|---|---|---|
| Predecessor evidence lab | `feat/fcg-ehr-evidence-lab-20261102` (PR #3, head `da953450`) | INTEGRITY_ONLY + DISCOVERY_NEGATIVE |
| Claude red-team | `redteam/claude-fcg-local-ablation-20261102` (this branch) | what `docs/reviews/CLAUDE_REDTEAM_REPORT.md` says, nothing more |
| Team app/ingestion | `main` (PR #4) | operational Supabase schema; no frozen benchmark |

## Before you change anything
1. `python3 scripts/verify_predecessor.py --bundle evidence/freeze/predecessor` must print `root_recomputed: PASS`.
2. `python3 scripts/verify_review_export.py` must verify three roots from pinned Git commits (never from the working tree).
3. `python3 scripts/redteam/freeze_redteam_successor.py --verify evidence/breakpoints/REDTEAM-<root16>` for the red-team successor.
4. `python3 -m unittest discover -s tests -v` must pass.
Do not edit anything under `evidence/freeze/`, `evidence/breakpoints/`, `evidence/notebook_runs_*`, `evidence/redteam/` or
`evidence/receipts/`. Corrections are new files with a `parent`/`predecessor` field.

## Reproduce the red-team lane
* Container-only (no model inference): `python3 scripts/redteam/execute_redteam_notebooks.py` creates a NEW `evidence/notebook_runs_redteam_v<N>`.
* On magicSTUDIObox with the private evidence directory (never copied here):
  `python3 scripts/redteam/redteam_verify_sources.py --source <evidence dir> --pairs evidence/stats/discovery_pair_flags.jsonl --out <receipt>` and
  `python3 scripts/redteam/redteam_local_lanes.py --source <evidence dir> --model <ollama model> --split heldout --out-dir <dir> --tag <tag>`.
  Only `*_PUBLIC.jsonl` and `*_META.json` may be committed. `*_LOCAL.jsonl` contains gold answers and stays on the host.
* Rebuild the attribution matrix: `python3 scripts/redteam/build_attribution_matrix.py`.

## Local JSON databases (read these first; no credentials needed)
* `evidence/redteam/db/models.json` — every checkpoint actually run, with its Ollama manifest digest / safetensors sha256 and the lanes it appeared in. Blocked models are listed with the reason.
* `evidence/redteam/db/field_answers.jsonl` — one row per synthetic form image: for each of the 7 fields the printed value, the source value, whether an error was planted, and every model's actual answer (Apple Vision OCR, qwen2.5vl extraction + reread, OCR→Qwen mappers, Qwen2.5-VL grounding with bbox and IoU) plus validation verdicts.
* `evidence/redteam/db/ledger.jsonl` and `evidence/redteam/attribution_matrix.json` — the attribution ledger. Each record separates **weights** (name + digest), **mechanism** (enabled/disabled FCG or antigentic mechanisms) and **outcome** (measured delta with McNemar/Holm/bootstrap and a claim status). `mechanism.changed = WEIGHTS_ONLY` rows are model comparisons; `MECHANISM_ONLY` rows are harness ablations.
* `evidence/redteam/gate_factorial.json` + `docs/architecture/gate_factorial_heatmap.{svg,html}` — the 16-combination heat map on SYNFORM2-ERR.

## Things that look like results but are not
* Discovery-split numbers (n=38) are hypothesis-generating. Only heldout rows (n=39) can pass the admission rule, and only with
  Holm-corrected McNemar PASS, bootstrap lower CI > 0, replication PASS and guardrails PASS.
* `antigence_swap` coverage/false-admission figures are selective-prediction metrics, not accuracy gains.
* `admitted_injected` on a 2-option task is the wrong letter; use `injection.excess_injected_rate` and `flip_correct_to_injected`.
* Fireworks L4/L5, NVIDIA training, Snyk, live Supabase and Epic are BLOCKED or NOT_TESTED in this lane. Do not upgrade them.

## Secrets and rights
No credentials in code, chat, shell history or receipts. LongevityBench is CC BY-NC 4.0 and the Insilico checkpoint is CC BY-ND 4.0:
nothing from either leaves magicSTUDIObox except hashes and booleans. Synthea forms are synthetic; still, oracle values are not exported.
