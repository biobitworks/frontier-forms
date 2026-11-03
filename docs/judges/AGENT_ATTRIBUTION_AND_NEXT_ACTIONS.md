# Frontier Forms: judge evidence, PR attribution, and next action

Sources: JUDGE_OUTCOMES_SUCCESSOR_V1.json (82 immutable outcome leaves), PR_HISTORY_SUCCESSOR_V1.json (GitHub snapshot), FIGURES.md (source-captioned synthetic demo), and the merged FCAR admission gate. All numeric experiments are on synthetic data.

## Who did what, as supported by evidence

| Contribution | Agent / evidence | Boundaries |
|---|---|---|
| Original labeled Figures 1–10, synthetic screenshots, browser/PDF server, Apple Vision overlays | **Claude Code**, PR #51 attribution and files; PR #50 source figure was also Claude-authored | Do not confuse illustrations or box localization with form clinical correctness |
| Expanded 34-row result ledger (Figure 1c), including failed and negative experiments and teammate bench | **Claude Code**, PR #57, merged on main | Three labeled operational promotions are not three scientifically admitted model improvements |
| OpenCV + logistic trained local box validator and independent negative result | **ChatGPT** independent execution, PR #14 | 540/540 boxes for both trained and deterministic baseline; zero gain |
| Longitudinal inference/statistical dashboard and Holm/patient bootstrap replay | **ChatGPT** independent execution, PR #18 | Only epoch-0 Qwen LoRA val loss in original frozen receipt; no held-out LoRA checkpoint gain |
| Demo hash reconciliation and mutation regression | **ChatGPT** independent audit, PR #55 and successor | First judge manifest had 10 wrong annotation hashes; preserved original failure and repaired 62/62 asset entries |
| Additional Figure 11, all 60 YOLO epoch statuses and 82-event Merkle/outcome reconciliation | **ChatGPT** independent execution, successor PR | Does not assert neural model performance gains from integrity roots |
| Supabase schema, jointly maintained FCO work, Fireworks pilot bench | Teammates or multi-agent; exact producer varies by PR | Common GitHub login is not proof of individual author |

## All outcome classes to show judges

**FCO discovery positive, NOT PROMOTED.** B0+L1 to B0+L1+L3 changes full-form success 18/54 to 30/54 on 18 synthetic test patients; +22.22 percentage points, exact paired McNemar p=0.00048828125, Holm p=0.005859375, patient-cluster 95% CI [+7.41,+37.04] pp. Rule selection was informed by prior baseline failures; neural checkpoint weights unchanged. No independent prospective replication.

**YOLO checkpoint results, development-only.** Local YOLOv8n has 30 actual epoch receipts per arm: full arm = 3 GAIN, 3 LOSS, 23 NEUTRAL, 1 FIRST; no-scan = 3 GAIN, 1 LOSS, 25 NEUTRAL, 1 FIRST. Merkle epoch chains independently recomputed with recorded checkpoint SHA identities. Those are 44-development-image transitions; not patient-level independent model promotion. Original trained weight bytes were NOT_REHASHED in this review.

**Negatives and null.** Local trained logistic field detector matched deterministic contour baseline 540/540 each (McNemar p=1; patient CI [0,0]). Random Forest 10/30/63 training-patient checkpoints fell below deterministic F1=1.000 control. Some FCO leaves added no full-form success; detector-crop arms have no supported improvement. In a 10-page synthetic Apple Vision OCR comparison, 58/70 fields were correct from clean images versus 0/70 when diagnostic boxes were drawn before OCR. These are separate outcomes and must not be pooled.

**Failures and adversarial evidence.** Prior forged custody state, initial public JSON scan, YOLO D1, prompt injection and synthetic field mix-ups remain FAILED where applicable. Corrected successor tests are new PASS records, not retroactive deletion of a failure.

**Admission.** Operational integrity gates have positive PASS/promoted records; **scientific model-gain admissions remain zero** per the executed Frontier Forms FCAR assessment. Vita DAISY contributed the freeze, challenge, replicate and admit process only. Vita DAISY weights, source roots or gain values were NOT imported; DAISY-specific performance is NOT_COMPUTED.

## Newly reported OCR-correction result — not yet independently replayed

Claude reports a preregistered learned OCR correction reaching 22/46 all-seven-field forms with Holm p=0.023, and detector-crop controls null. The source preregistration, 46 paired answer rows, model/adapter weight SHA-256, independent patient-cluster bootstrap, and stable GitHub receipt were NOT_OBSERVED at this review checkpoint. Treat this as REPORTED_PENDING_VERIFICATION, not a validated or admitted result. Append a new frozen successor and update Figure 11 only after inspecting the exact output bytes and statistical calculation.

## Next work, priority order

1. Merge this independent judge supplement after full synthetic-publication and CI checks; leave prior manifests, failed receipts, and all negative model records intact.
2. Verify Claude's OCR-correction new checkpoint and paired field outputs on exactly the preregistered frozen 46 cases, recompute exact McNemar/Holm and patient-cluster bootstrap, and cross-check text model weights vs FCO context vs crop/box intervention.
3. Retain FCAR HOLD until untouched patient and layout replication, matched oracle, signed/pinned checkpoint and independent PI admission. Do not conflate a changed Merkle root with causal model gains.
4. Show the same patient-source/FHIR field and output JSON in local browser and local PDF; OCR should operate on the unannotated image, while overlays are post-extraction visualizations.
5. Update Notion and GitHub with each actual successor checkpoint only after independent replay; review the remaining drafts (#22, #44, #53, #54) without force-merging destructive or unverified content.

The 82-event outcome root and all 62 demo asset hashes are identity commitments, not clinical evidence.

## OCR successor observed after the first report

The preceding REPORTED_PENDING_VERIFICATION entry was accurate at the earlier cutoff but is **now superseded** for paired statistics by OCR_CORRECTION_SUCCESSOR_V2.json and Figure 12. Original 46 synthetic paired outputs were merged with Claude PR #51, and the Figure 1 workstream update was merged with Claude PR #58. This independent reviewer recomputed the 14/46 versus 22/46 exact McNemar p=0.0078125, Holm p=0.0234375, and a 23-patient clean+scan **cluster-bootstrap** interval +4.35 to +32.61 pp. The fitted text-correction parameters were hashed as canonical JSON; the specific detector .pt bytes were not independently rehashed. This supports DISCOVERY_POSITIVE but does not prove signed preregistration chronology or untouched cross-cohort replication. FCAR scientific admission stays HOLD. The three-arm OCR result root 5acbf8276ed1c184423ea68b9973acec96a3a47e030d296f83e23c1c005071cb is append-only and binds the predecessor 82-event root.
