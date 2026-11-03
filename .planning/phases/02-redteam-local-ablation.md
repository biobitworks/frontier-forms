# GSD Phase 02 — Claude red-team: local model lanes and FCO/FCG/Antigence ablation

Parent: PR #3 head `da953450d33a721682191f77589c275e0b49731c`; predecessor roots 15-leaf `9e4d4df8…d3a9a`, 728-input `5f9a7e51…61b1`, review `2f1cfafd…95a2`.
Lane branch: `redteam/claude-fcg-local-ablation-20261102`. gsigmad registration of the confirmatory hypothesis: EXP-2.1 in a scratch project (see `evidence/redteam/gsigmad/`).

EXECUTED (receipts under `evidence/redteam/`): independent Merkle replay on the source host; L0/L1/L2 Ollama lanes and L3 transformers lane over the frozen discovery (38) and heldout (39) partitions with direct / FCO / FCG / injection / forged-leaf / removed-edge / verdict / option-swap arms; L0 cold-restart replay; VLM extraction over the 12 frozen synthetic forms with identity + consistency admission and draft FHIR; Lean 4.15 compile of `lean/Admission.lean`; verifier attack matrix (EXP-013); gitleaks on the pushed branch.

NEGATIVE / NULL (see report): see `docs/reviews/CLAUDE_REDTEAM_REPORT.md` section 10 for the per-question verdicts; discovery can only generate hypotheses; heldout rows carry the admission decision.

FINDINGS (structural): F-01 duplicate-last-leaf root collision (count bound only by unsigned manifest; verifier accepts a forged count); F-02 review-root verifier pinned to the working tree (CI would fail on any later edit; fixed by pinning to `da953450`); F-03 free-text system-prompt "context projection" changes the output format of instruction models so strict-letter accuracy collapses while content may be unchanged (format gate turns it into abstention).

BLOCKED / NOT_TESTED: Fireworks L4/L5 (no credential, CC BY-NC transfer unauthorized), Snyk (auth error SNYK-0005), NVIDIA/Megatron training (no CUDA GPU), live Supabase snapshot (no authorized read-only connection presented), Epic (specification only), MMR and signatures (NOT_COMPUTED / NOT_SIGNED), gsigmad run/audit/redteam gates (registration only).

HOLD: no clinical claims; no raw data export; no merge of PR #3 or of this PR by the lane itself; no process on magicSTUDIObox stopped or modified.

NEXT (teammate-reviewed): see report section 10.8.
