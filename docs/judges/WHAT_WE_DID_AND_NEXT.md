# Frontier Forms: what we did and what comes next

The project turns a medical intake form into a draft FHIR record and checks each field against its source. It uses only synthetic patients from MITRE Synthea. There is no PHI, and models run locally on our own Macs (Apple Vision, Ollama Qwen, local detectors). No hosted inference was used, and nothing was written to a live EHR. Each claim carries one of these statuses: PROPOSED, IMPLEMENTED, EXECUTED, OBSERVED, SUPPORTED, NEGATIVE, NULL, NOT_TESTED or BLOCKED. **No workstream has reached SUPPORTED**, because every positive result still needs replication on a fresh cohort or a new template family.

This summary covers 34 pull requests: 27 merged, 4 open and 3 closed without merging. The machine-readable inventory is `docs/judges/pr_inventory.json`.

## Workstreams

| Workstream | Status | PRs |
|---|---|---|
| Custody and Merkle root replay | OBSERVED (open custody findings) | 1, 3, 6, 8, 11, 13, 17, 20, 21, 47 |
| LongevityBench model lanes | NEGATIVE | 1, 3, 9, 11, 13, 20 |
| FCO/FCG context in the prompt | NULL | 11, 13, 20 |
| Supabase schema and importer | EXECUTED locally; live DB NOT_TESTED | 4, 5, 9, 17 |
| Synthea cohort freeze (100 patients) | OBSERVED | 10, 17 |
| Form rendering and loopback server | OBSERVED | 1, 10, 12, 19, 20, 22 |
| B0 baseline and L1–L3 module arms | OBSERVED (discovery grade) | 10, 17, 18, 19 |
| Apple Vision OCR | OBSERVED | 10, 12, 20, 22, 23 |
| qwen2.5vl:3b extraction | OBSERVED | 10, 12, 19, 20, 23, 29 |
| Tesseract OCR | OBSERVED | 10, 11, 19 |
| Qwen text mappers | NEGATIVE | 12, 22, 23 |
| Qwen LoRA SFT (before vs after) | EXECUTED; gain NOT_TESTED | 10, 17, 18, 26 |
| Learned bbox validators (logistic, RF, D1, D2) | NEGATIVE | 14, 15, 16 |
| YOLOv8n field detector | OBSERVED; V2 NOT_TESTED | 19, 20, 21 |
| Per-epoch Merkle training ledger | OBSERVED | 18, 20, 21 |
| Gate factorial and commitment gate | OBSERVED; replication NOT_TESTED | 20, 21, 23 |
| Injected-error detectors (Merkle, Lean, source binding) | OBSERVED | 10, 18 |
| Fault-injection factorial (16 masks) | OBSERVED (by design) | 12 |
| Training dashboards | OBSERVED | 7, 18 |
| 100-patient acceptance runner | OBSERVED; PR open | 22 |
| Lean 4 proofs | EXECUTED (compiled) | 3, 10, 11, 12, 20 |
| Paired statistics | EXECUTED | 3, 11, 17, 18, 19, 28 |
| Prompt injection | OBSERVED; filter NOT_TESTED | 10, 11, 29 |
| Security (gitleaks, JSON-only policy, CI) | EXECUTED | 8, 16, 17, 27, 28, 30, 39, 43, 45 |
| Fireworks | BLOCKED | 1, 3, 12, 20, 26 |
| NVIDIA/DGX training | NOT_TESTED | 1, 3, 12, 20 |
| Epic integration | NOT_TESTED | 1, 3, 7, 22 |
| Snyk | BLOCKED (CLI auth) | 1, 3, 8, 11, 20 |
| Governance (GSD/gsigmad, reviews, TASKS) | EXECUTED | 3, 5, 9, 17, 20, 29, 42, 44, 46, 47 |
| Demo and overlays | IMPLEMENTED | 7, 10, 12, 18 |

## Headline results

