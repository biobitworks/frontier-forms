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
