# gsigmad receipts (EXECUTED on magicSTUDIObox, scratch project)

* Tool: gsigmad 1.2.0b1, coordinate v1.2.1.1, source checkout `~/projects/active/gsigmad` at commit `d015d5e5feebc6edba6b673baf532b0fa093bb1f`, run as `uv run --project … python -m gsigmad`.
* Where: a throwaway project directory `/tmp/claude-redteam-20261102/gsigmad_proj`, NOT inside the frontier-forms checkout. The predecessor's `.gsigmad/README.md` statement that the repository itself is not gsigmad-initialized remains true. Initializing inside the repository (91 scaffold files, 62 skills) is proposed as a teammate decision, not done here.
* `init --yes` → exit 0. `register --type confirmatory` → exit 0, the tool allocated **EXP-2.1** (PROMPT-2.1 / TASK-2.1; registration prompt hash `711675d0…8fd2`, RFC 8785). This ID was issued by the tool, not invented, but it is scoped to the scratch project.
* `classify` of the discovery claim "25/38 vs 27/38, exact McNemar p=0.6875, superiority NEGATIVE" → **INFERRED** ("interpretive or statistical-result language detected without direct measurement details").
* `status` → 1 experiment, drift not triggered, `status_source=local_fallback`.
* Degradation observed on every call: `[DEGRADED] KG_DEGRADED — unavailable: kg` (knowledge-graph service at localhost:8531 not running). Governance ledger chain hashes are recorded in `governance_ledger_excerpt.jsonl`.
* NOT executed: `gsigmad run`, `audit`, `redteam EXP-2.1`, `power` (the registration YAML still carries TODO power/null-model fields; filling them is part of the proposed next experiment). No gate in the YAML is PASS.
