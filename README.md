# Frontier Forms — Antigentic EHR Form Intake

> **Start here (judges, 2026-11-02).** Current status, results and priorities: [docs/STATUS_2026-11-02.md](docs/STATUS_2026-11-02.md). Accomplishment heatmap: [docs/figures/accomplishment_heatmap.png](docs/figures/accomplishment_heatmap.png) (interactive: [.html](docs/figures/accomplishment_heatmap.html)). Every figure and image with its caption and source PR: [docs/figures/FIGURES.md](docs/figures/FIGURES.md).
> Headline on 54 held-out synthetic test forms: B0 33.3% (18/54) full-form success; B0 + FCG harness 55.6% (30/54), discovery grade; post-training arm not yet scored. All data synthetic (MITRE Synthea), all inference local. The sections below are the original pre-release protocol, and some of their NOT_TESTED rows have since been run (see the status file).

**Repo:** https://github.com/biobitworks/frontier-forms
**Parent commit:** 67bf6b0ba51dc7ed792c139f37fcc648653611c4
**State:** PRE-RELEASE_EVIDENCE_PACKAGE; NO_LIVE_EHR_WRITE.

## Business use case

Convert scanned/faxed medical forms into source-grounded, human-reviewed HL7 FHIR drafts with antigentic safeguards. A wrong field can cause rework and downstream clinical risk. This is a research prototype, not a clinical product and not a replacement for clinical judgment.

## Sources and integrations

