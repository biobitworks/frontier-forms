# Frontier Forms — Fireworks: Deploy submission and judging packet (2026-11-02)

> Submission-ready narrative, **not proof of form submission or Fireworks eligibility**. Source: GitHub PRs #12, #29, #46, #48, #49, #50, #51 and frozen dashboard records. The provided Forge Deploy sample Notion URL was NOT_FOUND to the connected workspace; this packet follows the user's supplied submission/rubric template rather than claiming to reproduce inaccessible page layout.

## 1. Project form

**Project name:** Frontier Forms — Evidence-Gated Synthetic Healthcare Form Filling

**Public repository:** https://github.com/biobitworks/frontier-forms

**Description:** A local-first, synthetic-only research system that maps structured synthetic healthcare records into registration, medication/allergy, and urgent-care forms. It pairs form-field extraction (Apple Vision OCR, local Qwen vision/text and YOLOv8n box detection) with deterministic source-bound FCO/FCG validation, independent oracle scoring, Merkle provenance, and factorial leave-one-module-out (LOMO) evaluation. It abstains or challenges unsupported field assertions rather than silently fabricating answers. Not a clinical deployment.

**Intended users:** Healthcare intake automation researchers, medical-form workflow developers, privacy/security reviewers, and evaluators testing reliability of form-filling agents. Real-world clinical use NOT_TESTED.

**Task:** Given a synthetic patient record and a form template, fill the required fields correctly while preserving source provenance and detecting unsupported or erroneous entries.

**Why it matters:** Form filling combines OCR, entity mapping, unit conversion and safety-sensitive source binding. The prototype makes errors and evidence traceable. Staff time savings, ROI, clinical safety and deployment economics NOT_COMPUTED.

**Technologies reported in PRs:** Python, MITRE Synthea synthetic records, FHIR/passport mapping, HTML/local HTTP form server, Apple Vision/PDFKit, local Qwen (qwen2.5vl:3b, qwen2.5:1.5b, qwen3:1.7b), YOLOv8n detector, RandomForestClassifier for box validation, Lean 4 source/admission checks, SHA-256/Merkle commitments, paired McNemar, Holm-Bonferroni and patient-cluster bootstrap, GitHub Actions. Exact setup/model availability must be checked against repository and hardware.

**Fireworks requirement:** FIREWORKS_EXECUTION_NOT_VERIFIED. Existing PR #12 explicitly states external Fireworks/NVIDIA inference NOT_TESTED; local-only synthetic privacy policy must not be described as Fireworks usage. Prize eligibility UNKNOWN / potentially BLOCKED until an actual permitted Fireworks use receipt exists and organizers confirm.

**Team roster:** UNKNOWN; confirm names and required fields in project form. Do not invent teammates.

## 2. Before and after: benchmark evidence

**Primary documented paired discovery comparison:** deterministic B0+L3 clinical filter vs B0+L1+L3 evidence-abstention + clinical filter; same 18 synthetic patients × 3 forms = 54 patient-form cases. Full-form required-field correctness: 18/54 (33.33%) baseline vs 30/54 (55.56%) challenger; 12 challenger-only improvements, zero baseline-only; +22.22 percentage points. Exact two-sided McNemar p=0.00048828125; Holm-adjusted p=0.005859375 (12 FCO edges); 10,000 patient-cluster bootstrap 95% CI [+0.0741,+0.3704]. Existing event FF-LOMO-B0+L3-to-B0+L1+L3 in dashboard/training_progress_latest.json. Recorded source graph root 43684d54e9c21c968b05d789dcceb91e2eb7d730cb3a948d669d0f82fb4facfc (NOT recomputed here). Neural weights unchanged; effect is conditional on L3. Discovery only because rules were designed after inspecting these test failures; independent prospective replication NOT_TESTED; promoted=false. Not a named frontier-model baseline comparison.

