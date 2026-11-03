# Training readiness — frontier-forms lane (synthetic forms)

Status line: **DATASET FROZEN AND SERVED; TRAINING NOT_EXECUTED.** This lane is separate from any cloudmer/knots work; it uses
its own data (Synthea-derived synthetic forms) and its own model candidates. Nothing below asserts a trained model exists.

## What is frozen (append-only successors of the 15-leaf root `9e4d4df8…d3a9a`)

| Dataset | Root | Parent | Content | Where |
|---|---|---|---|---|
| SYNFORM-36d12313 (predecessor) | `36d12313c179ec207af81cd24356ce5bc172b430b584bdef397f383292375fe6` | leaf 3 (Synthea zip `990d5206…eda16`) | 12 clean forms, private oracle | evidence dir on magicSTUDIObox |
| **SYNFORM2** | `aa447934df5267349386fd0c5053a63a5ec140b05c504d221591e4ddd4b7580e` (223 leaves, leaf 0 binds count) | SYNFORM-36d12313 + leaf 3 | 111 patients (one encounter each), **train 66 / dev 22 / test 23** by sorted case hash (patient-level), 2 variants (clean, scan) = 222 PNG; 7 labelled fields; private oracle | `~/projects/active/frontier-forms-redteam-cloud-20261102/synform2` |
| **SYNFORM2-ERR** | `790a7dc6f9641fa6c09df8ac951d8456f9ab2685326e4eb67012cd0e87d68944` (231 leaves) | SYNFORM2 | 23 test cases × 10 images: clean, 7 planted-error classes (E1–E7), 2 variance levels (V1 σ9, V2 σ25+2.5°); **per-field salted commitments in every FCO**; opaque image ids; private planted key + salts | `…/synform2_err` |

Public listings (`inputs.jsonl`, `manifest.json`, `leaves.jsonl`) contain hashes, splits and commitments only. Oracle values,
planted labels and salts live under `.private/` on the host. Public export of the oracle is **NOT_AUTHORIZED_PENDING_RIGHTS_DECISION**
(Synthea is synthetic, but the decision belongs to the owner, not to this lane).

## Local test server (observed)

Two `python3 -m http.server` instances bound to **127.0.0.1 only** serve the public directories: SYNFORM2 on port 8765, SYNFORM2-ERR
on port 8766 (PIDs recorded in `/tmp/claude-redteam-20261102/out/testserver*.pid`). Every lane fetches `/manifest.json`, verifies the
served listing against `public_input_listing_sha256`, fetches each PNG and verifies its sha256 against the FCO before any
extraction. A served file that does not match its leaf aborts the lane (fail closed). No external host was contacted.

## Extraction lanes on the frozen forms (receipts under `evidence/redteam/lanes/`)

* `OCR_apple-vision_synform2_{test,dev,train}` — Apple Vision (`VNRecognizeTextRequest .accurate`, en-US, no language correction),
  compiled Swift binary, headless; blank-page negative control PASS on every run.
* `VLM_qwen2.5vl_3b_synform2_test` — qwen2.5vl:3b single-pass JSON extraction + field-by-field reread challenge (queued after the
  LongevityBench driver releases Ollama).
* `OCRERR_*` / `VLMERR_*` — the same two extractors over SYNFORM2-ERR; the gate factorial (identity × rules × commitment × consistency)
  and its heat map are computed from these by `scripts/redteam/analyze_gate_factorial.py` on the host.
Numbers are in `docs/reviews/CLAUDE_REDTEAM_REPORT.md`; they are OBSERVED on rendered synthetic forms, not on scanned paper.

## What training would need (PROPOSED, nothing executed)

1. **Labels**: train/dev gold fields exist in `.private/oracle.jsonl` (66 + 22 cases × 2 variants). A rights decision is needed before
   they are copied anywhere, even though they are synthetic.
2. **Task definition**: image → 7 fields JSON (same scorer), plus a second head/prompt for the draft FHIR bundle produced by
   `frontier_forms.fhir_draft` (deterministic from fields, so it needs no separate labels).
3. **Candidate recipes**: (a) LoRA on qwen2.5vl:3b (Ollama weights are GGUF; a HF checkpoint download and MPS/CUDA fine-tune would be a
   new source leaf with its own hash); (b) a small OCR-post-correction model on top of Apple Vision output trained on the train split
   (cheap, CPU-feasible, directly targets the observed failure modes: single-letter gender box, spurious spaces, O/0 swaps);
   (c) NVIDIA Megatron-LM (pinned `631e146…`) only if a CUDA host appears — not on Apple Silicon.
4. **Admission for a trained model**: paired evaluation against the untrained extractor on the **test** split (23 cases × 2 variants),
   exact McNemar + stratified paired bootstrap ≥ 10,000, Holm, then replication on a freshly rendered template family; the ERR set
   (planted errors) is the safety guardrail: a trained model must not raise false admissions under the full gate.
5. **Receipts**: weights sha256, training config hash, dataset roots above, host/GPU, energy if measured; otherwise NOT_OBSERVED.

**When you can start**: as soon as (1) the rights decision for train/dev label use is recorded and (2) a recipe from (3) is chosen.
Everything else (frozen data, splits, server, scorer, gate, Lean-checked admission logic) is in place now.
