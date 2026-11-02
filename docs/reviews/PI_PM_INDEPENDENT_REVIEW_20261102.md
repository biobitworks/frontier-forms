# PI/PM independent evidence review — 2026-11-02T21:45Z

Reviewer: Claude (PI/PM review role). Human PI retains authorization. Nothing here is merged or admitted.
Every result below was rerun or recomputed by this reviewer unless marked REPORTED.

Reviewed heads: `main@e232fda`, `redteam/claude-fcg-local-ablation-20261102@25c56b1`, draft PR #1 `@4634098`.

> **Point-in-time scope:** This review describes the state as of 21:45Z. PRs #10–#12 were opened after it and claim a frozen cohort, a local form server, B0 and LOMO arms. Those claims are **NOT_REVIEWED** here, so a successor review must check them independently. "B0 NOT_IMPLEMENTED" below applies only to the heads listed above.

## 1. Current source and baseline state

| Item | State | Evidence |
|---|---|---|
| Synthea form-filling baseline **B0** (teammate local form filler) | **NOT_IMPLEMENTED in repo** | No form-fill runner, server, gold labels or case-level outputs exist on `main` or any branch. `supabase/migrations/...initial_schema.sql` defines run/answer tables only. `dashboard/training_history.json` → `FF-LOCAL-B0-LOMO` = PROPOSED, every gate NOT_TESTED. |
| B0 freeze | **NOT_FROZEN** | No source archive digest, no DB snapshot, no destination readback. A claimed freeze would be rejected. |
| Synthea source version | **UNPINNED** | Importer docs download `.../downloads/latest/synthea_sample_data_fhir_latest.zip`; schema stores only label `synthea-sample-data-fhir-latest`. The cohort can change silently upstream. |
| Predecessor 15-leaf root `9e4d4df8…` | Public metadata replay PASS; source bytes NOT_TESTED here | `scripts/verify_predecessor.py` rerun: 13 source files `NOT_TESTED_SOURCE_UNAVAILABLE`. |
| Review successors (65/66/… leaves) | Root replay PASS | `redteam/verify_roots.py` rerun: roots, leaf order and leaf bytes at introducing commits PASS; NOT_SIGNED. |

**Naming collision (must fix before any comparison):** the red-team ablation's arm `B0_baseline` is *LongevityBench-mini, messages-only*. It is **not** the Synthea form-filling B0. Results from that lane must never be reported as form-filling B0/Bfull/LOMO.

## 2. N=100 database verification

**UNKNOWN / NOT_TESTED.** The only source for N=100 is `SUPABASE_Data_Helper_Script.md` (REPORTED: 112 sample patients, 12 deceased skipped). Not verified because:
- No read-only DB credential in this environment, and none should be in the public repo.
- Cloud proxy refuses `synthetichealth.github.io` (HTTP 403), so the source archive could not be fetched or counted.
- No Synthea archive found on either Mac in a read-only search of `~/projects`, `~/Downloads`, `/tmp`.

Code-level red-team findings in `scripts/import_fhir.py` (affect any future parity claim):
- **R1 nondeterministic IDs:** `uuid.uuid4()` for `source_records`/facts (lines 108, 123) and `gen_random_uuid()` defaults → two imports of the same bytes give different row IDs. Parity must compare on natural keys (Synthea patient ID, FHIR resource ID), not UUIDs.
- **R2 destructive reimport:** delete-then-insert per passport (lines 371–372) leaves no prior-state history; stale/forked rows cannot be audited.
- **R3 cohort by filter:** N=100 is `--limit 100` after excluding deceased, sorted by UUID suffix. A changed `latest` archive changes membership with no error. Deceased exclusion is also a clinical-status selection rule that must be declared in the protocol.

## 3. Local form server implementation and executed tests

- Form server: **NOT_IMPLEMENTED** (none in repo).
- Tests rerun: `main` 30/30 PASS; red-team branch 33/33 PASS (Python 3.13). These test custody/statistics code, not form-answer correctness.
- CI `independent-evidence-check` on `main@e232fda`: success (run 41529418540).

## 4. B0 vs Bfull and LOMO

- Synthea form-filling: **NOT_TESTED** (no B0, no modules, no cases).
- LongevityBench context ablation (red-team lane, different task): **EXECUTING, NOT_COMPUTED.** Observed read-only at ~21:40Z: Studio S-L0 discovery 342/342 rows (38×9 arms), S-L1 discovery 295/342 running; MacBookPro P-L1 discovery 230/342 running. Heldout not started. No jobs were touched.
- Prereg integrity flag: `redteam/PREREGISTRATION.json` states `registered_utc: 2026-11-02T21:55:00Z`, but it was committed at **21:28:58Z** (commit `411a34c`). The timestamp is hand-written and future-dated. Registration-before-inference should be anchored to the commit time, and the field corrected in an append-only successor.