**Additional evidence:** 100-patient synthetic frozen cohort and 218 forms in earlier baseline receipts; 16 factorial synthetic fault-injection module combinations across 10/30/100 patient cohorts (PR #12); 702 seeded error instances in detector LOMO (distinct metric, not independent patients); PR #12 reports local Apple Vision 8/8 field extraction and local Qwen model 8/8 on a single synthetic PDF with different modalities, not a comparative model superiority claim. PR #51 reports an adverse OCR overlay result: Apple OCR 58/70 clean vs 0/70 with boxes drawn over 10 forms; run OCR on clean renders. These denominators and endpoints must not be combined.

**Baseline model for rubric:** NAMED_FRONTIER_MODEL_NOT_ESTABLISHED. Deterministic B0 is a rules baseline, not a frontier model. No defensible claim of frontier-model advantage or Fireworks cost/latency advantage. Latency observations on differing modalities cannot support like-for-like speedups. Prospective 100+ matched held-out cases NOT_TESTED.

**Tradeoffs and failure modes:** unsupported allergy assertions; clinical finding vs social-history confusion; kg/lb mapping; PDF field truncation; overlay boxes damaging OCR; patient dependence; potential template leakage; false-positive cost of source-binding detectors; 123 unchanged historical non-JSON blobs grandfathered by the later JSON-only publication policy. No clinical or patient data.

## 3. Demo under 120 seconds — storyboard (PROPOSED, not recorded)

0–10s: State problem: form filling must be correct and source-grounded, not merely fluent.
10–25s: Show one synthetic record and local form server; identify clean image and box overlay as separate visualization layers.
25–45s: Demonstrate actual local Qwen/Apple OCR field answers and deterministic source-binding checks. Do not claim Fireworks inference.
45–65s: Show matched B0+L3 vs B0+L1+L3 outcomes: 18/54 to 30/54; p-value and discovery-only caveat.
65–80s: Show Merkle × LOMO evidence-state heatmap and drill-down to hashes, source leaf, field and oracle.
80–95s: Show the negative OCR box-overlay failure (58/70 to 0/70) and why clean-image OCR is necessary.
95–110s: State limitations: no independent prospective validation, no verified Fireworks run, no clinical deployment.
110–120s: Repository, setup, evaluation commands and next experiment.
**Video URL:** NOT_PROVIDED. **Recorded/uploaded/processed:** NOT_VERIFIED.

## 4. Judging rubric — evidence-oriented self-audit (NOT organizer scores)

| Criterion | Weight | What can be shown | Gap |
| --- | ---: | --- | --- |
| Benchmark evaluation | 40% | 54-case matched FCO discovery, McNemar/cluster CI; factorial and local model receipts | No named frontier baseline, no verified Fireworks run, no prospective 100+ matched benchmark |
| Business value | 25% | Clear intake-form workflow and source-grounding benefit | Time/cost savings and adoption barriers not quantified |
| Technical execution | 20% | Local server, OCR/vision/field mapping, independent oracle, hashes, LOMO, Lean gates | Cross-machine reproduction and production readiness unverified |
| Presentation | 10% | Judge figures/heatmaps in PR #50/#51 and demo assets | Final <=120s accessible video not verified |
| Documentation | 5% | README, scripts, methods, PR inventory, reproducibility artifacts | Verify clean setup and public link permissions |

**Round 2:** rubric UNKNOWN; organizer confirmation required.

## 5. Deadline and final submission checklist

**User-supplied deadline:** 2026-11-02 16:30 PST. Start form by 15:30; aim to finish by 16:00 PST. Upload must finish processing before 16:30 PST. Do not claim on-time submission from repository activity.

- [ ] Confirm project form and actual submission URL; complete project name, description, repository, technologies, roster.
- [ ] Verify repo public and judge instructions; verify test/setup on clean environment.
- [ ] Record and upload final <120-second video; open video link anonymously and confirm processing.
- [ ] Disclose Fireworks eligibility blocker; do not claim use absent receipts.
- [ ] Click **Submit for judging**, not merely Save; independently confirm status **Submitted**.
- [ ] Save subsequent updates only after successful submission, as permitted by organizer.

## 6. Source links and responsibilities

- PR #12: https://github.com/biobitworks/frontier-forms/pull/12 — synthetic factorial and local OCR/Qwen receipt claims.
- PR #48: https://github.com/biobitworks/frontier-forms/pull/48 — FCO paired gain attribution.
- PR #49: https://github.com/biobitworks/frontier-forms/pull/49 — freeze/challenge/replicate/admit gate, hold on scientific promotion.
- PR #50: https://github.com/biobitworks/frontier-forms/pull/50 — Claude-authored status figures and judge labels.
- PR #51: https://github.com/biobitworks/frontier-forms/pull/51 — Claude-authored judge pack and local form server demo evidence.
- This submission packet: ChatGPT-authored rubric mapping, not a new benchmark, not a claim of Claude's experiments as ChatGPT executions.

## TURN_BREAKPOINT
ID=FF-FIREWORKS-SUBMISSION-PACKET-20261102; PARENT=FF-GAIN-ATTRIBUTION-20261102; VERIFIED_NEW=source PR metadata and submission packet; EXECUTED=GitHub/Notion source review and documentation publication; OBSERVED=PR-reported results only; DECISIONS=honest discovery ceiling and Fireworks eligibility flag; PROPOSED=demo and actual form submission; NOT_TESTED=Fireworks execution, frontier baseline, 100+ prospective cases, uploaded video, submitted status; FAILURES=sample Notion template NOT_FOUND; UNRESOLVED=team roster, final video, form, eligibility; NEXT_ACTION=verify submission form and upload/submit before deadline.
