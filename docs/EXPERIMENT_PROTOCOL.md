# GSD × gsigmad × MSM preregistration

Each experiment must have an executable notebook: requirements → exact-byte input → deterministic transformation → output and evaluation → custody receipts → review decision. GSD manages bounded orchestration and file-state; gsigmad governs preregistration, data contract, ablations and red-team; FCO/FCG is the exact-byte evidence authority.

## Phases
P0 recover exact predecessor, Git SHA and role authority.
P1 source rights and reproducible synthetic Synthea cohort.
P2 form render + field atom FCOs + hidden oracle, independently recomputed Merkle checkpoint.
P3 plain off-the-shelf model and local OCR baselines.
P4 same Fireworks model/config on direct serverless, DAISY, DAISY+Antigence; record token costs and exact output.
P5 LOMO: one at a time remove source parsing, retrieval/FCG, policy challenge, context memory, routing and FHIR validator. Freeze identical cases/seeds. Never disable medical safety in actual production.
P6 paired analysis: exact McNemar at patient/form level, paired bootstrap 10,000 samples stratified by task or clustered by patient; corrected multiple tests. Other metrics: complete-form exact success, precision, recall, FPR, FDR, AUROC for confidence-scored *binary error detection*, abstention, latency, billed tokens, and USD per verified form.
P7 second untouched patient cohort and different form template. Do not tune on test.
P8 replay, Lean 4 invariants, Gitleaks and authenticated Snyk, report absent gates NOT_TESTED.
P9 independent Claude/team review; release only after explicit approval.

## Confirmatory promotion rules
Baseline/challenger predictions paired on identical exact case IDs and oracle. Challenger must be directionally better; two-sided exact McNemar p<0.05 (with prespecified multiplicity handling); paired 95% bootstrap lower bound >0; effect survives a second untouched test set without safety regression. Missing results = NOT_TESTED/HOLD, not PASS. Non-significance does not establish equivalence.

AUROC requires continuous scores and known binary labels; not an OCR-string metric. FPR denominator FP+TN; FDR denominator FP+TP, zero denominator = NULL. Threshold and positive class frozen before test. McNemar significance tests binary form correctness, not the model's free-form quality.

Price-anchored cost: measured input/output image tokens × provider price version, plus OCR/runtime/host costs. Token ROI = correct accepted fields per 1M billed tokens, not invented savings; local hardware is not free.

**Current** original 38 discovery cases: p=.6875 and bootstrap CI overlaps zero → NEGATIVE for superiority, transfer NOT_TESTED.
