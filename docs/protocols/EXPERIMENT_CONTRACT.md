# EXP contract and statistical admission

Each EXP has Requirements, input origin/license and source SHA, data partitions and ground truth visibility, transformation recipe, analysis method, output hashes, negative controls, confidence intervals, failure register, claim ceiling and NEXT_ACTION.

Phase P00: source/rights/secret audit and immutable predecessor frozen. P01: offline FCO/Merkle and matched statistics. P02: Synthea CSV/FHIR → labeled form images with synthetic patient/template held-out partitions. P03: local OCR + Microsoft DI + NVIDIA document stack only when actually used. P04: Fireworks A1 minimal vs A2 governed harness with same model and generation params. P05: pre- and post-training independent inputs/recipes/weights. P06: held-out tests and second dataset/form-template replication with statistical acceptance. P07: Snyk, Lean, GSD, gsigmad, peer review and release admission.

McNemar: exact, two-sided, paired binary correctness; discordant b and c under symmetric null; alpha=0.05 predeclared, or Holm adjustment for multiple primary comparisons. PASS only if p<alpha and challenger wins more pairs. Bootstrap: 10000+ matched resamples, stratified by task, declared seed, observed 95% CI lower bound >0. Independent replication must be on a second untouched population or form-template set; no re-selection after viewing results.

FPR = FP/(FP+TN); FDR classification = FP/(TP+FP); FNR = FN/(TP+FN); undefined denominator = NULL. FDR in multiple hypothesis testing is a different measure from classification FDR. AUROC requires per-case continuous score, true binary labels and both classes. No probabilities means NOT_COMPUTED, not 0.0.

LOMO: one named antigentic mechanism removed at a time with same Fireworks weights, cases, tools, prompt, parameters and environment. Pretraining/posttraining and system-level model differences are NOT a LOMO intervention. Preserve baseline task completion, prompt injection ASR, false-admission, latency, usage and cost.

Token ROI requires actual Fireworks token receipts + time-referenced model rates + retries + relevant OCR per-page charges + observed human review costs. An illustrative pricing formula is not observed business ROI.

Status labels: PROPOSED ≠ IMPLEMENTED ≠ EXECUTED ≠ OBSERVED ≠ SUPPORTED. Also FAILED, NULL, NEGATIVE, DEFERRED, NOT_TESTED, UNKNOWN and NOT_COMPUTED. Errors create successor FCOs and do not erase old evidence. Lean proof code is NOT_PROVED until compilation receipts exist.
