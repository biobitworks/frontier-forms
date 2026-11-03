# Frontier Forms — public data availability and merge reconciliation

**Snapshot:** GitHub biobitworks/frontier-forms at main f10e1d7bb6856c85f9db054d409867ff65922c02 on November 2, 2026, after the competition deadline. This is an **append-only audit successor**, not evidence that any post-deadline changes were included in the HackerSquad submission.

[Machine-readable source coverage, exact 15-file SHA-256 readback and 13 remote-branch inventory](FINAL_PUBLIC_DATA_COVERAGE_20261102_V1.json)

## What's integrated versus unavailable?

| Review question | Observed answer | Scope |
| --- | --- | --- |
| Open PRs in frozen predecessor GitHub snapshot | **0** | **60 merged** and **4 closed without merge** of 64 inspected PRs; closed #1, #27, #45, #55 |
| Published predecessor main files | **1,468** | 549 evidence paths, 206 data paths, 70 Jupyter notebook paths, 283 PNGs and 570 JSON files; overlapping types, not independent studies |
| Critical synthetic evidence / figures accessible on main | **15/15 checked paths** | Actual file bytes and SHA-256 stored in the JSON receipt; includes 40-epoch detector metadata, 30+30 epoch ledgers, corrected Gantt, discovery register, acceptance outcomes |
| Remote branch heads not ancestors of main | **13** | Some contain branch-only historical code, docs, a synthetic binary fixture or redundant fixes; not proof all source bytes have been integrated |
| Unique historical public-safe JSON receipt | **1 imported byte-for-byte** | evidence/forms_bbox/MAIN_WORKFLOW_PARSE_CORRECTION_20261102.json, SHA-256 cbe7d67eb961e960068b13e22ba297877bd3dab03eda464c1fe6497d5f35d5cc |
| Unpublished trained weights and raw V2 forms | **NOT_PUBLIC** | V2 trained-checkpoint SHA exists; receipt explicitly says weights_published=false, images_published=false |
| Independent scientific replication | **NOT_TESTED; admission HOLD** | Separate FCO +22.22 percentage points and fitted OCR correction +17.39 points are synthetic discoveries, not independently replicated clinical efficacy |
| External HackerSquad submission accepted | **UNKNOWN** | Git merge and judge package do not establish third-party submission acceptance |
| Anonymous access to Notion | **UNKNOWN** | GitHub public images remain the judge access fallback |

The previous [63-PR Gantt](FINAL_SUBMISSION_REVIEW_AND_TRAINING_20261102.md) and its frozen sources are preserved; they are an earlier snapshot, not a claim about the final 64-PR review.

## Why 13 branch references remain unmerged

The branch-head ancestry test finds 13 remote branches that are not ancestors of this main commit. Nonancestry does **not** mean all their results are absent: some were integrated via later cherry-picks, rewrites, or successors. Affected old branches contain older protocol notebooks, duplicated figures and repaired code; blindly merging their entire HEAD would potentially overwrite corrected CI, source receipts and policy gates.

One older branch has a source-only synthetic binary fixture named synthetic_pseudobulk_v1.bin. It was **not imported** into main; it would require explicit public-rights and binary-policy review. Another branch contains a historical CI YAML parse failure receipt, safely copied **without changing its bytes** into main. That receipt retains new_ci=NOT_YET_EXECUTED as a historical statement. The separately verified newer main GitHub workflow is SUCCESS; do not rewrite predecessor status as a retroactive PASS.

All 13 branch names, heads, ahead-commit counts, unique-only paths, and modified-existing path counts are listed in the frozen JSON.

## Remaining experiment and publication gates

- **NOT_COMPUTED:** matched before/after Qwen LoRA held-out model improvement. Earlier epoch-zero validation-loss records cannot establish a generalization benefit.
- **NOT_TESTED:** untouched independent prospective synthetic cohort and template replication; full 100-patient Qwen acceptance in the saved acceptance receipt; production Epic writeback; independent Supabase/teammate database readback.
- **PARTIAL:** V2 YOLOv8n local detector shows strong box recall but held-out field-class errors and high diagnostic false-flag rates. Box localization alone is not reliable form filling.
- **FAILED and preserved:** old manifest mismatch and Gantt display-label mismatch have distinct corrected successors.
- **UNKNOWN:** the exact external contest submission receipt, actual anonymous Notion publish settings, and whether branch-only historical code should be separately recovered.
- **DECISION:** preserve all predecessor states and avoid publishing raw private weights/embedded images or new noncompliant binary fixtures merely to increase file coverage.

An older acceptance JSON reports a publication policy FAIL for 123 legacy items. The current incremental public-data gate reports PASS with those **123 historical files unchanged and exempt from new-addition checks**; it is not a retrospective claim all old payloads were compliant. Source SHA-256 checks prove exact-byte identity, not data accuracy, clinical truth, scientific novelty, or causality.

## Reproduce receipt-only checks

Run python3 scripts/verify_final_public_data_coverage.py to validate the 15 source-file SHA/size pairs, historical CI-receipt bytes, frozen PR counts and branch status assertions. This runs **no model inference**, does **not** compute a new Merkle root, and does **not** access connected private drives or external submission records.

Judge navigation: [README and visual results](../../README.md) · [source-linked Gantt and training comparison](FINAL_SUBMISSION_REVIEW_AND_TRAINING_20261102.md) · [Notion main research hub](https://app.notion.com/p/40c58ec71eb28161b79ddfbb083cb7c0) · [figure gallery](https://app.notion.com/p/40d58ec71eb281db9ba2db19e7f7adf6).
