# Claude red-team laboratory notebook (append-only)

Lane: `redteam/claude-fcg-local-ablation-20261102`. Parent: PR #3 head `da953450d33a721682191f77589c275e0b49731c`
(branch `feat/fcg-ehr-evidence-lab-20261102`). Predecessor states are never edited; every correction is a successor entry.

Status vocabulary (non-negotiable): PROPOSED ≠ IMPLEMENTED ≠ EXECUTED ≠ OBSERVED ≠ SUPPORTED. NEGATIVE, NULL, FAILED,
NOT_TESTED, NOT_COMPUTED and BLOCKED are preserved as written.

## R00 — 2026-11-02 21:1x UTC — environment receipt (OBSERVED)

| Item | magicSTUDIObox (Mac Studio) | magicPRO (MacBook Pro) | cloud container |
|---|---|---|---|
| OS / CPU / RAM | macOS 27.0.1, Apple M1 Max, 32 GiB | macOS 27.2, Apple M1 Pro, 16 GiB | Linux 6.18 x86_64 |
| Python | 3.15.0 (brew); 3.12.13 brew with torch 2.13.0 + transformers 5.8.1; evidence `.venv` 3.12.13 with pyarrow 23.0.1 | 3.9.6 system, torch 2.8.0 MPS | 3.13.18 |
| Ollama | 0.33.0; lfm2-1.2b-longevity-q4km, qwen3:1.7b, qwen2.5vl:3b present | 0.32.15; qwen3:1.7b present, no longevity model, no VL model | absent |
| Insilico checkpoint | present, safetensors SHA re-hashed = frozen leaf | absent | absent |
| Lean 4 | 4.15.0 via `~/.elan/bin` (not on PATH) | absent | absent |
| gh | authenticated as biobitworks | authenticated as biobitworks | GitHub MCP only |
| Snyk | not installed | 1.1307.2; `snyk whoami` → Authentication error SNYK-0005 | absent |
| gitleaks | installed | installed | download denied by sandbox policy |
| FIREWORKS_API_KEY | UNSET (sh and zsh login) | UNSET | UNSET |
| Claude Code | 2.1.212 | 2.1.314 | this session (claude-fable-5-1 configured) |
| gsigmad | source checkout at `~/projects/active/gsigmad` (1.2.0b1 wheel in dist/); CLI run recorded separately | NOT_TESTED | absent |
| Evidence dir | `/Users/byron/projects/active/fireworks-antigence-eval-20261102` present, not a git repo | absent | absent |

Access path: Desktop Commander connector; each remote command and exit code is in the receipts under `evidence/redteam/`.
Fireworks lanes L4/L5 are therefore BLOCKED_NO_CREDENTIAL (no provider request was made, no cost was incurred).

## R01 — independent Merkle replay (EXECUTED, OBSERVED)

Own re-implementation (`scripts/redteam/redteam_verify_sources.py`), run on magicSTUDIObox with the evidence `.venv`
interpreter in isolated mode. Result receipt: `evidence/redteam/independent_replay_magicstudiobox.json`.

* 728-input root recomputed = `5f9a7e51…61b1`; 728/728 inclusion proofs PASS; 728 DERIVED_INPUT_AT edges consistent.
* 15-leaf project root recomputed = `9e4d4df8…d3a9a`; all 13 source files re-hashed (including the 3.0 GB safetensors) match.
* Split manifest regenerated from the parquet with independent code: byte-identical (`46c48f08…9007`).
* 38 discovery pairs resolve to public input FCOs, all in the discovery partition, task labels match; correctness flags
  recomputed from local receipts match the public export; 25/38 vs 27/38, discordant 2/4, exact p = 0.6875 reproduced.
