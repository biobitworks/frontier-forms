# What was novel and what was standard training (red-team lane)

This page covers the Claude red-team lane only. The project-wide note is [DISCOVERY_ADMISSION_AND_NOVELTY_20261102.md](DISCOVERY_ADMISSION_AND_NOVELTY_20261102.md) from PR #66. Every number below is recomputed from committed evidence by `scripts/redteam/build_discovery_admission.py`. The machine-readable ledger is `evidence/admission/REDTEAM_DISCOVERY_ADMISSION_V1.json`, and `tests/test_redteam_discovery_admission.py` checks it in CI.

**Status:** results are admitted to the discovery ledger only. Scientific promotion is on HOLD for every record, because no independent replication cohort exists. Nothing here is SUPPORTED. All data is synthetic (MITRE Synthea), and no model weights are published.

## Standard training we used as-is

| Component | What is standard | What we did not change |
|---|---|---|
| YOLOv8n field detector | Ultralytics fine-tuning of a pretrained detector | Default hyperparameters, 30 epochs, standard validation metrics |
| Apple Vision OCR | Off-the-shelf OCR | No training; `.accurate` recognition |
| Qwen models (qwen2.5vl:3b, qwen2.5:1.5b, qwen3:1.7b) | Pretrained Ollama weights | No fine-tuning by this lane; inference only |
| Learned OCR correction | A post-OCR correction table, a long-standing technique | Simple counting rules |
| Statistics | Exact McNemar, paired bootstrap, Holm correction | Textbook methods |

## What this lane added

1. **Training as a hash-chained ledger.** Each detector epoch is committed as a Merkle leaf. The leaf holds the weights sha256, a paired McNemar test and bootstrap against the previous epoch, and a GAIN, LOSS or NEUTRAL status. A second run leaves out the scan variants (leave one mechanism out).
2. **Preregistered trained-versus-untrained test.** The arms, endpoint and statistics were committed before the test split was scored (commit 5615a07). The OCR engine is held constant, so only the trained component differs between arms. The test split was scored once.
3. **Per-field source commitments as an admission gate.** Each field carries a salted hash of its source value inside the FCO leaf. A full 2⁴ factorial with leave-one-mechanism-out measures what each check adds.
4. **Planted-error dataset with blind ids.** SYNFORM2-ERR has opaque image ids and keeps the planted-error list private, so extractors cannot see which images were altered.
5. **Weights, mechanism and outcome kept apart.** Every attribution record names the exact weights, the mechanism switched on or off, and the measured difference separately.

## Admitted to the discovery ledger (scientific promotion HOLD)

| Record | Result | Holm p | 95% CI | Standard or novel |
|---|---|---|---|---|
| Learned OCR correction (trained on train split) | 14→22 of 46 forms all 7 fields correct | 0.023 | [+0.043, +0.326] patient-cluster | Standard technique, novel protocol |
| Commitment check | planted-error detection 1.00, 0 false admissions | <0.0001 | [+0.61, +0.66] | Novel integration of a standard building block |
| Rules check | detection 0.51 | <0.0001 | [+0.25, +0.30] | Standard |
| Consistency check | detection 0.31 | <0.0001 | [+0.12, +0.19] | Standard |
| All four checks | detection 1.00, 0 false admissions | <0.0001 | [+0.50, +0.56] | Novel combination |

**Caveats.**
- **The correction is small.** It strips spaces from every field and maps `O` to `0` in the case id.
- **The commitment check works by construction.** It detects any printed value that differs from the source. The finding is that the other checks miss most planted errors, not that hashing is new.
- **Same authors.** The planted errors were designed by the same lane that wrote the checks.

## Post hoc model comparisons (recorded, never promotable)

These comparisons use the same 46 test images against Apple OCR plus the rule parser, which got 14 of 46 forms fully correct. They were not preregistered.

| Model (pretrained, not trained by us) | All 7 correct | Holm p | Reading |
|---|---|---|---|
| qwen2.5vl:3b | 42/46 | <0.0001 | Much better than OCR plus parser |
| qwen2.5:1.5b text mapper | 1/46 | 0.0002 | Worse |
| qwen3:1.7b text mapper | 0/46 | 0.0002 | Worse |

## Null, negative, failed and not-tested results kept

- **Trained detector crops plus OCR:** 9 of 46 forms, NULL. With the correction added: 15 of 46, NULL. A good detector (test mAP50 0.912) did not make crop OCR better.
- **FCO/FCG context in the prompt:** NULL in all six paired comparisons.
- **Small Qwen models on LongevityBench:** NEGATIVE_WORSE in four paired comparisons.
- **Identity check alone:** NULL.
- **Drawing boxes on the image:** Apple OCR fell from 58/70 to 0/70 correct fields. This is NEGATIVE and descriptive only.
- **macOS Preview capture:** FAILED for 0 of 10 windows.
- **Not run:** Fireworks and the hosted harness are BLOCKED. NVIDIA training and live sources are NOT_TESTED.

## Attribution correction

PR #66 lists the OCR-correction result under PR #58. The primary source is this lane's preregistered run, `evidence/redteam/trained_gain/`, merged in PR #51 (commit 4a52345). PR #58 re-plotted those numbers. This ledger also adds the patient-cluster bootstrap that PR #66 noted was missing. The result still passes, with CI [+0.043, +0.326].
