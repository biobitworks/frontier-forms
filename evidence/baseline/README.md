# Before/after baseline (v1)

**Baseline number: 33.3% full-form success (18 of 54 forms) on the frozen held-out test split.** A form counts as a success only when every required field is correct. Field accuracy on the same forms is 80.7% (436/540). Machine-readable version: `BASELINE_V1.json`.

## Why this number and not 46.3%

The 46.3% (101/218) B0 figure covers all 100 patients. The fine-tuning set `data/forms_sft_v1` trains on the 63 train and 19 validation patients, so a trained model would be scored partly on its own training data. Only the 18 test patients (54 forms, including the held-out urgent-care layout) are unseen by all three arms. Every before/after comparison uses those 54 forms, the same form server and the same code oracle.

## Three arms on the same 54 forms

| Arm | What it is | Full-form success | Field accuracy | State |
|---|---|---|---|---|
| A0 pre-harness | B0 frozen rule filler | **0.333 (18/54)** | 0.807 | Observed |
| A1 with FCG harness | B0 + L1 evidence/abstain + L2 units + L3 clinical filter | 0.556 (30/54) | 0.930 | Observed, discovery grade |
| A2 after training | Qwen2.5-0.5B-Instruct fine-tuned on `forms_sft_v1` | not scored yet | not scored yet | Training is running on the Mac Studio (epoch 0, val loss 1.005) |

A0 to A1 on the test split: +22.2 points. All 12 discordant forms moved in the harness's favour (exact McNemar p = 0.00049). The 95% CI is [0.07, 0.37] with patient-cluster bootstrap and [0.13, 0.33] with template-stratified bootstrap. The L1–L3 modules were written after B0 errors were seen on all splits, so this gain needs replication on a new cohort or template set before it is admitted.

For A2, score the trained checkpoint the same way, both alone (M1) and inside the harness (M1+L1+L2+L3). Also score the untrained base model (M0), so the training gain is separated from the switch from rules to a model. Each ledger row records the checkpoint SHA-256, whether the harness is on, and the paired delta.

## Supabase reconciliation

Supabase was not queried: no Supabase connector is installed, there is no read-only DSN on the Mac Studio, and the cloud proxy blocks supabase.com. The table below compares what the team reports for Supabase with the local frozen cohort, both built by the same teammate importer (`scripts/import_fhir.py`, unchanged).

| | Supabase (team-reported) | Local frozen cohort (computed) |
|---|---|---|
| Source | Synthea pre-generated sample, `latest` zip, unpinned | Synthea v3.4.0, seed 20261102, pinned |
| Patients | 100 living of 112 | 100 living |
| Passport facts | 8,252 | 11,254 |
| Source records | 8,252 | 11,254 |

These are two different synthetic cohorts. All the numbers above come from the local frozen cohort, not from Supabase. To use Supabase as the source, freeze a read-only snapshot and rerun A0–A2 on it as a successor. Do not mix the two cohorts in one comparison.

**Claim ceiling:** synthetic patients, scored against a code oracle. These are not clinical accuracy figures.
