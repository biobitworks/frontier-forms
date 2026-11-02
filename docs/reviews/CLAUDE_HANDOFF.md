# Claude independent peer-review task

Objective: independently falsify or corroborate our frozen-source, mathematical, FCG custody and reproducibility claims. This PR is not pre-approved. DO NOT trust our verifier alone.

1. Resolve the PR parent commit 67bf6b0ba51dc7ed792c139f37fcc648653611c4. Independent canonical encoder + leaf hashing + odd duplication for 15 ordered leaves. Expected predecessor root 9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a. If authorized on magicSTUDIObox, independently rehash original source files. Verify separate 728-input root and inclusion proofs, oracle isolation.
2. Independently pair 38 discovery cases by row SHA. Compare 25/38 vs 27/38; discordant 2 baseline-only, 4 challenger-only, exact two-sided McNemar 0.6875. Recompute paired stratified bootstrap and record RNG/method differences. Do not claim significance.
3. Verify FPR/FDR/TPR with class-specific denominators, optional macro rates; AUROC remains NOT_COMPUTED without continuous scores. Add corruption, swapped-keys, bad tree order, missing-label and zero-denominator tests.
4. Ensure LOMO is single-mechanism removal with the SAME Fireworks model weights and fixed data; model comparison is not LOMO.
5. Verify Synthea is synthetic input; Epic is technical spec not a dataset; no PHI or live write. Test source rights.
6. Check pinned NVIDIA Megatron source SHA; do not assume training on Mac Studio. Check Fireworks usage/receipt; if absent NOT_TESTED.
7. Run seven notebooks with independent kernels and compare output/status. Try real Lean4 compilation only if installed. GSD and gsigmad CLI commands must be executed to claim PASS, no invented registration IDs.
8. Run Gitleaks and authenticated Snyk where possible. Avoid credential leakage. Check public files have no raw weights, patient data or answer oracle.
9. Report table: requirement, source atom/path, expected, observed, PASS/FAIL/NOT_TESTED, earliest divergence, affected claims, repair successor, recommendation. Post review to PR as COMMENT/REQUEST_CHANGES only if justified; do not self-merge. Preserve old negative results.

Artifacts: input source manifest and leaves, verified receipts, statistic flags, notebooks, experiment ledger. Publication claim ceiling INTEGRITY_ONLY and DISCOVERY_NEGATIVE. No signed keys, MMR commitment or causality is established by the prior root.

## Successor review: Supabase source intake (2026-11-02)
The user reports a dataset under construction on Supabase. Verify `evidence/sources/supabase_source_intake.json` does not claim an observed project ID, table schema, record count, data export or Merkle source root. Verify `docs/protocols/SUPABASE_SOURCE_CONTRACT.md` requires a transaction-consistent authorized snapshot, source rights/PHI assessment, row/schema validation, canonicalization, independent replay, and append-only successor. Review EXP-007 notebook as a **negative admission gate** only; neither `NOTEBOOK PASS` nor a hash of this registration file constitutes a Supabase dataset freeze. When access is granted later, collect actual Supabase project and snapshot receipts in a fresh PR and independently validate before reclassifying.
