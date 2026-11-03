# Frontier Forms: open PRs and gap analysis (2026-11-02, about 23:20Z)

Reviewer: Claude (SWE/PM thread). It covers draft PRs #1, #14, #15, #16 and #18, and asks, gap by gap, whether those PRs or the merged work (#10, #12, #19) close it. Everything below was read from git at `main@dda6a66` plus this branch. "Filled" means there is executed evidence on main, not just a plan.

## 1. The PRs

| PR | Author / lane | What it adds | Size | State at review |
|---|---|---|---|---|
| #14 | biobitworks (Studio agent) | A logistic-regression box classifier on OpenCV contour proposals, trained on the 3 blank forms. It scores 540 boxes over 54 test forms. **Result:** recall 1.0, but a deterministic contour control also gets 1.0, so the gain is 0 (McNemar p=1, patient-cluster CI [0,0]). The weights are published as JSON coefficients. | 11 files, +943 | **Already merged** (1a80f48, 23:11Z) |
| #15 | biobitworks (Studio agent) | A Random Forest box-validator factorial: geometry/shape/pixel feature blocks, giving 7 trained arms plus a contour control at 3 scales. It is trained on train-split patients and tested on 18 test patients, including the urgent-care layout. The PR labels it EXPLORATORY. Several arms produce results identical to the control (same result hash). | 11 files, +481 | **Already merged** (280e69a) |
| #16 | Byron P. Lee | Two locally trained bbox validators. **D1:** recall 0.13, precision 0.10, so negative, and preserved as such. **D2:** a candidate-box classifier with recall 0.956, precision 0.656 and 180 false positives. It adds an independent byte/IoU replay and a fix to the synthetic-JSON policy checker. New-template generalization is NOT_TESTED. | 8 files, +730 | **Already merged** (dda6a66) |
| #18 | biobitworks (audit lane) | A longitudinal checkpoint dashboard (`dashboard/training_progress*.json/html`) that re-scores the FCO/FCG LOMO with Holm-Bonferroni correction and patient-cluster CIs, plus Merkle successor snapshots. No trained-model gain is admitted. | 20 files, +1795 | **Already merged** (2c89dd4) |
| #1 | ChatGPT (PI/PM review lane) | Freezes the EHR FCO evaluation protocol: docs, 5 notebooks, Lean custody invariant, paired stats scripts and a CI workflow. Notebook 05 (Fireworks costs) is a stub that makes no provider calls and prints NOT_TESTED. | 26 files, +1243 | **Open, conflicts with main.** It is 134 commits behind and edits `README.md`, `.gitignore`, `.github/workflows/verify.yml` and `scripts/build_notebooks.py`, which main has since changed. |

The four stacked PRs were merged through the GitHub web UI between 23:11 and 23:12Z, not by this thread. On the merged main, all unit tests pass and `scripts/check_public_payloads.py` passes (759 files). None of them commit binary weights.

**Overlap with our own work:** #14, #15 and #16 each train a *box* detector, as does our V2 (YOLOv8n, #19 pipeline). They complement each other rather than conflict, because each writes to its own directory. Two differences matter:
1. Only V2 maps boxes to fields and checks the *written value* (Tesseract crop against the planned value). #14, #15 and #16 stop at box localization.
2. Only V2 and #15 test on a held-out layout.

**#1 safe to merge?** Not as it stands. It conflicts, and most of its protocol and notebooks appear to have reached main already through #3 to #8. Its owner should rebase it or close it as superseded. This thread does not merge it.

## 2. Gaps

| Gap | Status | Evidence / what is missing |
|---|---|---|
| Fresh replication cohort | **NOT FILLED** | Every lane flags that the test patients were inspected before the L1–L3 modules were designed, and #18 records `replication: NOT_TESTED`. **Needed:** a new Synthea seed (for example `-s 20261103`) and new templates, scored once, with frozen arms. |
| Oracle-rule sign-off | **NOT FILLED** | Two rules still need PI sign-off: conditions count as disorders only, and a missing allergy record means "ask the patient". No PR touches this. |
| Noisy or scanned forms | **NOT FILLED** | All arms read clean browser renders. V2 adds layout and value randomization, and #15 adds deterministic augmentations, but nothing covers scan noise (blur, skew, JPEG, fax, handwriting). Apple A2 OCR read-back is the closest, and it already loses dropdowns and long lists. |
| Prompt-injection fix | **MEASURED, NOT FIXED** | V1i (qwen2.5vl:3b, 18 clean and 18 injected paired images) followed the injected note in 0 of 18 images. Box recall and value reads are about the same with and without injection (0.59 vs 0.61 and 0.54 vs 0.54), so the injection does not degrade the reads. Tesseract copies the injected note verbatim as text in 19 of 57 images. The urgent-care form still shows its untrusted notice, and no sanitizer or source-binding guard runs before a model reads the page. M3 source binding catches injected *values*, not instructions. |
| Cost/latency per correct form | **PARTIAL** | Latency is recorded per page or call: V1 24 s/page, V1i 23 s, Tesseract about 0.3 s, Ollama text arm per field, and V2 receipt fields. No "seconds (or $) per fully correct form" metric is computed. Hosted pricing is NOT_TESTED by design, because inference is local only. |
| Review of PR #3's later changes | **NOT FILLED** | No PR here reviews #3's later commits. It is still owed by the review lane. |
| N=100 readback | **PARTIAL** | The repo cohort `data/forms_cohort_v1` is independently re-counted: 100 distinct patients, cohort root `ee202dd8…`, recomputed by the PI/PM review on #10. The teammate database count still has no readback. Per Byron, the transformed JSON is the source, so this should either be closed as N/A or done with a local read-only export. |
| Post-training arm | **NOT FILLED** | M1 SFT (Qwen2.5-0.5B LoRA) was stopped at 23:15Z, without saving an adapter, to free memory for Vita DAISY on the Studio. It will restart on MacBookPro. M0 zero-shot is still running on MacBookPro. Run qwen3:1.7b (M2) after M0, also on MacBookPro. #18 admits no training gain. |
| Vision validator | **PARTIAL (boxes filled, value check not)** | Four trained box detectors exist from other lanes: #14 (gain 0), #15 (exploratory), #16 D1 (negative) and D2 (recall 0.956, precision 0.656), plus V1 qwen2.5vl inference (recall 0.82, 213 false boxes). **V2 YOLOv8n (executed, `evidence/forms_detector/V2-yolov8n/`):** box recall 1.000 with IoU 0.965 on seen layouts, and 0.997 with IoU 0.958 on the held-out urgent-care layout (class accuracy drops to 0.78 there). Its Tesseract value validator flags 94% of wrong values on seen layouts (33% held-out) but also flags about 58% of correct ones, so the *value* check is not usable as a gate. Next: a better crop reader (Apple Vision or the VLM on the crop) behind the V2 boxes. |

## 3. Next actions
1. **PI:** sign off on, or change, the two oracle rules, and decide whether the teammate DB readback is N/A.
2. **This thread:** land the V2 detector results, then M0/M1/M2 on MacBookPro, keeping the Studio free for DAISY. Add a "seconds per correct form" column to the arm summaries.
3. **Next protocol step:** build a fresh replication cohort and a scanned/noisy rendering of the test forms, preregistered before any arm sees them.
4. **#1 owner:** rebase or close as superseded. **Review lane:** review #3's later changes.
