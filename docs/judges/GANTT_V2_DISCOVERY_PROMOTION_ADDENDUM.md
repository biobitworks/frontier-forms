# Gantt V2 — post-snapshot discovery promotion and NULL controls

**Successor of:** the frozen [Gantt V1](FRONTIER_FORMS_GANTT_20261102.html), which stopped at 3:46:01 PM PST and indexed 42 PRs. Its previous state and admission counts remain unchanged.

**Updated frozen snapshot:** November 2, 2026, **3:57:09 PM PST**. [Updated Gantt V2](FRONTIER_FORMS_GANTT_V2_20261102.html) displays **46 PRs** (38 merged, 5 open, 3 closed-unmerged) and **18** dataset/model/governance milestones, with original PR-creation/merge clocks preserved. This is still a PR-review timeline, not engineering or training hours. The updated evidence index links 474 existing Git-tracked JSON files, not 474 independent datasets.

## Newly supported result (not visible in V1)

Merged **Claude PR #51** contains [SYNFORM2 trained-gain summary](../../evidence/redteam/trained_gain/trained_gain_summary.json), authored at **2026-11-02 23:51:55 UTC** (3:51:55 PM PST). On **46 synthetic held-out test images**, comparing all seven fields correctly:

| Arm | Complete seven-field images | Compared with baseline A0 | Holm p | Interpretation |
|---|---:|---:|---:|---|
| A0: page OCR + untrained rules | 14/46 | Baseline | — | OBSERVED |
| A1: A0 + learned OCR correction | **22/46** | **+8/46 = +17.39 percentage points** | **0.0234375** | **PROMOTE_DISCOVERY**, not clinical or replicated |
| A2: trained YOLO detector crop + OCR | 9/46 | −5/46 = −10.87 pp | 0.5336914 | NULL / NOT_PROMOTED |
| A3: crop + correction | 15/46 | +1/46 = +2.17 pp | 1.0 | NULL / NOT_PROMOTED |

A1 has eight challenger-only wins and zero baseline-only wins; bootstrap CI +6.52 to +28.26 percentage points. This is a **discovery-only local trained component result** with a preregistered comparison in the experiment script, single test-split touch, and **independent replication NOT_TESTED**. It does not contradict the earlier separate 24-event ledger, whose eight discovery-positive events were all unpromoted; A1 belongs to a later, independently recorded experiment. No real clinical performance, Epic production writeback, or general trained-Qwen model superiority is established.

Claude's **PR #58** adds the new result into existing figures, but was **open at the V2 cutoff**. Those figure updates should not be shown as already merged into V2. ChatGPT/independent PR #55 on judge annotation manifest hash repairs was also open at cutoff; it preserves a negative 10/62 manifest error state rather than claiming evidence of a trained gain.

**Admission accounting:** 38 GitHub merges; **1 discovery promotion in the newly merged trained-gain result**; **0 independently replicated or clinical scientific promotions**. Earlier 24-event ledger: 14 negative/tie, eight unpromoted discovery-positive, two baseline/methodology. Other negatives remain in [the successor register](PROMOTION_AND_NEGATIVE_RESULTS_V2_20261102.json).

Do not update V1 retroactively. All changes are append-only chart and JSON successors. No scientific experiment, model fine-tune, dataset transform or Merkle root was executed to create this addendum.
