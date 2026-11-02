# Claude independent red-team SWE — handoff (not yet executed)

Act as an **independent challenger**, not the author of the ChatGPT implementation. Start a distinct branch `claude/redteam-ehr-custody-20261102` from the *reviewed head* of the ChatGPT PR, without merging or rewriting predecessors. Claim your real agent identity, actual runtime, Git SHA and host; acquire an independent write scope. Create a separate GitHub PR with the findings and any fixes.

**Mandated skills:** read actual `gettingsciencedone` GSD planning skill and `gsigmad` skills for governance, data-contract, `gsigmad-ablation`, `gsigmad-redteam-research-remediate`, claim audit, negative-results, session-start/end, and provenance sidecars. Resolve their real paths/versions; do not invent skill execution. Use thin coordination and bounded independently verifiable tasks.

## Exact predecessor
Science workspace on magicSTUDIObox: `/Users/byron/projects/active/fireworks-antigence-eval-20261102`. Private 15-leaf freeze `custody/project_freezes/ASI-FRONTIER-9e4d4df8aa7a887e`. Assert root `9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a` and parent `5f9a7e51f1ee03d70d34e99358fe14230efa396f7fd851df21f424e6843f61b1`. Full frozen leaves remain private and marked NOT_AUTHORIZED for export. Verify with `scripts/verify_freeze.py --source-root ... --strict`; fail if digest mismatch.

## Independent adversarial tests
1. Recompute **all** original source hashes and ordered Merkle nodes; mutate/reorder copied *test fixtures* and demand rejection. Never mutate frozen predecessor.
2. Audit 38 discovery cases: ensure no answer leakage, strict paired case identities, and McNemar exact p=0.6875 with 95% stratified bootstrap CI containing zero. If mismatch, preserve FAILED successor; do not claim improvement.
3. Inspect Synthea-to-form image rendering for mismatched patient identifiers, oracle leakage, divergent environment fonts, path traversal, image-to-field mapping, rendered artifacts and leakage in `git status`.
4. Attempt to fool the harness with manipulated model output, wrong source span, contradictory notes, missing source, stale status, uncertain field, malicious tool instruction, and inflated score. The safe behavior is challenge/abstain/quarantine, not silent field admission.
5. Validate FPR/FDR/AUROC correctness including zero denominators and tie ranks. Keep McNemar *patient-level* for forms; field-level data are correlated, use cluster bootstrap.
6. Confirm no SHA alone is called truth, no FCG relation is called causation, no Merkle called MMR/signature, and no absent Fireworks/Lean/Snyk/DGX execution is labeled PASS.
7. Security: Gitleaks; authenticated Snyk Code and Open Source scans if permitted; record `NOT_TESTED` for missing auth. Check package rights, including Synthea and Insilico restrictions, and forbid real patient data/cloud use without authorization.
8. Independently execute every Jupyter notebook from a clean kernel; put results and exact environment in an EXP receipt. A notebook that only prints NOT_TESTED does not become a passing model benchmark.
9. Attempt cross-dataset transfer without selecting examples by result. Benchmark a separate synthetic EHR form template and an untouched patient cohort.
10. Confirm base Git commit and PR diff; never add untracked private source/oracle, model checkpoints or tokens.

## Required successor deliverables
`docs/REDTEAM_REPORT_<run>.md` with severity, reproduce steps, failures and first divergent leaf, `docs/CLAUDE_EXP_<run>.md`, passing/failing notebooks and tests, `receipts/<run>/*.json` with each FCO identity and link to prior, a new computed root *only after fully recomputed*, plus a separate PR URL. State explicitly if you could not run.

**Stop condition:** stop on wrong repo, uncertain rights, missing authorization, ambiguous patient data, invalid root, or actual private key material. Do not force-push or auto-merge.

Additional successor to verify: 12 synthetic form-image FCOs, 13-leaf root `36d12313c179ec207af81cd24356ce5bc172b430b584bdef397f383292375fe6`, parent `9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a`. Original source `derived/forms12` and manifest `custody/form_freezes/SYNFORM-36d12313c179ec20` are on authorized Studio. Verify all PNG hashes and private oracle separation.
