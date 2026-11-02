# Frontier Forms — synthetic error-factorial / LOMO discovery protocol

**Status:** DISCOVERY / CONTROLLED_FAULT_INJECTION. **Parent:** `biobitworks/frontier-forms` PR #10 HEAD `8a8053ed19f53d74055ae88e748a1f6ed1f88d2b` (at branch creation). This is an independent stacked successor, not a replacement for Claude's B0 or historical work. All 100 synthetic FHIR subset patient bytes are read-only and checked against PR #10's `MANIFEST.json`. **No real PHI or Epic writes.**

## Existing reasons to build the challenge

- The Synthea names legitimately mix letters and digits (`Lanny564`, `Volkman526`). Truncating digits is incorrect.
- OCR may confuse letters `O/l` and digits `0/1`; the numeric suffix must remain unchanged.
- ZIP/postal codes require string semantics, especially `00000` and `02110`.
- A field from a different synthetic patient is wrong even when syntactically valid.
- A clean control must not be modified by correction logic.

## Frozen design (controlled synthetic example, not a clinical benchmark)

Five synthetic form challenge types: `name_suffix`, `ocr_confusable`, `postcode`, `patient_bind`, and `clean`. Four corresponding isolated deterministic correction modules. Enumerate all `2^4 = 16` enabled-module masks (B0, singletons, pairs, triples, full), and compare each mask with B0, full, and every attack stratum. Each module is a permissive source-bound repair using the **same authorized source patient passport**; the attack type and gold answer are NOT arguments to the module. Gold is separately extracted from the pinned FHIR source.

**Sample sizes:** tiny 10, small 30, medium 100 synthetic patients. These sizes are scaled tests of the *same synthetic fault model*, **not independently randomized replications** or different-sized model checkpoints. The 100-patient source was already visible during original PR #10 design, so this is discovery-only. A genuine prospective test needs a newly generated, separately held-out Synthea cohort, prespecified after this discovery and locked before models are tuned.

### Metrics and limitations

For every module mask: accuracy per corrupted synthetic form field; paired delta versus injected B0 and full; exact two-sided McNemar with discordance counts on each **attack type**, where there is at most one case per patient; patient-cluster paired bootstrap (2,000 resamples, seed 20261102) for 95% intervals. Pooled McNemar p-values are recorded only as descriptive because multiple case rows per patient are correlated.

**AUROC:** NOT_COMPUTED until an independently produced continuous error-risk score exists; do not derive AUROC from these deterministic repair flags. Correct-by-construction synthetic repairs are **not** evidence of fine-tuning or model superiority.

**Primary scientific admission:** NO_PROMOTION. Synthetic design generates the specific faults the modules repair. Even strong p-values represent fault-injection regression coverage, not generalization.

### FCO/FCG provenance

Source `MANIFEST.json` byte SHA-256 → occurrence source SHA-256 → deterministic challenge case → challenge-leaf SHA-256 → challenge root → module-mask variant/prediction SHA-256 → variant result Merkle root → paired McNemar/bootstrap → claim ceiling DISCOVERY.

**Canonical recipe:** `SHA256(UTF8('FF_ERROR_LEAF_V1') + 0x00 + canonical_UTF8_JSON_with_LF)`; parents `SHA256('FF_ERROR_NODE_V1' + 0x00 + raw_left_digest + raw_right_digest)`; unpaired last digest carried without duplicate, sorted case generation by ascending patient ID then predetermined attack order. Merkle root proves bytes under this recipe, not clinical truth or causality. A repair creates a new successor; do not overwrite previous results.

### Lean 4

`FixtureInvariants.lean` checks the Boolean fault model and fail-closed source admission. It **does not** prove actual SHA-256 cryptographic correctness or that predicted values are clinically accurate.

### Historical regression (preserved)

The preliminary 10-patient implementation repaired 40 of 44 cases. Four failures exposed incorrect handling of the legitimate digits in family names and a `00000` postal code. The repaired implementation is a successor. This statement records observed first-run behavior; the preliminary report is kept in the audit log, not silently reclassified as PASS.

## Run and verify

```bash
python3 -m unittest discover -s tests -p 'test_form_error_factorial.py' -v
$HOME/.elan/bin/lean experiments/form_error_factorial/FixtureInvariants.lean
python3 experiments/form_error_factorial/run.py --cohort data/forms_cohort_v1 --out experiments/form_error_factorial/results/tiny --size 10
python3 experiments/form_error_factorial/run.py --cohort data/forms_cohort_v1 --out experiments/form_error_factorial/results/small --size 30
python3 experiments/form_error_factorial/run.py --cohort data/forms_cohort_v1 --out experiments/form_error_factorial/results/medium --size 100
```

Do not merge PR #10 or its stacked successor while scientific gold rules, non-production security, and independent review remain unresolved.
