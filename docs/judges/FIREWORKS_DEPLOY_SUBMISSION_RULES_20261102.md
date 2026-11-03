# Fireworks: Deploy — rules-based submission and judging checklist (2026-11-02)

Source: event rules and submission rubric supplied by PI. **This document is a post-fact compliance record unless its commit was included in the submitted frozen SHA before 2026-11-02 16:30 PST. It is NOT permission to modify a judged artifact after deadline.** The organizer's sample Notion page was inaccessible to the integration; this document follows the pasted template, not an unverified copy of that page.

## Submission fields
- **Project name:** Frontier Forms — provenance-gated synthetic clinical form autofill
- **Repository:** https://github.com/biobitworks/frontier-forms (public accessibility in signed-out browser NOT_TESTED)
- **Task:** extract and validate values from synthetic health records and form images into form fields with source-aware abstention and deterministic audit trail.
- **User:** healthcare intake, clinical operations, and interoperability engineering teams; **research prototype only**, not production clinical deployment.
- **Approach:** Synthea synthetic cohort, read-only FHIR/passport, HTML/HTTP echo, Apple Vision OCR, local Qwen and field-box detectors, deterministic FCO/FCG evidence validation, Merkle and LOMO receipts.
- **Technologies:** Python, GitHub Actions, MITRE Synthea, FHIR, Apple Vision, local Qwen, YOLOv8n, RandomForest, Lean 4, JSON and Merkle receipts. Fireworks inference use NOT_VERIFIED; do not list as used without receipts.
- **Team roster:** UNKNOWN; verify 2–5 registered, in-person checked-in contributors; one team only; at least one present for awards.
- **Video:** URL UNKNOWN; must be under 120 seconds, processed and publicly accessible before deadline.
- **Submission form:** draft/saved/submitted status UNKNOWN; saving is not submission.
- **Submitted SHA:** UNKNOWN; record immutable SHA and submission timestamp, verify before deadline.
- **Sponsor tracks:** UNKNOWN; Fireworks-use receipts required if claiming sponsor-specific awards.

## Before / after evaluation
- **Dataset:** synthetic Synthea, recorded 18 patients × 3 forms = 54 paired cases for FCO LOMO discovery; larger synthetic sets exist but not equivalent frontier-baseline holdouts.
- **Compared systems:** deterministic B0+L3 vs B0+L1+L3, neural weights unchanged.
- **Metric:** required-field full-form success.
- **Baseline:** 18/54 = 33.33%; **challenger:** 30/54 = 55.56%; **delta:** +12/54 = +22.22 percentage points.
- **Paired statistics:** exact two-sided McNemar 0.00048828125; Holm-adjusted 0.005859375 (12 edges); 10,000 patient-cluster bootstrap CI [0.0741, 0.3704].
- **Tradeoffs:** abstention/false-positive costs; clean-image Apple OCR degraded from 58/70 to 0/70 on boxed overlays in PR #51; overlay must not be fed back into OCR.
- **Evidence ceiling:** discovery only; rules designed after viewing original failures; independent prospective replication NOT_TESTED; no clinical generalization.
- **MANDATORY FRONTIER BASELINE:** named frontier model, model/version/config, identical held-out cases, same scoring, quality/cost/latency and uncertainty NOT_VERIFIED. Existing B0 is NOT a frontier-model baseline. Do not claim rubric compliance.
- **DAISY:** methodology reused for freeze/challenge/replicate/admit; no DAISY weights, results or roots imported; DAISY-specific gain NOT_COMPUTED.

## Judge-facing navigation
- README.md
- docs/judges/WHAT_WE_DID_AND_NEXT.md and docs/judges/FIGURES.md (PR #51; verify merge and exact SHA)
- docs/figures/FIGURES.md (PR #50; verify merge and exact SHA)
- dashboard/training_progress.html and dashboard/TRAINING_PROGRESS_METHOD.md
- experiments/form_error_factorial/heatmap.html
- docs/architecture/FRONTIER_FORMS_GAINS_ATTRIBUTION_20261102.md (PR #48)
- docs/architecture/DAISY_METHOD_TRANSFER_BOUNDARY_20261102.md (PR #46)
- scripts/check_fcar_admission.py and evidence/admission/FF_FCAR_GATE_ASSESSMENT_V1.json (PR #49)
- scripts/redteam/form_server.py (PR #51; confirm landed)

## Rubric (100%)
1. **Benchmark evaluation 40%:** currently BLOCKED for frontier-model matched held-out comparison; no invented result.
2. **Business value 25%:** clear healthcare-intake user and error-reduction hypothesis; quantified production time/cost savings NOT_COMPUTED.
3. **Technical execution 20%:** working local pipeline and provenance/LOMO experiments reported; identify which PRs were pre-existing versus built on Nov 2.
4. **Presentation 10%:** final <120s video and publicly working URL NOT_VERIFIED.
5. **Documentation 5%:** setup, run commands, dependencies, model IDs, sources, results and limitations; clean-room reproduction NOT_TESTED.

## Event eligibility and deadline
- Nov 2, 2026, TERRA, 511 Harrison St, SF; build 10:30–16:30 PST; start submission by 15:30, aim 16:00.
- All participants approved, physically checked in; 2–5 members; one team per person; one submission per team; finalist in-person presentation; one member at awards.
- Public repo accessible signed-out. No PHI, secrets, private weights or unlicensed data.
- Stop developing at 16:30. Upload processing must complete before deadline. Freeze submitted Git SHA; no feature or evaluation replacements after cutoff.
- General event rule says Fireworks infrastructure optional; prize listing supplied separately says Fireworks required for listed awards. **CONFLICT: request organizer determination, do not presume eligibility.**
- Code of conduct and builder support URLs are TODO in provided rules; UNKNOWN.
- Round 2 detailed rubric unpublished.
- AI assistants and all pre-existing project work must be credited, with event-day changes distinguished.

## Final form verification ledger
| Gate | State |
|---|---|
| 2–5 registered and checked in | UNKNOWN |
| Team roster complete | UNKNOWN |
| Named frontier-model baseline and same-case comparison | NOT_VERIFIED |
| 100+ held-out varied cases | NOT_VERIFIED |
| Public repo signed-out accessibility | NOT_TESTED |
| Reproducible setup and judge figure links | PARTIALLY_IMPLEMENTED |
| Demo video <120 seconds accessible and processed | UNKNOWN |
| Submitted commit SHA before deadline | UNKNOWN |
| Sponsor Fireworks use receipt | NOT_VERIFIED |
| Form marked submitted, not draft | UNKNOWN |

**Do not label submission COMPLETE until the form itself confirms submitted and timestamped.**
