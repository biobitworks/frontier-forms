# Frontier Forms open tasks

Opened 2026-11-02 from the gap analysis in `docs/reviews/GAP_ANALYSIS_20261102.md` (PR #29). That file holds the evidence for each gap; this file only tracks who does what and when a task counts as done. Each task has a GitHub issue, and the issue is where discussion and sign-offs go.

Status values: **OPEN** (not started), **IN PROGRESS**, **BLOCKED** (waiting on a person or a machine), **DONE** (acceptance criteria met, evidence on main).

Standing rules for every task: inference is local only (local Qwen models, no hosted providers); weights and credentials never go in git; new results are new arms or new evidence directories, never edits to frozen ones; no jobs run on magicSTUDIObox (training and vision runs use MacBookPro).

| ID | Task | Owner | Status | Issue |
|---|---|---|---|---|
| T01 | Fresh replication cohort | Claude (forms thread); Byron approves prereg | OPEN | #31 |
| T02 | Sign-off on two oracle rules | **Byron** | BLOCKED on Byron | #32 |
| T03 | Noisy and scanned form renders | Claude (forms thread) | OPEN | #33 |
| T04 | Prompt-injection filter | Claude (forms thread) | OPEN | #34 |
| T05 | Cost and latency per correct form | Claude (forms thread) | OPEN | #35 |
| T06 | Review PR #3's later changes | Review lane (ChatGPT PI/PM) | OPEN | #36 |
| T07 | N=100 readback from teammate DB | Byron decides N/A or readback; Claude runs it | BLOCKED on Byron | #37 |
| T08 | Trained-model result (SFT on MacBookPro) | Claude (forms thread) | IN PROGRESS (M0 running; M1 to restart) | #38 |
| T09 | Vision validator (V2) results | Claude (forms thread) | IN PROGRESS (run on MacBookPro) | #40 |
| T10 | Close draft PR #1 as superseded | **Byron** approves; Claude checks and closes | BLOCKED on Byron | #41 |

## Acceptance criteria

### T01 Fresh replication cohort (#31)
The test patients were seen before L1–L3 were designed, so the 0.333 → 0.556 lift is discovery grade.
- Preregistration committed before any arm sees the data: new Synthea seed (e.g. `-s 20261103`), arms and pins, metrics, decision rule.
- Cohort generated with the pinned Synthea jar; root hash recorded; byte-reproducible on a second run.
- B0-v1, A1 (B0+L1+L2+L3) and any trained arm scored once, with no code changes after unblinding.
- Result committed with ledger rows whether it replicates or not.

### T02 Oracle-rule sign-off (#32)
Rules: (1) conditions count disorders only; (2) no allergy record means "ask the patient".
- Byron approves each rule or states a change on the issue.
- A change becomes oracle-v2 as a new file; oracle-v1 stays; all arms rescored under both.
- Decision recorded in the evidence freeze file.

### T03 Noisy and scanned forms (#33)
- Seeded degradation set of the 54 test forms (blur, skew, JPEG, fax binarization, a handwriting-style fill), parameters committed before scoring.
- Tesseract, Apple Vision and qwen2.5vl scored clean vs degraded with the same scorer, per perturbation.

### T04 Prompt-injection filter (#34)
- Deterministic, versioned filter that flags or strips instruction-like text before any model reads it.
- Scored on `data/forms_vision_inject_v1` and the clean set: pass-through rate (target 0) and false-strip rate on clean fields (target ≤1%).
- Filter on/off is its own ledger column.

### T05 Cost and latency per correct form (#35)
- `seconds_per_correct_form` (and machine-hours or energy where measurable, host recorded) added to every arm summary on the 54-form test split.
- Arms without timing show NOT_RECORDED; unit test on a fixture.

### T06 Review of PR #3's later changes (#36)
- Commit range stated by SHA; findings in `docs/reviews/`, each marked fixed, accepted risk, or follow-up issue.

### T07 N=100 readback (#37)
- Either Byron marks it N/A (transformed JSON is the source of truth) and the issue closes as not planned,
- or patients and facts are recounted from the teammate's transformed JSON export, with its SHA-256, against the reported 100 / 8,252. That cohort is never mixed with `forms_cohort_v1`.

### T08 Trained-model result (#38)
M1 SFT was stopped on the Studio at 23:15Z without an adapter; it restarts on MacBookPro.
- M0 (base), M1 (SFT) and M2 (qwen3:1.7b) scored on the same 54 test forms and oracle.
- Each ledger row: weights SHA-256, FCG harness on/off, outcome delta vs B0-v1 (0.333), per-field raw model answers.
- M1 and M1+harness reported separately; McNemar and patient-cluster CI; weights stay out of git.

### T09 Vision validator results (#40)
- V2 run committed: flag recall and false-flag rate per perturbation type on the held-out layout, with model identity hash.
- Compared with the contour control and D2 on the same images; summary says whether the gap is closed.

### T10 Close draft PR #1 (#41)
- List what in #1 is not on main (expected: dashboard/form fixtures, notebook 05 stub); carry anything worth keeping into a new PR.
- Close #1 only after Byron approves, with a comment pointing to the superseding PRs.

## Updating this file
When a task changes state, update its row and link the evidence (PR or commit). Close the issue when the row says DONE.