- **Frozen cohort.** It has 100 Synthea v3.4.0 patients split 63/19/18. Two generations were byte-identical (#10).
- **Baseline vs harness.** These numbers are on the 54 held-out test forms. B0 reached 0.333 (18/54) full-form success. The B0+L1+L2+L3 harness reached 0.556 (30/54), with McNemar p=0.00049 and a patient-cluster CI of [0.074, 0.370] (#17, #18, #19). This is discovery grade only.
- **Commitment gate.** The per-field commitment leaf raised planted-error detection from 0.13 to 1.00, with 0 false admissions. Holm p < 0.0001 and the CI is [+0.61, +0.66] (#20). Replication is NOT_TESTED.
- **Injected-error detectors.** The test set had 654 forms with 702 injected errors. M3 source binding reached 0.989 recall with a 0.041 clean-field FP rate. Without source data, M1+M2 reached 0.426 recall (#10, receipt in `evidence/forms_detectors/README.md`).
- **qwen2.5vl:3b.** On SYNFORM2 test it read 318/322 fields correctly (#23 lane, `evidence/redteam/db/ledger.jsonl`). On 57 form images it reached box recall 0.821 and value read 0.736 (#19). It followed the injected note in 0 of 18 paired injected images (#29, open).
- **YOLOv8n detector.** Test mAP50 was 0.912 (315/322 fields at IoU≥0.5). The no-scan LOMO run reached 0.857 (#20).
- **100-patient B0 acceptance.** It covered 218 forms and 2,180 fields, with 1,867 matches (85.6422%) and 0 server echo errors (#22, open).
- **Custody.** The 728-input, 15-leaf and review roots were recomputed independently, and all 728 inclusion proofs verify (#11, #20, #47).

## Negative and null results we kept

- **LongevityBench.** Liquid scored 25/38 and Insilico 27/38, with McNemar p=0.6875. This is NEGATIVE (#1, #3).
- **FCO/FCG context in the prompt.** The result is NULL on held-out data (25/39 vs 25/39). Insilico with full FCG scored 25→24/38 and 22→19/39, which is NEGATIVE (#11, #13).
- **qwen3:1.7b and qwen2.5vl:3b on LongevityBench.** They scored 3/39 and 6/39 because of format failures, which is NEGATIVE (#20).
- **Qwen text mappers.** On the same input, qwen2.5:1.5b got 209/322 and qwen3:1.7b got 109/322. The deterministic parser got 283/322 (#23).
- **Logistic box validator.** It got 540/540, the same as the contour control (McNemar p=1.0, CI [0, 0]). This is NEGATIVE (#14).
- **Random Forest box validator.** It got full pages right on 34/54 forms against the control's 54/54, a gap of −37.0 pp (#15).
- **D1 segmenter.** It reached F1 0.11285 (NEGATIVE). D2 reached F1 0.77828, but it was tested only on layouts it had already seen, so it is exploratory (#16).
- **Qwen2.5-0.5B LoRA.** We have one epoch-0 validation loss (1.0049872103490327) and no adapter, so the gain is NOT_TESTED (#18).
- **Publication policy.** The JSON-only gate found 123 legacy non-JSON files. They are exempt only while unchanged; they are not compliant (#22, #27/#30).
- **External services.** Snyk is BLOCKED (auth), Fireworks is BLOCKED (no credential, and the PI policy forbids it), and NVIDIA training, live Supabase and Epic writes are NOT_TESTED.

## What remains (ordered)

1. **Fresh replication cohort (T01 #31).** Use a new Synthea seed, preregister the arms and score them once. Only this can move the L1–L3 gain and the commitment gate toward SUPPORTED.
2. **Trained-model result (T08 #38).** Restart M1 SFT on the MacBookPro. Then score M0, M1 and M2 on the 54 test forms with McNemar and a patient-cluster CI.
3. **Custody fixes (#47).** Fix the duplicate-last-leaf, uncommitted-parent and dangling-edge findings by binding the leaf count and parent in leaf 0, or by moving to RFC 6962. Regenerate `evidence/stats` through the source-byte gate.
4. **Oracle-rule sign-off (T02 #32).** Byron needs to approve the two oracle rules.
5. **Noisy and scanned renders (T03 #33).** Compare Tesseract, Apple Vision and qwen2.5vl on clean vs degraded renders.
6. **V2 detector results (T09 #40).** Report them per perturbation and compare them with the contour control and D2.
7. **Prompt-injection filter (T04 #34).** Build it and score both its pass-through rate and its false-strip rate.
8. **Acceptance runner (#22).** Rebase it onto main and produce one unified field-level receipt for Qwen → PDF → OCR → source binding.
9. **Publication policy (issue #24).** Migrate the legacy binary and JSONL fixtures to JSON only, then confirm CI is green on main after #43.
10. **Cost and latency (T05 #35).** Report cost and latency per correct form.
11. **Owner decisions.** Decide T07 (Supabase readback), T10 (closure of PR #1) and #25 (porting PR #1's fixtures). Merge #29 and #47, review the #44 contract, and open a PR for the unmerged red-team demo branch.