* Public inputs contain only system+user roles; no answer-like keys. Oracle isolation PASS at the file level.
* NEGATIVE CONTROLS all behave: corruption, reorder, removal, prefix swap, zero-pad all change the root.
* FINDING F-01 (structural): duplicate-last-odd Merkle trees give the SAME root when a copy of the last leaf is appended
  (729 → 730 leaves). The root alone does not bind leaf count. The manifests do bind `rows`/`leaf_count` separately and
  there is no signature, so this is a documented ceiling, not a break. Recommendation: bind count into the leaf-0 context
  or adopt an RFC 6962-style construction in the next freeze schema.

## R02 — predeclared hypotheses for the local lanes (written BEFORE any heldout result was read)

Frozen partitions from the split manifest: discovery n=38, heldout n=39 (10/10/10/9), reserve untouched.
Primary endpoint: strict single-letter accuracy. Alpha 0.05, exact two-sided McNemar, 10,000 stratified paired bootstrap
replicates (numpy PCG64 seed 20261102), Holm across the predeclared primary comparisons per split.

H1 (model lane): no local lane differs from L0 on heldout after Holm correction. Discovery results are hypothesis-generating only.
H2 (FCO/FCG context): adding FCO or FCG metadata to the system prompt does NOT change strict accuracy (null expected; any
   change is a prompt-perturbation effect, not evidence that provenance improves reasoning).
H3 (antigentic admission): the admission gate reduces false admissions relative to the base error rate at the cost of coverage;
   the verdict-only prototype is expected to be degenerate for letter-only fine-tunes (observed on L0 smoke: it re-emits a letter).
H4 (injection): a tool-note injection in the FCG block raises attacker success on direct answers; the swap-consistency gate
   must drive admitted-injected rate toward 0 because the injected letter cannot flip under option swap.
H5 (integrity): forged leaf and removed edge are caught deterministically before inference (100% ABSTAIN, 0 model calls).
H6 (replay): L0 cold-restart replay reproduces the frozen 38 discovery outcomes exactly at temperature 0 (agreement 38/38);
   any disagreement is recorded as nondeterminism, not corrected.

## R03 — Lean 4 compile receipt (EXECUTED)

`lean/Admission.lean` (sha256 `9f74867b…9bd0`) compiled with Lean 4.15.0 on magicSTUDIObox, exit 0, no output.
Theorems `no_admit_on_mcnemar_fail` and `no_admit_on_bootstrap_fail` type-check. Scope: a Boolean conjunction gate; the
theorems say nothing about the statistics themselves. Status moves from NOT_TESTED to COMPILED (not "proved clinically").

## R04 — Snyk and gitleaks (OBSERVED)

magicPRO: `snyk --version` = 1.1307.2; `snyk whoami --experimental` → "Authentication error (SNYK-0005) Authentication
credentials not recognized, or user access is not provisioned." Snyk gate = BLOCKED_AUTH, no scan executed. magicSTUDIObox has
no Snyk binary. Gitleaks: run against the pushed branch clone is recorded in `evidence/redteam/gitleaks_redteam_branch.json`
(see later entry).

## R05 — branch collision and sibling lane (OBSERVED 21:56 UTC)

The requested branch name `redteam/claude-fcg-local-ablation-20261102` was already on origin with commits from a concurrent
Claude Code session (Claude Opus 5.5, `session_015q5z1zKr1rBHbSRyNW2L18`) running the same mission on magicSTUDIObox and magicPRO.
Its processes (`redteam/ablation_runner.py`, `run_logged.sh S-L1`) were visible in `ps` and share the Ollama GPU with this lane.
Decision: no force-push, no rebase onto their history. This lane continues on `redteam/claude-fcg-local-ablation-20261102-cloud`
from the same parent `da953450`. The sibling lane is an independent code-level replication (different code, same frozen cases) and
is compared case-by-case in the report where its public bits allow it. Agreement between the two lanes is NOT an independent-population
replication: same hosts, same weights, same cases, temperature 0.

## R06 — early L0 observations (OBSERVED before heldout analysis; numbers restated in the report)