| System | Role | Current scope |
|---|---|---|
| [MITRE Synthea](https://synthea.mitre.org/about) | Synthetic patient records and encounters, in CSV/FHIR/C-CDA | Local sample archive byte-frozen; rendered scanned forms NOT_TESTED |
| [Open Epic](https://open.epic.com/TechnicalSpecifications) | FHIR R4, SMART/OAuth2 specs, supported read/write resources | Documentation, not an OCR dataset; OAuth and reads NOT_TESTED; writes PROHIBITED |
| [NVIDIA Megatron-LM](https://github.com/NVIDIA/Megatron-LM) | NVIDIA GPU-optimized training framework | Source pinned at 631e146322af891b0c79b8d5a53bc579a69f01f3; GPU training NOT_TESTED |
| [Fireworks](https://fireworks.ai/pricing) | Serverless inference and usage-based cost comparison | Existing historic Braintona adapter; this EHR experiment NOT_TESTED |
| [Microsoft Document Intelligence](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/overview) | Optional specialist OCR/layout arm | NOT_TESTED |
| [Antigence](https://github.com/biobitworks/antigence) | Independent challenge, MCP policy, admission and abstention | Prior component, new form-harness deployment NOT_TESTED |
| [Snyk](https://docs.snyk.io/developer-tools/snyk-cli/snyk-cli/getting-started-with-the-snyk-cli.md) | Code, dependency and integration security | Scan gate must have real receipt |

Synthea and Open Epic are not two paired OCR datasets. Labeled rendered forms must be generated with reproducible layouts, source field positions and held-out patient/template splits. Never send real PHI to public model APIs or this repository.

## Exact immutable FCO/FCG predecessor

15-leaf recomputed project Merkle root:
9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a

Predecessor dataset input Merkle root:
5f9a7e51f1ee03d70d34e99358fe14230efa396f7fd851df21f424e6843f61b1

13/13 source files independently checked on magicSTUDIObox; 728/728 input inclusion proofs independently replayed. SIGNATURE=NOT_SIGNED. MMR=NOT_COMPUTED. These prove file identity/inclusion, not clinical truth, causality or model competence.

**Frozen discovery only:** 38 matched cases. Local Liquid longevity 25/38; Insilico Qwen3-0.6B-Longevity 27/38. Exact two-sided McNemar p=0.6875. Both source and independent stratified-bootstrap intervals include zero. Superiority is NEGATIVE/FAIL. The older and successor bootstrap methods and receipts remain separately recorded.

The original frozen manifest declares public_export=NOT_AUTHORIZED. This PR includes a user-requested **metadata-only review export**, not authorization to publish raw model weights, patient records, protected gold-oracle values, dataset bytes, or private credentials.

## Reproducibility

Every notebook has Requirements, Data input, Data analysis, Data output and claim ceilings.

| Notebook | Focus | State |
|---|---|---|
| [EXP-000](notebooks/00_fco_merkle_replay.ipynb) | 15-leaf predecessor recomputation | Source metadata PASS |
| [EXP-001](notebooks/01_paired_mcnemar_bootstrap.ipynb) | Paired exact McNemar, bootstrap | Discovery negative |
| [EXP-002](notebooks/02_classification_auroc_fpr_fdr.ipynb) | FPR/FDR/TPR; AUROC missing scores | Partial; AUROC NOT_COMPUTED |
| [EXP-003](notebooks/03_lomo_harness_ablation.ipynb) | LOMO harness removal protocol | NOT_TESTED |
| [EXP-004](notebooks/04_synthea_to_fhir_contract.ipynb) | Fixture-only FHIR shape | No actual EHR operations |
| [EXP-005](notebooks/05_fireworks_pricing_roi.ipynb) | Rate formula, token ROI missing | Actual tokens NOT_COMPUTED |
| [EXP-006](notebooks/06_lean_gsd_gsigmad_admission.ipynb) | Formal and governance checks | Lean/GSD/gsigmad NOT_TESTED |

With Python 3.12+ and nbformat, nbclient, ipykernel, run:

    python3 scripts/verify_predecessor.py --bundle evidence/freeze/predecessor
    python3 -m unittest discover -s tests -v
    python3 scripts/execute_notebooks.py

A raw-source verify can be run locally on magicSTUDIObox with --source pointing at the existing frozen directory, but the public metadata replay does NOT recalculate source bytes.

## FCG experiment route

source bytes → SourceFCO → atom/occurrence/context FCO → typed FCG relationships → transformation receipt → measured claim → statistical gate → release artifact.

Future paired harness comparison: A0 closed frontier if event rules require; A1 fixed Fireworks serverless model + minimal tools; A2 same model/settings + Antigence/FCG; A3 local model is a system comparison, not a harness causal ablation; A4 NVIDIA training/post-training is separate.

Require directionally positive exact McNemar p<0.05, 95% stratified paired bootstrap lower bound>0, independent untouched replication, denominators for FPR/FDR, continuous scores for AUROC, authorized task success guardrail and source-backed token ROI. Do not preregister an outcome as true. All unexecuted actions remain NOT_TESTED.

See the experiment protocol, FCG chain, lab notebook, source-rights boundary, GSD phases and independent Claude review handoff in docs.

## Supabase upstream intake (reported, not frozen)
The user reports a dataset being built in Supabase. The project and schema are not yet linked to this repository, and its row count, sensitivity, source version and contents are UNKNOWN. We register this as a **prospective upstream source** in [the Supabase source contract](docs/protocols/SUPABASE_SOURCE_CONTRACT.md) and [the source-intake ledger](evidence/sources/supabase_source_intake.json). This does not replace the frozen LongevityBench root or authorize an export. EXP-007 checks that these unresolved gates fail closed. Only an observed consistent snapshot and separately computed Merkle commitment can advance the Supabase lane.

## Claude red-team lane (cloud session, append-only successor)

Branch `redteam/claude-fcg-local-ablation-20261102-cloud` (parent PR #3 head `da953450`). Independent re-verification of every
root above with separate code, matched local-model lanes (L0 Liquid longevity, L1 qwen3:1.7b, L2 qwen2.5vl:3b, L3 Insilico
checkpoint) over the frozen discovery (38) and heldout (39) partitions with FCO/FCG context, forged-leaf, removed-edge, prompt
injection, verdict and option-swap antigentic gates, a cold-restart replay, and a synthetic-form VLM extraction lane with a
deterministic FHIR draft scorer. Results, gates and claim ceilings: [docs/reviews/CLAUDE_REDTEAM_REPORT.md](docs/reviews/CLAUDE_REDTEAM_REPORT.md),
[docs/architecture/LEAF_GAIN_ATTRIBUTION.md](docs/architecture/LEAF_GAIN_ATTRIBUTION.md), [experiments/CLAUDE_LAB_NOTEBOOK.md](experiments/CLAUDE_LAB_NOTEBOOK.md).
Agent instructions: [README_AI.md](README_AI.md). A concurrent local Claude lane lives on `redteam/claude-fcg-local-ablation-20261102`
and is cross-checked, not merged.

Reproduce (container, no inference): `python3 scripts/redteam/execute_redteam_notebooks.py` → new `evidence/notebook_runs_redteam_v<N>/`.
Reproduce (magicSTUDIObox, private evidence dir): see `scripts/redteam/*.py` docstrings; only `*_PUBLIC.jsonl`/`*_META.json` leave the host.
Fireworks L4/L5, Snyk, NVIDIA training, live Supabase and Epic remain BLOCKED / NOT_TESTED in this lane.

## App-plane integration and red-team review
The project application baseline includes teammate [Supabase migration](supabase/migrations/20261102000000_initial_schema.sql) and [Synthea FHIR importer](scripts/import_fhir.py) merged from PR #4. The evidence workflow must not mutate that operational implementation without review. New review checks fail closed on exact frozen evaluation input byte mismatches; Jupyter reruns write new versioned receipt directories. The original predecessor Merkle root has not changed. Draft PR #5 reviews stable identity, nondestructive provenance and a canonical dataset snapshot; draft PR #6 provides a synthetic red-team comparison, not demonstrated improvements in live model accuracy.

## Post-merge custody hardening
The Claude synthetic freeze-red-team lane and independent design-review document were merged via PR #6 and PR #5. A follow-on review corrected an input-state spoofing flaw in the Claude verifier, added a regression test, and explicitly pinned the only permitted synthetic binary fixture by its exact SHA-256. This fixture tests custody, not clinical source data or model improvement. Existing frozen predecessor and prior review roots remain immutable.