## 5. Statistics

| Test | Result | Status |
|---|---|---|
| Exact two-sided McNemar, frozen discovery (LongevityBench, 38 pairs) | n10=2, n01=4, **p=0.6875**; 25/38 vs 27/38 | Independently recomputed from `evidence/stats/discovery_pair_flags.jsonl`; matches. 38 distinct case digests. NEGATIVE. |
| Paired bootstrap, seed 20261102, 10k | Δ=+0.053; unstratified 95% CI [−0.079, 0.184]; task-stratified [−0.053, 0.184] | Recomputed; CI includes 0. NEGATIVE. (Exact bounds depend on RNG implementation; conclusion does not.) |
| Patient-cluster bootstrap | NOT_COMPUTED | No patient-level form data exists. |
| AUROC | NOT_COMPUTED | No continuous risk scores and no unsupported/incorrect field labels exist for any form task. |
| Synthea form-filling McNemar/bootstrap | NOT_COMPUTED | Blocked on B0, gold labels, cases. |

## 6. FCO/FCG and Merkle evidence

- cloudmer `DATASET_FREEZE_V1` (project files): independently recomputed root **`4a4c2714…b618b886` matches**; 39/39 stored atoms byte-match; 9 atoms (X001–X009) NOT_STORED/NOT_ACQUIRED. **HOLD is correct** — source bytes missing. (Leaf field list taken from `freezelib.build_leaf`; tree recipe implemented separately.) No cloudmer evidence copied here.
- FCG impact-view finding (REPORTED by red-team lane, plausible from file list): source parquet edges do not reach discovery outputs/stats, so a source revision would under-propagate. Not yet independently replayed.
- A Merkle PASS proves byte identity/inclusion only; it is **not** evidence of better form answers.

## 7. GitHub PR and merge status

PRs #3–#8 merged to `main` by the PI (GitHub API lists them as closed with `merged_at` set). PR #1 (draft) open. Red-team branch has 4 commits, no PR. **No merge recommended now**; nothing in scope has passed a scientific gate.

## 8. Vita DAISY continuity

UNKNOWN for live run states: Kaggle is refused by the cloud proxy and no Kaggle receipt was rerun. Jobs not touched. Heatmap row `VITA-DAISY-PARALLEL` remains REPORTED (correct). No results or roots transferred across programs.

## 9. Missing tasks and next authorized action

Blockers, in order:
1. Notion lab/ledger unreachable from this environment (connector failed: proxy refused tunnel). GitHub↔Notion sync NOT_TESTED.
2. Pin the Synthea archive (SHA-256 + byte count) and persist it in the schema/source table.
3. Read-only DB credential (outside the repo) for a transaction-consistent snapshot + row count + readback.
4. Implement/freeze B0 form filler with case-level outputs, gold labels and patient/template splits.
5. Rename the LongevityBench `B0_baseline` arm (e.g., `LB-B0`) and correct the prereg timestamp in a successor.

Next action needing the PI: decide 2–4 (source pin and DB access) before any form-filling comparison.

```
TURN_BREAKPOINT: PIPM-REVIEW-20261102-01 | PARENT main@e232fda | VERIFIED_NEW: DATASET_FREEZE_V1 root recomputed match (39 stored, 9 not stored); discovery McNemar p=0.6875 recomputed; review-successor roots replay PASS; tests 30/30 + 33/33 PASS | EXECUTED: unit tests, predecessor metadata replay, root replay, McNemar, bootstrap, read-only device inspection | OBSERVED: LB ablation running (S-L0 disc complete; S-L1, P-L1 partial); prereg timestamp after commit time; importer uses uuid4 + unpinned 'latest' archive | DECISIONS: no merge; no admission; V1 HOLD upheld | PROPOSED: pin Synthea archive, DB read-only snapshot, B0 freeze, arm rename | NOT_TESTED: N=100 DB count, B0, Bfull, LOMO (forms), local-vs-Postgres parity, Epic sandbox | FAILURES: Notion connector, Synthea fetch (proxy 403), Kaggle unreachable | UNRESOLVED: Vita DAISY live states, patient-cluster bootstrap, AUROC | NEXT_ACTION: PI to authorize source pin + read-only DB access
```
