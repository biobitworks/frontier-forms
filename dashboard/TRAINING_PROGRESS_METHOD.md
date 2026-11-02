# Frontier Forms longitudinal checkpoint × Merkle × LOMO statistical view

## Access

From the repository root:

    python3 scripts/verify_training_progress.py
    python3 -m http.server 8787 --bind 127.0.0.1

Open http://127.0.0.1:8787/dashboard/training_progress.html.

The dashboard loads the mutable view pointer dashboard/training_progress_latest.json and shows exact immutable event snapshots under evidence/training_progress/OBS-.../. No CDN, external analytics or hosted model calls. GitHub reviewers can inspect the JSON even without the local server.

## Correct interpretation

1. **Actual training curve:** Qwen2.5-0.5B-Instruct LoRA rank 16, lr 2e-4. Only observed validation-loss epochs appear in this chart, and training steps appear only when the trainer actually logs them. A new adapter model must be checked by exact local weight hashes and **paired held-out inference**, not by loss alone. Epoch 0 is the pre-training validation baseline and **does not have learned adapter weights**.
2. **FCO LOMO effect:** Hold model weights fixed; compare a single added/removed leaf with exact matched patient×form outcomes. Display full-form correctness, exact two-sided McNemar and **10,000 patient-cluster bootstrap** intervals. Treat case-level p as descriptive because forms repeat by patient. Use Holm adjusted p across the 12 tested edges. Rule design saw the test failures, so even positive p/CI is discovery, NOT promotion.
3. **Error-detector LOMO:** 702 synthetic seeded error instances (not independent patients). Show detection recall with exact McNemar, error-type-stratified intervals and Holm correction over 6 tested edges; patient cluster CI NOT_COMPUTED. Source binding adds false-positive cost. Not comparable to neural SFT accuracy.
4. **Learning sample-size comparison:** 10/30/63 synthetic training patients, different Random Forest fitted weights, same 18 test patients. This is cross-sectional sample-size sensitivity—not a longitudinal model whose weights continued from tiny to medium. Plot F1 and patient-cluster full-page paired CIs separately, with no positive claim. Checkpoint and Merkle identities are pinned to each branch.
5. **Separate program:** Vita DAISY's hierarchy of frozen source to candidate to challenger to admission to replicability is a useful abstract workflow, not a shared training dataset, optimizer, root, or FCO gain. Its program output remains NOT_COMPUTED in Frontier Forms.

## Update when a new actual checkpoint or log line arrives

When the local training log and/or adapter checkpoint changes:

    python3 scripts/snapshot_training_progress.py --training-log /path/to/authorized/local/runs/forms_sft_v1.log
    python3 scripts/verify_training_progress.py

Each invocation writes a new append-only OBS directory with a separately computed exact-byte Merkle root and a predecessor root pointer. Earlier snapshots, including failed experiments/corrective successors, are never overwritten. Only the latest view pointer is updated; Git commits / PRs and the Notion log are separate publication steps. The script never uploads any model weights, raw images, PDF, PHI, secrets or network requests.

For an actually trained model checkpoint, evaluate the same frozen patient/test forms and raw field answers with the exact harness; then invoke scripts/compare_paired_checkpoints.py with both scored output JSONLs and actual weight SHA256. The scorer refuses unequal cases, invalid weight IDs or collision with prior append-only output. A comparison is not admitted until model checkpoint and adapter SHA, prompt/parser/oracle, FCG leaf set, patient disjointness, matched case digest, output root and independent replication are verified.

### Scope of immutability

Each committed OBS snapshot contains events.jsonl and manifest.json with a computed leaf/root scheme. dashboard/training_progress_latest.json is a replaceable projection pointer and must not be used as a canonical root. FCO and model-weight roots use distinct declared schemes; they cannot be numerically compared as delta performance.

### Audit repairs, preserved

- First verifier FAILED when it compared rounded synthetic-detector gains with exact paired fractions. A successor uses fractions from paired tables and preserves the source rounded value.
- Initial independent Random Forest root comparison FAILED due to missing the documented canonical trailing newline. Corrected roots for all three training-size experiments were independently recomputed, with failure preserved.
- The first paired-checkpoint demo used a descriptive value under a model_weights_sha256 key. Successor V2 explicitly sets weights NOT_APPLICABLE for deterministic FCO rules, preserving the previous receipt and marking it invalid for model-weight provenance.

### Remaining blockers

- No epoch-1 or epoch-2 Qwen LoRA validation receipt, adapter SHA, paired frozen held-out SFT result or independent template holdout observed at initial snapshot.
- No unbiased estimate of gains from L1/L3; the old test cases were seen during development.
- Clinical accuracy and PDF/OCR generalization must be evaluated on separately pinned synthetic cohorts and unseen templates.
- The separately reported Supabase data are not automatically the source of truth for this cohort; no live database row count or frozen database Merkle root was computed.
