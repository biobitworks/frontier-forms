# Fireworks Deploy — prioritized action ledger (post-deadline audit)

**Evidence status:** Administrative documentation only. Nov 2, 2026 16:30 PST was the build/submission deadline; do NOT modify or backdate the judged SHA, results, features or video after cutoff. A PR merged now is a post-deadline successor, not the judged artifact. Source: PI-supplied event rules; predecessor PR #53.

| Priority | Task | Acceptance receipt | Current state | Owner |
|---|---|---|---|---|
| P0 | Recover HackerSquad form submission confirmation and exact timestamp | submitted status, completed processing time <= 16:30 PST, screenshot or exported receipt | UNKNOWN | team lead |
| P0 | Recover exact frozen submitted Git commit | SHA, commit timestamp, comparison to form, no later modifications represented as judged | UNKNOWN | repository owner |
| P0 | Verify 2–5 registered in-person participants, check-in and team roster | approved registrations, check-in evidence, names as submitted | UNKNOWN | team lead |
| P0 | Verify public repo accessible signed-out | HTTP/browser access to submitted SHA and setup | NOT_TESTED | teammate |
| P0 | Verify <120-second video processed before cutoff and accessible | final video URL, duration, upload completion receipt | UNKNOWN | demo owner |
| P0 | Clarify general Fireworks optional vs listed prize Fireworks-required contradiction | written organizer ruling and sponsor use receipt if applicable | UNRESOLVED | team lead |
| P1 | Inventory actual named frontier baseline and same-case held-out results | baseline model/version, same cases and metric, case hashes, latency/cost, CI, pre-cutoff evidence | NOT_VERIFIED | evaluation owner |
| P1 | Reconcile PR #50/#51 figures and judges-pack links against submitted SHA | file existence at frozen SHA, figure labels, source leaves, working links | NOT_VERIFIED | documentation owner |
| P1 | Distinguish pre-event vs event-day commits and Claude vs ChatGPT contributions | PR/commit-by-time attribution ledger, assistance disclosure | PARTIAL | repository owner |
| P1 | Verify all model/detector gain claims and failures | frozen paired JSON, model hashes, source roots, negative/NULL records | PARTIAL | evaluation owner |
| P2 | Assemble reproduction instructions and clean-room review | dependency pins, commands, local synthetic fixtures, deterministic receipts | NOT_TESTED | reviewer |
| P2 | Prepare six-finalist in-person presentation and Q&A if eligible | speaker and presence confirmation | DEFERRED | team |
| P3 | Future-work: prospective unseen synthetic cohort, true frontier comparison and independent FCAR replicate | separately dated successor, NOT part of 2026-11-02 judged version | PROPOSED | research team |

## Judging rubric priorities
- Benchmark 40%: **BLOCKED** until actual named frontier-model matched held-out evidence is identified; B0 deterministic is not a frontier baseline. Do not invent new results after deadline.
- Business value 25%: clinical intake user and synthetic error reduction supported as motivation; production savings NOT_COMPUTED.
- Technical execution 20%: demonstrate frozen local form pipeline, source-binding, Merkle, LOMO, failures; confirm artifacts at submitted SHA.
- Demo 10%: video completion/access UNKNOWN.
- Documentation 5%: public access and reproduction NOT_TESTED.

## Verified pre-existing discovery result (not frontier superiority)
B0+L3 18/54 vs B0+L1+L3 30/54 full-form synthetic success, +22.22 pp; exact McNemar p=0.00048828125, Holm p=0.005859375, patient-cluster CI [0.0741,0.3704]. NOT_PROMOTED because rules were designed after inspecting failures; prospective independent replication NOT_TESTED. DAISY framework reused, DAISY-specific gain NOT_COMPUTED.

## Rule to close an item
Attach the original immutable receipt, owner, timestamp, submitted SHA association, and reviewer sign-off. No item is PASS from a promise, screenshot of a draft, or post-cutoff recomputation. Preserve FAILED, NEGATIVE, NULL, UNKNOWN, NOT_TESTED and NOT_COMPUTED.
