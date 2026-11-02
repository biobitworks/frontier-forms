# Frontier Forms — PR × dataset × model history for judges

Start with the [interactive Gantt](FRONTIER_FORMS_GANTT_20261102.html) (download HTML to view) and [evidence ledger](FRONTIER_FORMS_GANTT_EVIDENCE_20261102.json).

The Gantt shows **GitHub PR created-to-merged/closed durations**, not how long a model trained or an engineer worked. Actual model start/end timestamps are used only if a receipt provides them. Other model milestones are labeled PR-creation proxies or exact observation timestamps. All times Pacific Time on November 2, 2026.

At the 3:46:01 PM PST snapshot, **42 pull requests: 33 merged, 6 open, 3 closed without merge**; 16 dataset/model/governance milestones; 24 pre-existing tracked challenge events; 14 negative/tie outcomes; 8 discovery-positive outcomes **not promoted**; zero scientific promotions. An index links **472 existing Git-tracked JSON files**; these are source references, not 472 independently verified datasets or newly uploaded copies.

## Explicit negative and promotion results

The [machine-readable complete negative/admission ledger](PROMOTION_AND_NEGATIVE_RESULTS_20261102.json) preserves earlier events and 13 additional named outcomes. Representative results:

- D1 trained segmentation recall 13.06%; D2 post-hoc candidate detector recall 95.56% / precision 65.65%, 180 false positives; known layouts; NOT_PROMOTED.
- Logistic box detection equals deterministic contour 540/540, no measurable gain; Random Forest training-size cross-sections negative.
- B0 required-field-complete test forms 18/54 vs deterministic B0+FCG 30/54; discovery only, rules were selected after seeing baseline errors.
- Synthetic Merkle + Lean + FCO full stack detects 694/702 injected faults, with 236 false positive clean fields / 5,731; no claim of clinical correctness.
- SYNFORM2 deterministic geometric parser 283/322 fields vs qwen2.5:1.5b 209/322 and qwen3:1.7b 109/322, on the matched comparison in merged PR #23.
- YOLOv8n full vs no-scan: 315/322 vs 316/322 matched test boxes; mAP50 is higher for full, exact-field correctness is not. No unconditional admission.
- Claude PR #51: Apple OCR 58/70 clean → 0/70 after visible box annotation (negative preprocessing evidence); the annotation manifest required ten SHA/size corrections in independent audit PR #55. Both are open and **not merged in this snapshot**.
- Qwen2.5-0.5B LoRA: epoch-0 validation snapshot exists; independent post-training improvement NOT_COMPUTED. Vita DAISY methodology reused, but **not** its weights, performance or program roots.

## Distinct work lanes

Teammate PR #4 provides app/Supabase project baseline (DB facts are teammate-reported until verified). Claude's PRs #10/#19/#20/#21/#23 and #29/#51 provide Synthea, FHIR/HTML form server, B0, Qwen/Tesseract/Apple vision, local YOLO and red-team/demo. ChatGPT independent PRs #12/#14–#16/#18 and open #22/#54 provide controlled ablations, D1/D2/Random-Forest and logistic experiments, progress verification, PDF/Qwen smoke tests, and judge review. Other PRs are integration/security/attribution uncertain; a shared GitHub account cannot establish individual authorship.

## Acceptance boundary and remaining tasks

Before 4:30 PM PST, prioritize actual demo screenshots and source-linked figure captions, exact model digest, one successful synthetic HTML→PDF readback and one negative. Mark anything not done as pending; no hosted inference in this lane. Open Epic technical documentation does not prove the synthetic HTML templates are exact Epic UI replicas. The teammate's separate 100-patient Supabase cohort needs independent readback. Actual Epic patient writeback and clinical performance remain NOT_TESTED.

After the event, preregister a fresh independent synthetic replication cohort, score B0/Qwen base/trained/harness in the same held-out protocol, validate geometric OCR source-to-field alignment, then adjudicate admissions. Merged Git PRs do not constitute scientific promotion. Historical public binary-policy exceptions do not mean their pixels are newly JSON-compliant. No Merkle root computed in this reporting successor.

See [copyable teammate request](FRONTIER_FORMS_GANTT_REQUESTS_20261102.md).
