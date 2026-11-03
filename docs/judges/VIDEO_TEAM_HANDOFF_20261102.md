# Frontier Forms — final video/presenter and teammate handoff

**Disposition:** PRESENTATION HANDOFF COMPLETE when this successor merges; SCIENTIFIC ADMISSION=HOLD. **Program:** FRONTIER_FORMS, entirely separate from Vita DAISY/Cloudmer. **Timing:** documentation after the November 2, 2026 4:30 PM Pacific build cutoff. Do not infer the original HackerSquad submission status or timestamp from this file.

**Predecessor chain:** `main@99e4a87d89f7af6f202920aa3ac32a04c4bc543e` (merged PR #83, evidence-lane closeout) → `f409a1defa54c55c9e412b14becf126a75243166` (video entry index pushed) → this append-only handoff successor. The existing [evidence-lane closeout](EVIDENCE_LANE_CLOSEOUT_HANDOFF_20261102.md) is retained unchanged.

## 1. What to open during the video

1. **Primary visual V3:** [`present_v3.html`](present_v3.html) — corrected UTF-8, contributor Gantt, frozen gains, no implication that post-deadline work was judged.
2. **Deep-dive UI:** [Claude vs. ChatGPT comparison](VIDEO_EVIDENCE_STORYBOARD_20261102.html) — cyan independent PI/PM, amber Claude SWE/PM, violet teammates; clickable comparisons, LOMO, Merkle root links, hardware and sponsor tasks.
3. **Navigation and four-minute script:** [VIDEO_REVIEW_ENTRY_20261102.md](VIDEO_REVIEW_ENTRY_20261102.md) and [VIDEO_START_HERE_20261102.md](VIDEO_START_HERE_20261102.md).
4. **Notion team entry:** [VIDEO START HERE](https://app.notion.com/p/40d58ec71eb2815c9911e6952b41fbc9). Sharing/public-access controls are **NOT_VERIFIED** by this handoff.
5. **Figures and raw evidence references:** [judges figure catalog](../FIGURES.md), [100-source-epoch training timeline](FINAL_JUDGE_LANE_TRAINING_TIMELINE_V1.json), [source-bound video result manifest](VIDEO_EVIDENCE_MANIFEST_20261102.json), [all outcomes/negatives ledger](../../evidence/governance/OUTCOMES_AND_PROMOTIONS_20261102_V2.json).

Open **on magicSTUDIObox** in a clean checkout of current merged main; it is not a public deployment:

```bash
git pull --ff-only origin main
python3 -m http.server 8894 --bind 127.0.0.1
open http://127.0.0.1:8894/docs/judges/present_v3.html
# Optional deep dive:
open http://127.0.0.1:8894/docs/judges/VIDEO_EVIDENCE_STORYBOARD_20261102.html
```

**Status distinctions:** GitHub HTML blob URL = code reference, not deployed rendered page. localhost URL = machine-local preview, not teammate-public access. Notion page = shareable review text subject to access controls. GitHub Pages **NOT_VERIFIED**.

## 2. Talk track (four minutes)

| On screen | Evidence statement | Allowed interpretation |
|---|---|---|
| 00:00–00:30 / synthetic protocol | MITRE Synthea FHIR R4 synthetic patients → frozen cohort/B0 → local intake/PDF; open.epic gives interoperability requirements | NO real patient records, production Epic reads or writeback |
| 00:30–01:10 / lanes | Claude built the local workflow and OCR/YOLO challengers; ChatGPT independently challenged custody/statistics; teammates maintain database/API writeback | Attribution only where original commits/receipts support it; mixed actors explicitly MIXED/UNKNOWN |
| 01:10–02:00 / positive findings | Source-bound FCO L1×L3 **18/54 → 30/54**, +22.22 pp, weights unchanged; fitted OCR correction A1 **14/46 → 22/46**, +17.39 pp, Holm p≈0.0234 | Two different endpoints and denominators; discoveries, not generalizable clinical gain or Qwen LoRA improvement |
| 02:00–02:45 / negative controls | Trained YOLO cropping alone **14/46 → 9/46**; local logistic bounding-box validator tied OpenCV **540/540**; RF medium **34/54 vs 54/54** full page boxes | Retain failed and null experiments; do not force model promotion |
| 02:45–03:20 / integrity | Frozen byte hashes → leaf → model answer/FCO → paired McNemar/Holm + patient-cluster bootstrap → Merkle roots and breakpoint | Hash identity ≠ correctness; Merkle integrity ≠ causality; statistical significance ≠ independently replicated model admission |
| 03:20–04:00 / hardware + next | Local Apple Silicon Macs, optional separately run synthetic hosted pilot, sponsor handoff | Do not claim we trained on NVIDIA CUDA or tested Fireworks externally in the private local lane |

## 3. Data, discovery, engineering and scientific admission

| Domain | Current classification | Receipt / limit |
|---|---|---|
| Frozen Synthea source cohort and B0 | **RECORDED / FROZEN_PENDING_PI_REVIEW** | Existing `evidence/forms_b0/B0_FREEZE_V1.json`; original patient records are synthetic, but independent live PostgreSQL parity is not established |
| Local image/form/PDF/Apple OCR and deterministic pipeline | **EXECUTED in predecessor runs** | Historical receipts; this handoff does **not** rerun forms or claim every PDF was visually inspected |
| FCO/FCG L1×L3 data transformation | **DISCOVERY_POSITIVE_ADMITTED**, **SCIENTIFIC_ADMISSION=HOLD** | +12/54 complete forms, post-error-inspection module design; no neural weight change |
| Learned OCR correction A1 | **DISCOVERY_POSITIVE_ADMITTED**, **SCIENTIFIC_ADMISSION=HOLD** | +8/46 complete synthetic images; learned post-correction, not demonstrated Qwen neural fine-tuning |
| YOLO crop and learned box detector rivals | **NEGATIVE / NULL ADMITTED** | 9/46 cropped OCR; logistic tie; RF below OpenCV; retain all failures, including unknown/abstain |
| M0 Qwen2.5-0.5B zero-shot | **NEGATIVE / NO_MODEL_GAIN** | Measured field answers not sufficient for promoted local LoRA result; earlier SFT-1 training stalled under laptop memory pressure |
| SFT adapter/weight promotion | **UNKNOWN/NO_NEW_CHECKPOINT at last prior inspection** | Do not substitute epoch-0 validation, configuration, or a README statement for a new adapter/checkpoint readback |
| Independent prospective new-cohort/form replication | **NOT_TESTED** | Separate untouched patient and layout split plus independent oracle needed |
| PI admission of generalized scientific model superiority | **HOLD / ZERO scientifically supported promotions** | Mandatory FCAR gate, `scripts/check_fcar_admission.py` |
| Video, code and judge figures | **MERGED predecessor; this handoff separate successor** | PR #70, PR #83, V3 merged; GitHub CI statuses are historical rather than rerun by this handoff |

**Distinct DAISY boundary:** Frontier Forms adopts freeze–challenge–replicate–admit methods only. It imports **no** Vita DAISY model weights, training performance, cell datasets, program roots, or promotion decisions.

## 4. Teammate actions and acceptance criteria

| Priority | Responsible lane | Action | Evidence required / state |
|---|---|---|---|
| P0 | **Demo/PI** | Present `present_v3.html` and optionally the detailed actor storyboard. State actual judged submission separately. | Video screenshot or capture timestamp and frozen submitted SHA. Original submission status **UNKNOWN** |
| P0 | **Data steward / teammate** | Confirm exact synthetic FHIR archive/license/manifest and live Supabase snapshot parity. | Authorized read-only consistent snapshot, row/patient IDs, missingness, hashes, canonical source identity. **NOT_TESTED/NOT_VERIFIED** |
| P0 | **Claude SWE/PM** | Provide smallest *actual* patient → source FHIR → passport → form field → PDF golden path with source SHA and field-level predictions; identify missing/failed cases. | Local trace receipt with original bytes, versioned template, full leaf→answer→PDF edge, no real PHI. **NEEDS_INDEPENDENT_VERIFICATION** |
| P0 | **ChatGPT PI/PM reviewer** | Independently test exact same-case outcomes, oracle locking and sign of gains. Preserve negative predecessors. | Paired discordances, patient-cluster confidence bounds, Holm plan, provenance mismatch counters, exact observed root inputs. **PROPOSED** |
| P1 | **Claude model owner** | Report current SFT-1/2/3 status without duplicate training dispatch; preserve stalled/missing checkpoints and memory limits. | Actual log timestamps, adapter sha, training args/dataset split, held-out field answers, LoRA status. **NOT_RECHECKED_THIS_HANDOFF** |
| P1 | **NVIDIA hardware owner** | Benchmark an authorized **synthetic-only** matched model/checkpoint on an actual NVIDIA device with GPU introspection. | GPU model/driver/CUDA/VRAM, Nsight trace, exact source and weight digests, cost, matched outputs. **PROPOSED / NOT_EXECUTED** |
| P1 | **Fireworks API owner** | Continue only separately authorized synthetic-hosted pilot, pin endpoint/version, compare identical cases and measure quality/cost/latency; never export private local records. | Provider request IDs, raw JSON response SHA, fields, time, cost, failure flags; note that public hosted model weight digests may be UNKNOWN. **TEAMMATE PILOT EXISTS; NEXT ROUND DEFERRED** |
| P1 | **Microsoft/GitHub owner** | Add verified signed artifact attestations and least-privilege required CI for published JSON evidence. | GitHub attestation subject SHA and independent `gh attestation verify` receipt. **PROPOSED / NOT_TESTED** |
| P1 | **Research/PI** | Freeze a genuinely untouched prospective cohort and form family, then allow controlled B0/full/LOMO. | Signed protocol/PI permission, frozen gold oracle, predeclared McNemar/bootstrap/critical-field gates, blind replication. **NOT_TESTED** |
| P2 | **Notion/teammates** | Link new result JSON and any verified failures/successors in Notion, with exact GitHub PR and SHA. | State transition recorded and original data retained. **THIS DOCUMENT IS HANDOFF ONLY** |

## 5. Security and reproducibility contract

- Only authorized **synthetic-derived public-safe JSON** and permissible code should be committed in new PRs. Do not add private source PDFs/PNG, model checkpoint weights, real patient records, Epic credentials, Supabase secrets, or live API tokens.
- Distinguish **PROPOSED ≠ IMPLEMENTED ≠ EXECUTED ≠ OBSERVED ≠ SUPPORTED**. Preserve **FAILED, NULL, NEGATIVE, DEFERRED, NOT_TESTED, UNKNOWN, NOT_COMPUTED**. File SHA-256 identifies bytes, not truth or ownership.
- Do not rewrite predecessor roots or statuses; create successors and link to both exact-file digest and Git commit. Old public binaries and disallowed legacy artifacts remain historical; an exemption is not a license to publish new ones.
- Do not infer a training-gain curve from Git PR creation/merge times or from archived historical 30+30 vs later 40 YOLO epoch records. Training runs and epochs have separate sources.
- Do not modify, stop, reconfigure or duplicate-dispatch Vita DAISY jobs. Cloudmer/knots are separate projects.
- Keep post-deadline visualization and new dataset migrations explicitly separate from the submitted competition state; **SUBMISSION_ACCEPTED / VERIFIED_VIDEO_CUTOFF remain UNKNOWN** until independently established.

## 6. Final baton

**Documented lane closed:** video review entry + presenter handoff + exact-byte source index, after commit/push/merge of this successor. **Scientific/operational lanes remain open** for original submission confirmation, golden-path replay, live DB parity, local SFT adapter evidence, new patient/layout replication and sponsor-specific execution.

**Next authorized action:** Teammates can open the linked Notion page and V3 presentation, annotate failures or request independent case-level evidence. Any new observation must be a distinct FCO/FCG successor and public-safe JSON receipt before it is shown as a gain.

**Preserve predecessor:** [PR #70](https://github.com/biobitworks/frontier-forms/pull/70) for video storyboard; [PR #83](https://github.com/biobitworks/frontier-forms/pull/83) for research-lane closeout; [prior handoff](EVIDENCE_LANE_CLOSEOUT_HANDOFF_20261102.md); [read-only evidence root/index](../../evidence/governance/OUTCOMES_AND_PROMOTIONS_20261102_V2.json). This handoff should never claim that PR merges prove a scientific result.
