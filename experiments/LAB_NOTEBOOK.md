# Frontier Forms append-only laboratory notebook

## P00: 2026-11-02 source freeze
15 ordered leaves, 13/13 file SHA and size checks PASS on magicSTUDIObox. Recomputed root 9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a. Historical input root 5f9a7e51f1ee03d70d34e99358fe14230efa396f7fd851df21f424e6843f61b1 with 728/728 inclusion proofs PASS. NOT_SIGNED; MMR NOT_COMPUTED.

## P01: 2026-11-02 discovery comparisons
38 cases, matched SHA keys, baseline 25 correct, challenger 27. Discordant cells baseline-only 2, challenger-only 4. McNemar exact two-sided p=0.6875. Earlier bootstrap CI [-0.078947,+0.184211], successor independently coded bootstrap CI [-0.052632,+0.184211]; method/RNG resampling differences not hidden. Both contain zero. Superiority NEGATIVE.

## P01 successor: public review export
Preserve predecessor root and raw byte identities. Export only hashes, booleans, task confusion aggregates and verified receipts. Seven notebooks specify requirements, input, analysis and outputs. Actual execution receipts tracked separately.

## P02+ / NOT_TESTED
Synthetic form render/OCR/FHIR, Fireworks, NVIDIA training, Microsoft Document Intelligence, Epic OAuth and read/write, LOMO intervention, external replication, Lean4 compilation, GSigmaD registration and Snyk authenticated scan. Append new entries with successor evidence, not edits to history.

## P01 security failure and repair successor (2026-11-02)
First staged Gitleaks scan FAILED with 38 generic-api-key pattern matches on hashed case identifiers in the review export. No actual API secret was identified in this controlled exported field. Renamed the exported field from row_key_sha256 to case_digest_sha256; kept the 38 actual digest values unchanged; preserved security failure receipt. Staged security rerun PASS, zero findings. The original P01 notebook run output remains in notebook_runs_v2_prekeyfix; new execution is a successor.

## P01 verifier failure and successor (2026-11-02)
Previous review root 37152dc823a8009fc8d7a7a2b7abaf819fa00e6bc3377b2b2ea1f50cfe7641e7 was COMPUTED, but the initial independent verifier FAILED with KeyError signed (manifest used signature). Preserved exact predecessor at Git commit bf58691bbf93753a9a63b4722e479d8b044fcb01, then created a new verifier that reads predecessor bytes from Git history and current bytes from current tree. Old failure not promoted to PASS.

## P02 source intake: Supabase (2026-11-02)
The user reported a Supabase-hosted dataset under construction. No project reference, tables, data classification, row count, transaction snapshot or model-labeled records were supplied. Intake is REPORTED_IN_PROGRESS, NOT_OBSERVED. Source root NOT_COMPUTED and export NOT_AUTHORIZED. Added source contract and notebook protocol; no Supabase API calls or SQL executed. Prior project root and both review successors remain unchanged. New successor shall reference old review root and this intake event only.

## P03 remediation and Supabase integration reconciliation (2026-11-02)
GitHub reviewer identified two legitimate risks in PR #3: the private paired exporter could trust forged matching case keys without hashing frozen eval input bytes, and notebook reruns targeted a frozen output directory. Repaired by fail-closed verified digest/size checks for frozen 3 input files and never-overwrite unique execution directories. Existing v1..v4 receipts and roots are preserved. Merged teammate PR #4 into the review branch, resolving the added-in-both .gitignore by union of patterns. This changes no deployed database, patient records or teammate importer. The imported SQL migration and Python code are new review evidence, not a computed Supabase source snapshot. PR #6 Claude red-team fixture has a different Merkle construction (RFC 6962 split shape + newline) from the original duplicate-last predecessor; its root is not interchangeable.

## P04 postmerge red-team verifier security correction (2026-11-02)
Concurrent reviews merged teammate PR #5 and Claude synthetic PR #6 before the PR #3 evidence merge. The postmerge combined tree contains a binary synthetic fixture that conflicted with the all-binary-denied GitHub workflow. Codex also identified a genuine forged custody-state attack against Claude freezelib: a producer could place custody_state=VERIFIED plus output_sha256=UNKNOWN in a self-consistent manifest and have the verifier echo VERIFIED without byte readback. This is a prior-state security failure, preserved in PR #6/merge commit. Fix: input custody vocabulary restricted to STORED_READBACK_VERIFIED, NOT_STORED, UNKNOWN; only actual byte hash/length verification yields output VERIFIED, with adversarial tests. Public CI now allows only the exact-byte public synthetic fixture by path and SHA256 (no generic binary exception), and executes the Claude tests. New freeze successor covers merged PR #5 + PR #6 and this fix. No claims about model performance, signatures or Supabase database snapshot are promoted.

### Adversarial test harness failure, preserved
The first newly authored forged-VERIFIED test supplied a readback callback that returned None for *all* stored atoms, so the verifier correctly failed earlier with STORED_ATOM_MISSING:F001 and the expected error assertion failed (1 failed, 14 passed). Corrected the negative test to serve real stored bytes while leaving the forged remote atom unread, then reran. This is a test-fixture defect, not evidence of accepting a forged custody state.
