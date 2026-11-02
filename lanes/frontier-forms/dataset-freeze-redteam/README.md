# Lane `frontier-forms`: dataset-freeze red team (method package)

This is an independent method lane, so teammates can compare their freeze and red-team approach against it. **Everything here is synthetic and public-safe.** The private application of this method (to a non-public research dataset) lives in a private repository and is summarized only at the end of this file. No private data, receipts, hashes of private files, model weights or credentials are included.

## What the method does

1. **Freeze contract.** Every file becomes an *atom*: `source_id → content_sha256 → occurrence_id → transform_id → output_sha256 → partition_id → dataset_version → consuming_run`, plus `custody_state`, `rights_assertion_id`, and a `reported_sha256` that is kept as a citation only. Bytes that were not actually read are recorded as `NOT_STORED` with `content_sha256 = UNKNOWN`. A remote checksum is never treated as custody.
2. **Merkle tree.** `leaf = sha256(0x00 ‖ canonical_json(leaf))`, `node = sha256(0x01 ‖ left_hex ‖ right_hex)`, split at the largest power of two below n (RFC 6962 shape), leaves ordered by `atom_id`. Canonical JSON is sorted keys, compact separators, UTF-8 with no ASCII escaping, plus a trailing `\n`. Each atom carries an audit path.
3. **Red team.** Three verifiers face the same attacks:
   - *INCUMBENT* is a common training-kernel input check: filename, gene count, batch-split equality, and SHA-256 of **positional** row-index lists. File size is recorded but never compared.
   - *BASELINE* is the git/SQLite-style whole-file hash plus a linear hash chain.
   - *SUCCESSOR (BINDING_V2)* hashes the input bytes at consumption, binds gene names, and hashes per-row content per partition.
4. **Admission rule.** A freeze is admitted only if source identity, rights, data integrity, split isolation, reproducibility, custody readback and independent verification all PASS. NOT_TESTED, UNKNOWN and BLOCKED are never PASS. A model-vote majority never overrides a deterministic failure. In the private lane this rule is also encoded and CI-checked in Lean 4.
5. **Independence.** The independent verifier must be a separate implementation written from the recipe text alone (separate agent, different hashing path). Lanes that ran sequentially are labelled sequential.

## Run it

```bash
python3 tools/public_redteam.py --out results/   # 30 challenges, deterministic except IM01
python3 -m pytest -q tests/                       # 13 tests
```

Expected: synthetic freeze root `a10240801c05e0121bf6ec6f3ad07cae4073e2a3f7d0e88205a8ef67986ce4a5`, results root `616c520155071ec99849d7a15576bfb923a4cba966104dd918cfd7bf228e2383`. The IM01 probe depends on the machine; as root, file modes are not enforced.

## Results on synthetic data (`results/REDTEAM_TEST_MATRIX.csv`)

| Attack | Incumbent | BINDING_V2 | Whole-file hash / chain |
|---|---|---|---|
| Same-size byte edit, row reorder, gene reorder, gene rename, holdout content copied into train, label switch (RT01–04, 08, 11) | **undetected** | detected | detected |
| Batch-ID swap, duplicate or missing record, batch placed in two partitions (RT05–07, 09) | detected | detected | detected |
| Target identity shared across batch-level partitions (RT10) | 12/12 overlap, unguarded | reported | n/a |
| Byte drift, TOCTOU, leaf substitution, missing or reordered leaf, reused occurrence id, duplicate atom, false root, remote checksum promoted to custody (MK01–10) | rejected by the manifest verifier | same | — |
| Forked history, rollback to an older valid prefix (MK12–13) | **accepted** without a pinned root | rejected with a pinned root | also undetected without an external anchor |
| Duplicate admission, self-claimed independence, "signed" with no signature (AD01–03) | no gate | rejected by the proposed gate | — |

What the Merkle design adds over a plain whole-file hash and hash chain, **as demonstrated here**: per-leaf failure localisation and O(log n) inclusion proofs. What it does **not** add: detection of fork or rollback. That needs a root pinned in a reviewed commit or an external anchor, for Merkle and hash chain alike.

**Observed limitation:** an inclusion proof checked against a *claimed* tree size still verifies when the wrong size gives the same audit-path shape (index 0, size 7 vs 8). Pin `leaf_count` together with the root.

## Private application (summary only)

Applied on 2026-11-02 to a private VCC-2025-proxy training lane, the result was **HOLD: partial freeze, not admitted**. Protocol and evidence files were frozen and independently re-verified (root MATCH). Source data bytes could not be read from the cloud environment and stay NOT_STORED. The incumbent kernel's input binding showed the same six undetected attacks as above. Early stopping and the gain gate used the same validation rows. The rights gate did not block. Model-based lanes (Qwen3-1.7B, Qwen3.8-27B, JEV/Fireworks) were BLOCKED, with no endpoint or credential reachable, and none were simulated.

## Files and digests

- dc3c1bc09da6739368be558dd881e2f53ca494a0ae630c6a42e61d297d1c4648  `tools/fixture_attacks.py`
- 416060c5dfd3e0bba3a715e07c68281950cae1fc54c23fec85f890c52d44399f  `tools/freezelib.py`
- 880836e23ae852282b7631de62267cc27baa0f4c6cbbaaccf4c9a46a2f0fd225  `tools/public_redteam.py`
- 6dcb568dfa631b1030f7e47d1f36029681986becee314f006c25e3739f2421b5  `fixtures/synthetic_pseudobulk_v1.bin`
- 0d25fe58ed2c1f37553237a0e9c77a2be47e8734e4537c1a860d8db911764ec2  `results/REDTEAM_TEST_MATRIX.csv`
- d69935502258261162aa79b078115dcdd12f04e931d2adc3896667c77bb094b3  `results/RESULTS.json`
