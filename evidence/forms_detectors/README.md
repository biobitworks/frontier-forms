# Detector benchmark: prebuilt forms with injected errors (run v1)

The preregistration (`data/forms_injected_v1/PREREG.json`, commit 6bae953) was committed before any detector code. It covers 654 synthetic filled forms (218 patient-by-form cases × 3 seeded variants) and 702 injected errors of 8 types. 197 forms are clean.

| Combination | Recall | FP rate (clean fields) | Form sensitivity | Form specificity |
|---|---|---|---|---|
| M1 Merkle breakpoint | 0.162 | 0.000 | 0.236 | 1.000 |
| M2 Lean 4 constraints | 0.268 | 0.001 | 0.365 | 0.995 |
| M3 FCO source binding | 0.989 | 0.041 | 0.998 | 0.706 |
| M1+M2 | 0.426 | 0.001 | 0.525 | 0.995 |
| M1+M3, M2+M3, M1+M2+M3 | 0.989 | 0.041 | 0.998 | 0.70–0.71 |

The per-error-type heatmap is in `run_v1/heatmap.html`, and all single-leaf edges are in `run_v1/DETECTOR_RESULTS_V1.json`.

## What each mechanism contributes
- **M1 Merkle breakpoint** catches 100% of post-seal tampering, points to the exact field and has zero false positives. It needs no source data. It catches nothing that happened before sealing.
- **M2 Lean 4** catches 86% of swapped fields and 65% of dropped required fields, with a 0.1% FP rate. It needs no source data. It cannot catch values that look plausible but are wrong (another patient's value, unit errors, stale vitals, a fabricated "None").
- **M3 source binding** catches nearly everything, because it re-derives every value from the patient passport. The cost is 4.1% of clean fields flagged, which comes from disagreements between the mapping rules and the gold rules. In LOMO it is the only mechanism with a unique gain (+0.563, p≈2e-119). M1 and M2 add nothing once M3 is present.
- **Without source access** (for example, a receiving clinic that only has the form), M1+M2 catch 42.6% of errors at 0.1% FP. Each one adds a significant, attributable gain over the other.

## Caveats
- Errors are defined relative to the oracle, and the passport mostly agrees with the oracle. So M3's recall is close to ceiling by construction. Real-world error sources need a separate test.
- Lean examples are checked with `native_decide`, which trusts the compiler. See `run_v1/LEAN4_RECEIPT.json`.
- Declared deviation: the FP-cost bootstrap used 1000 reps instead of 10000.
