# Frontier Forms — judges' evidence package (2026-11-02)

**Start with [the labeled, offline accomplishment heatmap](JUDGES_EVIDENCE_HEATMAP_20261102.html).** Open it as a local HTML file to see the 4-column contributor × capability map, actual quantitative denominator bars, captioned figure gallery and PR inventory. GitHub's file viewer may show HTML source rather than render it; the JSON and Markdown below remain readable in GitHub.

This package is a **presentation and provenance successor**. It has not trained, rerun, rescaled or corrected model measurements and **has not created any new Merkle roots**. All numeric evidence is sourced from existing receipts. Every image caption is an editorial label based on known workflows and filenames, **not** independent pixel-level verification. Original raster image assets are referenced, not duplicated.

## Contributions: do not conflate the work lanes

| Lane | What the source PRs establish | What not to claim |
|---|---|---|
| **Teammate — PR #4** | App/Supabase importer and teammate-reported synthetic cohort, passport facts and writeback design | Teammate's 100/8,252 DB values have not been independently read back; those records are **not** the same cohort as the 100 Synthea v3.4.0 subset patients |
| **Claude Code — PRs #10, #19, #21, #23; draft #29** | Pinned Synthea cohort; local FHIR read-only form server, B0 and FCG modules; Apple OCR/PDFKit; Qwen2.5VL/Tesseract; YOLO pipeline; synthetic red-team evidence, gate factorial, draft bbox overlay viewers | No demonstrated unseen-template trained-model superiority or clinical performance; draft #29 is not merged |
| **ChatGPT / independent lanes — PRs #12, #14–16, #18; draft #22** | Independent factorial fixtures/Apple/Qwen comparisons; local logistic, Random Forest, D1 and D2 box model experiments; Holm/LOMO and Merkle breakpoint audits; 100-patient deterministic acceptance replay, Qwen one-patient smoke test, CSS/PDF samples, Apple OCR spot checks | No end-to-end local neural model gain or authenticated production writeback; PR #22 remains draft |
| **Integration/review successors — PRs #27, #30, #39, #43; draft #44** | Exact-byte legacy Git publication policy, CI/yaml correction, integration model/LOMO contract | Neither a passing unit test nor a merged PR substitutes for scientific replication or necessarily green current CI |

**Attribution method:** source PR bodies and session references were reviewed. Shared GitHub account names **do not** identify who authored a change. A lane label may reflect a documented handoff or an independent research pass rather than sole authorship. The machine-readable [PR contribution ledger](PR_CONTRIBUTION_LEDGER.json) records uncertainty; no attribution is asserted solely from a commit's GitHub author.

## What can be shown to judges today

1. **The actual frozen data and server:** 100 living MITRE Synthea v3.4.0 synthetic FHIR subset patients, split 63/19/18; 3 synthetic HTML forms. These are **100 patients, not 100 separate datasets**. Open Epic provides technical FHIR documentation; these forms are not independently proven Epic UI replicas.
2. **Held-out deterministic baseline:** B0 18/54 required-field-complete test forms; full B0+L1+L2+L3 30/54. The 12-form improvement is **discovery grade** because those errors were seen before designing modules, not a replicated trained-model gain.
3. **Image evidence:** Claude's local qwen2.5vl:3b evaluated 57 synthetic form images, 82.11% IoU50 box recall, 213 false boxes, 73.56% nonblank value read. Tesseract's 78.74% nonblank read accuracy uses a different text-proximity method and is **not** a direct box IoU comparison. Exact source summaries are in the [metric JSON](ACCOMPLISHMENT_MATRIX_20261102.json).
4. **Independent negative results are important:** D1 trained segmenter failed (13.06% recall), D2 local post-hoc candidate classifier reached 95.56% recall but only 65.65% precision on the same layouts; logistic classifier matched a deterministic contour control exactly (540/540, zero gain). These are useful diagnostics, not a license to claim generalization.
5. **Causal-labeling discipline:** The M1 Merkle, M2 Lean and M3 FCO detector factorial is on 702 **planted** synthetic faults. The full combination detects 694, with 236 false-positive clean fields (of 5,731). Conditional LOMO identifies no extra detector recall from M1/M2 once M3 is present. This demonstrates source-binding sensitivity in these fixtures, not clinical efficacy.
6. **End-to-end connection remains partial:** ChatGPT draft PR #22 executed 100-patient B0 server submissions (218 form cases; 1,867/2,180 correct fields), one-patient Qwen2.5:0.5b (12/20 fields) and selected HTML/CSS → PDF/Apple Vision spot checks. The 100-patient run **did not** produce a final unified Qwen/vision writeback receipt.

