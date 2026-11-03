# Frontier Forms — final judge-facing review of contributors, training and gains

**Status:** post-deadline review successor, synthetic research only. This package does **not** establish that an external HackerSquad form was submitted or that these post-cutoff merges were judged.

## One-click navigation

| Visual or source | Destination | Boundary |
| --- | --- | --- |
| [GitHub README](../../README.md) | Public repository homepage | Two time-series figures and earlier gains/accomplishment heatmaps |
| [Main Notion lab hub](https://app.notion.com/p/40c58ec71eb28161b79ddfbb083cb7c0) | Project-wide lab page | Anonymous Notion sharing not verified |
| [Notion figures](https://app.notion.com/p/40d58ec71eb281db9ba2db19e7f7adf6) | Dedicated gallery | GitHub PNGs are public fallback |
| [Corrected contributor Gantt](figures/fig20_contributor_gantt_corrected_v2.png) | Four attributable/mixed lanes, 63 PRs | PR creation→merge windows, not labor hours |
| [Training/checkpoint chart](figures/fig19_actual_training_epochs_20261102.png) | 40 + 30 + 30 epochs, three distinct runs | Epoch-indexed; V2 per-epoch UTC unavailable |
| [Original captioned figures](FIGURES.md) | Synthetic forms and results | Source PR and statistical evidence |
| [Frozen source record](FINAL_JUDGE_LANE_TRAINING_TIMELINE_V1.json) | Exact PR times, model splits and SHA256 | All source files and PNGs pinned by byte hash |

## Contributors with grounded attribution

| Lane | PRs identified in 63-PR snapshot | Demonstrated scope |
| --- | ---: | --- |
| Teammate/app | 1 | Project/spec and initial Supabase application; other teammate work may be in mixed |
| Claude Code/models | 10 | Synthetic form server, Qwen/vision baselines, YOLO training, fitted OCR post-correction, original screenshots/figure pack |
| ChatGPT/independent | 9 | Independent logistic/RF negative challengers, Holm and patient bootstrap, source/weight custody, admission corrections, judge review |
| Mixed/unknown | 43 | Shared FCO/FCG, freeze/CI/security and integration; GitHub login alone cannot assign an AI author |

These counts describe PR attribution, not person-hours, all teammates, or all work delivered. Teammate API/hosted benchmarks and local Mac training are separate experiments.

## Observed training and model limitations

**V2 local detector, Claude PR #75:** YOLOv8n on MacBookPro/MPS, 40 epochs; 252 training / 38 validation / 108 test synthetic renders. The 40-epoch validation mAP50–95(B) curve is indexed by epoch; no per-epoch V2 UTC is declared. On 36 held-out-layout images: box recall IoU≥0.5 **99.72%**, matched class accuracy **77.99%**, validator false-flag rate **57.63%**, mismatch flag recall **33.33%**. This shows strong field-box localization but unsolved field-value validation. The trained .pt SHA256 is recorded; weights are not published.

**Earlier YOLO detector, Claude/red-team:** 30 checkpoint records each in full and no-scan lanes, all with actual per-epoch UTC and recorded weight SHA. Full arm: 3 GAIN / 3 LOSS / 23 NEUTRAL / 1 FIRST; no-scan: 3 GAIN / 1 LOSS / 25 NEUTRAL / 1 FIRST. The paired development-image curves are on 44 synthetic renders per epoch, not new patient-cluster prospective replication.

**Separate matched discoveries (not YOLO training):** FCO L1×L3 source validation 18/54 → 30/54 synthetic complete forms (+22.22 pp; exact McNemar p=0.000488, Holm p=0.005859). Fitted OCR post-correction table 14/46 → 22/46 synthetic all-seven-field forms (+17.39 pp; exact paired p=0.0078125, Holm p=0.0234375). Neither used a changed Qwen neural checkpoint. YOLO cropping outcomes 9/46 and 15/46 did not demonstrate superiority. The local trained logistic box classifier tied the deterministic contour control 540/540 each. Earlier failures, neutral and null records remain preserved.

**Qwen LoRA:** Earlier frozen longitudinal tracker observed epoch-zero validation loss without a complete matched before/after adapted-checkpoint comparison. Thus LoRA performance superiority NOT_COMPUTED. No Vita DAISY weights, datasets or metrics were imported; only its freeze–challenge–replicate–admit method informed evidence gates.

## Time, lineage and evidence limits

The frozen GitHub source JSON comprises 63 observed PRs at 2026-11-03T00:38:48Z, after the Fireworks event cutoff on November 2 at 4:30 PM Pacific. This is a **review successor**; exact prize-eligible submitted commit and external HackerSquad acceptance receipt remain UNKNOWN.

The first produced Gantt showed 0 mixed-lane PRs despite source events containing 43; this is preserved as **FAILED_DISPLAY_LABEL_MISMATCH** in fig18 and the V1 source. The corrected Gantt figure 20 and V2 correction receipt preserve predecessor SHA, corrected SHA and full source PR counts. Training figure 19 was separately visually inspected; no training source was changed by this correction.

Run the standard-library, source-byte verifier: python3 scripts/build_judge_final_timeline.py. It independently verifies original and corrected PNG SHA256, PR counts, actual training source hashes, and synthetic disclosure. SHA/Merkle proves receipt identity, not model efficacy. **Scientifically independently replicated promotions: 0 (FCAR HOLD)**; real PHI, Epic writeback, independent external patient validation and HackerSquad submission state remain NOT_TESTED/UNKNOWN.
