# Frontier Forms observed gains and DAISY attribution boundary

Status: REPOSITORY-EVIDENCE REVIEW, not new experiment or independent replay. Parent: PR #46 merge 01b5bc1a9d239780d245b771155fe5b344127c06.

## Direct answer
YES: a Frontier Forms deterministic FCO/FCG module combination produced a recorded paired discovery gain. NO: this does not measure a gain attributable to Vita DAISY weights, training, optimizer or freeze–challenge–replicate–admit framework itself. The framework provides evidence discipline, not a performance intervention.

## Concrete positive paired record
Source: dashboard/training_progress_latest.json, event FF-LOMO-B0+L3-to-B0+L1+L3. On 18 synthetic patients × 3 forms (54 matched cases), parent B0+L3 had 18/54 full-form successes; child B0+L1+L3 had 30/54. Paired table: both correct 18; both wrong 24; baseline-only 0; challenger-only 12. Difference +12/54 = +0.2222222 (22.22 percentage points). Exact two-sided McNemar p=0.00048828125; Holm-adjusted p=0.005859375 across 12 FCO LOMO edges; 10,000 patient-cluster bootstrap CI [0.0741, 0.3704]. Source graph root as reported in the event: 43684d54e9c21c968b05d789dcceb91e2eb7d730cb3a948d669d0f82fb4facfc. Source file SHA256 as reported: 90b06b191b87fe7eb2a89624f8a3d4b7814b6928d38a367020ccd07a4845524d. These hashes are quoted from the source record, NOT recomputed by this documentation action.

Model identity: deterministic FCO/FCG rules; neural weights unchanged; model_weights_sha256=null, not an actual neural weight hash. Intervention L1_evidence_abstain conditional on L3_clinical_filter; NOT a standalone L1 effect. Standalone L1/L2/L3 additions and several LOMO edges are zero/ties. The original test failures informed rule design, so this is discovery-only, promoted=false, replication NOT_TESTED. No clinical efficacy, prospective generalization or causal DAISY contribution established.

## Other lanes
- Detector LOMO: 702 seeded error instances; endpoint error recall, not clinical full-form accuracy. Preserve negative/tie and false-positive cost.
- Random Forest training-size comparison: separate fitted weights at 10/30/63 patients, not a continued DAISY training trajectory; repository method notes no positive claim.
- Qwen LoRA: validation loss alone cannot establish held-out form gain; paired checkpoint inference NOT_TESTED in the initial method snapshot.
- Vita DAISY: methodology_only, status NOT_COMPUTED, no shared weights, performance metrics, source roots or imported cell datasets.

## Admission next step
Prospective patient/template-disjoint synthetic holdout, frozen pre-registered oracle and arms, independent paired McNemar and patient-cluster bootstrap, exact-byte source/weight/root receipts. Only then consider promoting an FCO gain. DAISY-specific performance delta stays NULL/NOT_COMPUTED.
