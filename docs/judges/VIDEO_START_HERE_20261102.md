# Frontier Forms — video start here
**Presentation and evidence handoff · November 2, 2026 (Pacific) · synthetic data only**

## Open on magicSTUDIObox for the recording

From a checkout of `biobitworks/frontier-forms` at the published PR/merge commit:

```bash
cd /path/to/frontier-forms
python3 -m http.server 8787 --bind 127.0.0.1
# On this same Mac:
open http://127.0.0.1:8787/docs/judges/VIDEO_EVIDENCE_STORYBOARD_20261102.html
```

**[Presentation source in GitHub](https://github.com/biobitworks/frontier-forms/blob/main/docs/judges/VIDEO_EVIDENCE_STORYBOARD_20261102.html)** · **[Exact source-linked JSON](https://github.com/biobitworks/frontier-forms/blob/main/docs/judges/VIDEO_EVIDENCE_MANIFEST_20261102.json)** · **[Original judge figure catalog](https://github.com/biobitworks/frontier-forms/blob/main/docs/judges/FIGURES.md)**

GitHub Pages is **NOT VERIFIED** for this repository (API responded 404). The GitHub link displays the source; the HTTP launcher is the **actual interactive view** on your Mac. A Notion review page gives the team a stable entry link without inventing a public deployment. The localhost URL only works on the same host—it is not an external public address.

## Four-minute presentation sequence

| Time | Screen section | Say |
|---|---|---|
| 0:00–0:30 | Hero + protocol | “We tested a synthetic Synthea FHIR-to-form pipeline locally. open.epic is our interoperability reference, not a production writeback.” |
| 0:30–1:10 | Cyan vs amber roles | “Claude produced the localhost forms, model and OCR challengers, and the original demo. My independent lane froze/verified source identities, statistical inference, FCO/FCG custody, negative ablations and admissions.” |
| 1:10–2:05 | Measured comparisons | “L1×L3 source-bound validation moved full-form results 18/54→30/54 (+22.22 pp). Learned OCR correction moved 14/46→22/46 (+17.39 pp). They are discovery observations, not independently replicated clinical gains.” |
| 2:05–2:50 | Negative controls + Merkle | “YOLO crops were 9/46; adding a trained box classifier did not beat OpenCV. Each source, result and reported weight has distinct leaf/hash lineage. A root is identity, not correctness.” |
| 2:50–3:25 | Hardware / privacy | “Apple Silicon on magicSTUDIObox and magicPRObox; local 127.0.0.1 form server and models. Teammate synthetic hosted API benchmark is separate; PostgreSQL parity not independently queried.” |
| 3:25–4:00 | Sponsor handoff | “NVIDIA can run the same cases on GPU with Nsight traces; Fireworks can provide a frozen hosted frontier baseline on approved synthetic inputs; Microsoft/GitHub can attest evidence manifests and enforce signed CI gates. None of those proposed integration tasks should be presented as already completed.” |

## Original experimental protocol

**Freeze:** MITRE Synthea synthetic FHIR cohort target N=100, frozen patient/template identities and 63 train / 19 validation / 18 test patient split; deterministic B0 and gold oracle need PI sign-off. No raw real patients.

**Transform:** Source-bound FHIR paths → typed passport → form fields → deterministic normalization, abstention and validation. **Challenge:** run B0 + additions and Bfull-minus-one (LOMO), plus Apple Vision, local Qwen, YOLO and deterministic controls on exactly matched cases. **Measure:** exact paired McNemar, Holm multiplicity, patient-cluster paired bootstrap, separate bbox candidate AUROC, latency and unsupported fields. **Replicate:** a new untouched cohort plus form layout and independently locked oracle is **NOT_TESTED**. **Admit:** records with verified source identity can enter the research ledger, including negative and null results; scientific superiority remains **HOLD**.

### What counts as admitted in the research record

- **DATA_ADMITTED_FOR_RESEARCH** — an existing committed synthetic source file has exact-byte SHA-256 identity and a grounded program boundary; this does NOT independently certify all licensing or semantic correctness.
- **DISCOVERY_RECORD_ADMITTED** — the observed experiment and provenance, uncertainty, and limitations are preserved; even statistically positive discovery is **NOT** a generalizable gain.
- **NEGATIVE_OR_NULL_RECORD_ADMITTED** — a measured loss, tie or failure is preserved without silently promoting a fix.
- **SCIENTIFIC_GAIN_ADMITTED** — **NONE**, because untouched prospective replication, independent PI oracle approval and other gates are outstanding.

## Distinct actor and dataset lanes

| Lane | Delivered | Model/weights | Claim limit |
|---|---|---|---|
| Claude Code SWE/PM | 100 synthetic-patient cohort; local HTML/PDF intake and filled forms; B0; Qwen zero-shot M0 answers; YOLOv8n training; A1 OCR learned correction | M0 local Qwen2.5-0.5B Instruct; YOLOv8n 30+30 epoch paths and recorded SHA; OCR correction **not Qwen weight training** | Original work and discovery improvements, not an independently approved clinical model |
| ChatGPT PI/PM independent | FCO/FCG paired analysis, bootstrap and Holm audit, exact-byte Merkle source/successor checks, local logistic/RF box challengers, negative results, FCAR gate, judge audit | Logistic trained checkpoint; RF 10/30/63 checkpoints; Apple Vision and local Qwen receipt spot-check | Provides independent verification and challenger models; does not claim ownership of Claude original forms |
| Teammate API/serverless | Supabase/PostgreSQL schema/import claims; 48 synthetic hosted model-run aggregates and 24 paired pilot comparisons; GitHub branch/CI integrations | Hosted endpoint revision/weight **UNKNOWN** in public aggregate | Team-reported hosted pilot, **not** local/private inference or independent FHIR source parity |

**Hardware:** magicSTUDIObox Apple Silicon (prior readback ~32 GiB RAM, 10 CPU cores) and magicPRObox Apple Silicon (16 GiB RAM, 8 CPU cores). No NVIDIA CUDA GPU executed by this local experiment; no new Fireworks job, Epic writeback or real patient-data upload.

## Concrete teammate requests — bounded and evidence-based

| Owner requested | Minimum task | Acceptance proof |
|---|---|---|
| Claude / SWE/PM | Link this start page in README and demo; preserve original screenshots, all A0–A3 outcomes and failed Preview record; add new untouched synthetic layouts only after freeze | New commit, no predecessor modification, source screenshots and model answers traceable by hash |
| ChatGPT / PI/PM | Red-team the new blind replication and independently recompute paired McNemar/bootstrap/AUROC, preserving negatives | Independent source/weight/readback receipt and FCAR decision |
| NVIDIA teammate | Run same frozen synthetic forms on an **actually authorized** NVIDIA CUDA GPU; record GPU model, driver/CUDA, memory, Nsight profiling, fixed model weights and matched outputs | GPU hardware probe, performance trace, exact checkpoint + source digests, matched-case quality and latency |
| Fireworks teammate | Select verified model endpoint/version, use **approved synthetic-only** inputs, execute matched frontier vs open-model benchmark, record raw response digests, cost, runtime, accuracy, calibration | Provider request IDs, endpoint identity, response hashes, source/weight identity if available, paired evaluation and latency/cost receipts |
| Microsoft/GitHub teammate | Add verifiable GitHub artifact attestations for release evidence bundles and required-workflow checks; review least-privilege Actions permissions | `gh attestation verify` pass for actual release bundle, pinned git/ref and digest, reproducible CI |
| PostgreSQL/Supabase owner | Independently read back a transaction-consistent synthetic source snapshot versus local frozen 100 records | Same patient identity mapping, row count, hashes/NULL discrepancies, no destructive reimport |

**No teammate is authorized by this document to export private patient/source files or change existing Vita DAISY training.** The separate project may share methodology only.

## Existing deeper material

- [PR #64 — independent OCR statistics and root reconciliation](https://github.com/biobitworks/frontier-forms/pull/64)
- [PR #63 — Claude model screenshots and actual trained OCR correction](https://github.com/biobitworks/frontier-forms/pull/63)
- [PR #62 — Claude M0 zero-shot model answers](https://github.com/biobitworks/frontier-forms/pull/62)
- [PR #60 — complete outcome and negative ledger](https://github.com/biobitworks/frontier-forms/pull/60)
- [PR #65 — Claude source-linked per-cell heatmap](https://github.com/biobitworks/frontier-forms/pull/65) (check current status before making claims)
- [FCO/LOMO details](JUDGE_OUTCOME_HEATMAP_V1.html), [OCR bootstrap](FIG12_OCR_CORRECTION_ABLATION_V1.html), [Gantt](FRONTIER_FORMS_GANTT_V2_20261102.html).

**Source of truth:** `VIDEO_EVIDENCE_MANIFEST_20261102.json` preserves the exact source-file SHA-256 values. All displayed roots are derived from already-computed, source-declared canonical leaf recipes. This presentation does not fabricate a new root or claim causality from Merkle membership.