* L0 cold-restart replay: 38/38 agreement with the frozen receipt and with the warm run (H6 PASS).
* The predecessor-style ACCEPT/CHALLENGE verdict prototype is degenerate on L0: the longevity fine-tune re-emits a letter
  (`UNPARSEABLE` in 100% of calls), so verdict-gated coverage is 0 (H3 partial: observed as predicted).
* The option-swap gate admits ~60% of L0 cases, and its false-admission count equals its admitted-injected count because on a
  two-option task the injected letter IS the wrong letter; the unconfounded injection metric (excess/flip) is used instead (F-05 metric artifact).

## R07 — owner directions received mid-lane (OBSERVED, acted on)

1. **Why a Liquid longevity model at all?** Because the predecessor's frozen discovery (Liquid 25/38 vs Insilico 27/38 on
   LongevityBench mini) is the evidence this lane was told to replay and extend; L0 is kept only as the pinned replay baseline.
   The product lane is Qwen: qwen2.5vl:3b (vision), qwen3:1.7b, qwen2.5:0.5b/1.5b, qwen2.5-coder:1.5b (local) and the Insilico
   Qwen3-0.6B fine-tune. The spec's Qwen3.8-27B on Fireworks is BLOCKED (no credential on either Mac).
2. **Per-field actual answers must be exported.** The forms are Synthea-derived synthetic renders and the owner authorised the
   export, so the lane now writes `evidence/redteam/db/field_answers.jsonl` (printed value, source value, every model's answer,
   bbox, verdicts). LongevityBench oracle values remain unexported (CC BY-NC, predecessor policy).
3. **Bounding boxes / small vision models.** Mistral OCR and any Fireworks vision model: BLOCKED_NO_CREDENTIAL. YOLO: no trained
   form-field detector exists locally (NOT_USED; GT boxes from the renderer are the labels a detector would train on). Implemented:
   Apple Vision boxes (already real-time, ~0.3 s/page after warm-up) and Qwen2.5-VL grounding (`bbox_2d`) scored by IoU against the
   renderer's exact geometry.
4. **Ledger contract.** Every attribution record now separates `weights` (checkpoint/adapter + digest), `mechanism` (enabled/disabled)
   and `outcome` (measured delta with gates): `evidence/redteam/attribution_matrix.json`, `evidence/redteam/db/ledger.jsonl`,
   `docs/architecture/LEAF_GAIN_ATTRIBUTION.md`.
5. **Local JSON databases, no credentials:** `evidence/redteam/db/{models.json, field_answers.jsonl, ledger.jsonl}` built on the host
   from lane files and pushed with the public exports.

## R08 — operational notes (OBSERVED)

* 22:18 UTC gitleaks pre-push scan on the first export: 273 `generic-api-key` matches on the JSON field `key` (64-hex case digest).
  FAIL receipt preserved (`evidence/redteam/gitleaks_lanes_initial_failure.json`); successor renames the exported field to
  `case_digest_sha256` (values unchanged, originals on host), loaders accept both; re-scan after the final push.
* 22:30 UTC GPU contention on magicSTUDIObox (sibling lane holding qwen2.5:1.5b, my VLM-ERR pass, the Insilico MPS lane and a
  newly queued mapper lane): Ollama began swapping qwen2.5vl in and out; the mapper driver was paused by the operator (this
  session) and will be re-queued after the VLM passes. All latency/throughput receipts from this window are CONFOUNDED.

## R09 — trained-model gain, preregistered (OBSERVED 2026-11-02)

* Protocol committed first (5615a07, sha256 `9ba4b693…`), then run once on magicSTUDIObox against the 46 test images (EXIT=0).
* A1 learned correction: all-7 14→22/46, Holm p=0.023, CI [+0.065, +0.283], PROMOTE_DISCOVERY (replication NOT_TESTED).
* A2 detector crops: 9/46, NULL. A3 crops + correction: 15/46, NULL. Both kept as null results.
* Outputs: `evidence/redteam/trained_gain/{trained_gain_summary.json, trained_gain_rows.json, run_log.txt}`.
