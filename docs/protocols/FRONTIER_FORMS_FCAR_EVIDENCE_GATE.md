# Frontier Forms FCAR gate — executable methodology reuse

**Program boundary:** `frontier-forms` only. Vita DAISY/Cloudmer is an independent research program. This implementation copies the **logic of freeze → challenge → replicate → admit**, not a checkpoint, result, dataset, optimizer, FCO or Merkle root.

## What is implemented and what is not

1. **FREEZE — RECORDED, PENDING PI REVIEW.** The frozen 100-synthetic-patient Synthea cohort, deterministic B0, gold oracle, source hashes and output receipts are on the existing Frontier Forms branch. The gate asserts lane IDs and exact source cohort identity, **not** human approval of all gold answers. Supabase source parity is not assumed.
2. **CHALLENGE — EXECUTED DISCOVERY HISTORICALLY.** The FCO and detector LOMO evidence families, paired McNemar results and patient-cluster intervals are in the preexisting training snapshot. The gate checks their presence and reuses the repository's exact-byte snapshot verifier; it does **not** retrain, infer or generate new scores.
3. **REPLICATE — DISTINCT FROM REPLAY.** Repeatable bytes, inclusion roots and checks are evidence of **integrity**. A new, untouched form family with independent oracle and locked patient cohort has **NOT_TESTED** prospective scientific replication. The gate checks this distinction explicitly.
4. **ADMIT — HOLD.** No Frontier Forms claim of superiority can be promoted solely for a positive discovery delta or significant McNemar result. Any `promoted: true`, `SUPPORTED`, `SUPPORTED_GAIN` or `ADMITTED` event is rejected by the current v1 schema. A separately reviewed v2 receipt/PI authorization must be established before that policy can ever permit scientific admission.

## Enforcement

`python3 scripts/check_fcar_admission.py` runs the existing `verify_training_progress.py` verifier, then enforces the program and scientific gates on the current source pointer.

`python3 scripts/check_fcar_admission.py --output evidence/admission/FF_FCAR_GATE_ASSESSMENT_V1.json` writes a **public-safe, append-only** record whose file digests are computed from exact bytes in the current checkout. It refuses modification of an existing assessment file.

The gate explicitly checks:

- Frozen dataset root matches B0, challenge graph and training snapshot
- One and only one `FF-VITA-DAISY-ABSTRACT-ONLY` methodology event
- That event has **NULL** model weights, performance, confidence interval, statistical p-value, and DAISY source root
- No external source program or DAISY checkpoint in scientific event families
- No unsupported scientific `promoted` status
- Historical positive, null, negative and failure records remain present and are not silently promoted

Unit tests inject foreign program data, DAISY weights and performance, altered roots, duplicate IDs and false promotions, verifying a fail-closed response.

## Important limitations

This gate is a **receipt validator**, not an oracle for clinical truth or a theorem that a model improved. It is neither a replacement for the user's DAISY freeze–challenge–replicate–admit pipeline nor proof that a prospective replication occurred. The existing Lean `Admission.lean` is a Boolean formalization, not a new Lean certification of the data or hash implementation. Hashes establish identity; Merkle roots establish integrity; neither establishes causality.

The v1 policy intentionally rejects all promotions, even hypothetical future successfully replicated claims. Extend it in a successor with a verified prospective replication schema, independent gold oracle and human PI signature/authorization; do not loosen it merely to admit a historical discovery result.

## Predecessor

[PR #46 — documented DAISY methodology transfer boundary](https://github.com/biobitworks/frontier-forms/pull/46) is already merged. This is an **implementation successor** that turns its statement into an executable audit, while retaining Vita DAISY as a distinct research program.
