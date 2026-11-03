# Frontier Forms — video review entry and handoff index

**State:** COMMITTED post-deadline research presentation; **scientific promotion HOLD**. This document is not evidence of submission before the November 2, 2026 4:30 PM Pacific hackathon cutoff. It preserves predecessor main `99e4a87d89f7af6f202920aa3ac32a04c4bc543e`, containing merged video PR #70 and evidence closeout PR #83.

## Open for the recording

**Primary team-wide visual:** [Presentation V3 — corrected UTF-8 text, source-backed gains and actor attribution](present_v3.html).

**Alternative interactive deep dive:** [Claude versus ChatGPT lane comparison, LOMO × model results and Merkle roots](VIDEO_EVIDENCE_STORYBOARD_20261102.html).

**Shared Notion review:** [VIDEO START HERE — experiment protocol, results and sponsor handoff](https://app.notion.com/p/40d58ec71eb2815c9911e6952b41fbc9).

**Source and talking points:** [Video-start instructions](VIDEO_START_HERE_20261102.md) · [source-bound presentation JSON](VIDEO_EVIDENCE_MANIFEST_20261102.json) · [labeled judge figures](../FIGURES.md) · [V3 original timeline, 100 recorded epochs](FINAL_JUDGE_LANE_TRAINING_TIMELINE_V1.json).

### On magicSTUDIObox

Use a checkout of merged current `main` and open a localhost server, not the older independently developed branch's server:

```bash
cd /path/to/frontier-forms
python3 -m http.server 8894 --bind 127.0.0.1
open http://127.0.0.1:8894/docs/judges/present_v3.html
```

The localhost address is accessible on the machine running it, not externally. GitHub file views display HTML source, not necessarily a rendered presentation. GitHub Pages deployment is **NOT_VERIFIED**.

## What can be shown as actually observed

| Separate experiment | Existing result | Admission ceiling |
|---|---|---|
| FCO/FCG source-binding, L1×L3 vs frozen B0 | 18/54 → 30/54, **+22.22 percentage points** | Executed synthetic discovery, not prospective replication; model weights unchanged |
| Fitted learned OCR text post-correction A1 vs A0 | 14/46 → 22/46, **+17.39 percentage points**; Holm p ≈ 0.0234 | Admitted discovery; **not** Qwen weight fine-tuning |
| Trained YOLO crops before OCR | 14/46 → 9/46 | Negative/null; retain |
| Local logistic bounding-box classifier vs OpenCV | 540/540 both arms | Tie, no gain |
| Local RF medium bounding-box classifier vs OpenCV | 34/54 vs 54/54 fully localized forms | Negative |
| Teammate hosted-model synthetic pilot | 48 runs, 24 paired comparisons | Separately sourced API observations, not local/private training |

**Data/discovery records may be admitted into the research ledger; zero independently replicated scientific superiority claims are admitted.** Some original model training receipts remain in local/private storage and must not be inferred from the GitHub figure alone.

## Who did what

- **Claude Code / SWE–PM (amber):** local synthetic FHIR form server and B0, Qwen form-fill/zero-shot and local training work, YOLOv8n and learned OCR experiments, original PDFs, UI and figures.
- **ChatGPT / independent PI–PM reviewer (cyan):** research admission rules, source and reproducibility audits, FCO/FCG and LOMO statistical interpretation, Apple OCR/box challenger comparisons, negative preservation, Merkle roots and evidence manifests.
- **Teammates / API and serverless (violet):** PostgreSQL/Supabase implementation, synthetic hosted-model pilot, public-safe JSON writeback and sponsor integrations. Do not misattribute API results to local model training.

Attribution comes from exact source PRs, run/receipt metadata and review records. Where authorship is mixed or uncertain, retain **MIXED/UNKNOWN**, not invented ownership.

## The handoff

See [VIDEO_TEAM_HANDOFF_20261102.md](VIDEO_TEAM_HANDOFF_20261102.md) for role-specific remaining tasks, exact acceptance receipts, reproducibility instructions, preservation rules and deadline distinction. The prior [evidence-lane closeout](EVIDENCE_LANE_CLOSEOUT_HANDOFF_20261102.md) remains the independent predecessor; no training, data or model output is overwritten here.