## Figure labels

Every principal source figure has a [stable judge-facing ID and complete caption](JUDGE_FIGURE_CATALOG.json). The current [main-image inventory](IMAGE_CAPTION_INVENTORY.json) covers **143 existing images** with a separate label for each. Sample captions:

- **FIG-01** — FCO/Lean/Merkle gate-factorial study diagram (Claude/red-team PR #21). This visual concerns *synthetic* source admissions, not patient outcomes.
- **FIG-02** — Longitudinal training dashboard (independent PR #18). Actual neural epochs, cross-sectional model-size checks and deterministic interventions are visually separated.
- **FIG-03** — Three-detector factorial recall/false-positive heatmap (Claude PR #10). Exact denominators 702 injected faults and 5,731 clean fields.
- **FIG-04/05** — Controlled fault and vision overlay demonstrations (independent PR #12). By-design corrections or one-form comparisons are not generalizable model gains.
- **FIG-06/07/08** — Blank, B0-filled, and adversarial synthetic forms (Claude PR #10). Original pixels unchanged. Captions expressly describe them as synthetic.
- **FIG-09** — Single local Apple/Qwen comparative form raster (independent PR #12), *not* 100-form performance evidence.
- **FIG-10** — Historical status heatmap (independent PR #7), including prospective and NOT_TESTED states.
- **FIG-11/12** — Clean and injected bbox overlay **draft HTML viewers** from Claude PR #29, explicitly not included on main in the frozen snapshot.

## What remains and what judges should not be told

The open issues and PRs specify: fresh independent replication (T01/#31); two oracle decisions (T02/#32, PI decision required); degraded/noisy forms (T03/#33); prompt-injection filter and negative controls (T04/#34); cost/latency per correct form (T05/#35); PR #3 successor review (T06/#36); independent teammate DB verification (T07/#37); matched base-versus-trained Qwen evaluation (T08/#38); unseen-layout vision validation (T09/#40). See [Claude's merged task register](../../docs/TASKS.md).

The next executable **end-to-end** acceptance contract is patient × form × field × source leaf × model digest × written value × HTML DOM box × PDF OCR box × validator outcome. Do not substitute a form server's JSON echo, PDF text found *somewhere*, or a Merkle hash for full source-to-display correctness.

**Security/CI:** Current JSON-only policy permits explicitly frozen *unchanged historical* non-JSON Git blobs while rejecting newly introduced prohibited data. This is not the same as removing old public content from Git history. No weights, raw new images, hosted inference or real PHI are added by the judge package. CI has had both success and failure runs; the report does not assert a global pass unless the exact integration commit has completed green required checks.

## Inspectable companion files

- [Offline heatmap / captioned gallery](JUDGES_EVIDENCE_HEATMAP_20261102.html)
- [Matrix + metric source ledger](ACCOMPLISHMENT_MATRIX_20261102.json)
- [All-PR frozen snapshot](PR_HISTORY_SNAPSHOT.json) and [lane attribution](PR_CONTRIBUTION_LEDGER.json)
- [Figure captions](JUDGE_FIGURE_CATALOG.json) and [every existing main image's caption](IMAGE_CAPTION_INVENTORY.json)
- [Source-only view builders](build_judge_views.py) and [render script](render_judge_dashboard.py)

**Release decision: NOT ADMITTED** for Epic production writeback or trained-model superiority. This packet is judge-ready as an explicitly *bounded synthetic evidence demonstration*, pending PR review and an independently executed end-to-end gate.
