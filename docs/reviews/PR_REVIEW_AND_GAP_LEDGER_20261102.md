# Frontier Forms PR integration and leaf-gain audit — 2026-11-02

Scope: `biobitworks/frontier-forms`; review based on GitHub PR metadata, local Git bytes and executed tests. No Supabase SQL query or production EHR interaction was performed.

## Branch/PR audit

| PR | Head at review | Evidence and scope | Decision |
|---|---|---|---|
| #4 | `08169f932d9ae097c8879936caa3b89e29da6c51` | Supabase nine-table schema migration, Synthea FHIR importer, app specs; already merged to `main@bba71d8578c30822a8bb546aa06097cd62d0c2ff` | RETAIN app baseline; runtime DB state remains NOT_TESTED |
| #3 | `da953450d33a721682191f77589c275e0b49731c` before remediation | FCO/Merkle custody, exact McNemar, notebooks; two reviewer findings; conflict with #4 `.gitignore` | Remediated in proposed successor; verify CI before merge |
| #1 | `46340989d56eaa0b35bb21e52dd2dbdd8e777bae` | Draft precursor with unique form-rendering, freeze-form scripts and dashboard; merge conflicts with current main | HOLD, inspect unique artifact provenance before adoption |
| #5 | `bf192ba7d48b8f78bc4f6004baa7cb32008b41b1` | Draft comparison/report only; importer UUID nondeterminism and source integrity issues reported | HOLD draft; incorporate findings, preserve review |
| #6 | `6e789da80c6bf29ce2f57b7fa7c6f2226a7f6f00` | Claude independent public synthetic freeze-red-team method; 13 tests passed locally on Python 3.12 | HOLD draft pending author readiness/CI/integration |
 
## Resolved on PR #3 successor

1. Corrected two in-line findings: before the public paired statistics exporter assigns the exact predecessor root, it recomputes input-byte SHA-256 and sizes for **both model result files and the locked split manifest**, against the root-pinned predecessor leaves. Missing or changed bytes now abort **before output writes**. A forged-source test was executed; negative tests added.
2. Notebook reruns now create a fresh `evidence/notebook_runs/RUN-<UTC>-<random-id>` directory with exclusive creation. Original receipts v1–v4 remain byte-unchanged; eight notebooks were executed to a new successor directory. `PASS` means offline protocol/fixture replay, NOT model inference.
3. Integrated PR #4 on the PR #3 branch without modifying its database migration or importer. Resolved add/add `.gitignore` by retaining the union of safe ignores and package exclusions.
4. New review Merkle successor binds the merged teammate app code, migration, repaired verification scripts, notebook replay receipts and this audit. Verify exact new root using the corresponding manifest and independent replay. Existing project/model input roots are historical and immutable.

## Independent red-team execution (PR #6)

Ran `python3.12 -m pytest -q` on the Claude lane: **13 passed**. Ran `python3.12 tools/public_redteam.py --out /tmp/ff-claude-pr6-fresh`: **30 challenge outcomes**. The synthetic *data freeze root* matched the declared `a10240801c05e0121bf6ec6f3ad07cae4073e2a3f7d0e88205a8ef67986ce4a5`. The *results root* differed from the committed report only because `IM01` attempts an OS-permission overwrite: the committed report was produced as root and recorded overwrite success, whereas the local non-root account observed `overwrite refused`. That is environment-sensitive negative evidence, not silent proof drift. Other 29 challenge records were unchanged.

**CRITICAL HASH COMPATIBILITY:** Claude's red-team tree uses RFC 6962 split-at-largest-power-of-two, a canonical JSON newline, and hex-encoded children. PR #3's original freeze uses duplicate-last for odd levels, canonical JSON without an embedded newline, and raw child digest bytes. The two schemes do NOT share a root namespace and roots cannot be compared directly or treated as model gains. Record scheme/version per leaf/root.

PR #6 tests demonstrate *tamper detection and custody robustness for a synthetic fixture*, not Fireworks EHR extraction performance. The fixture `.bin` is currently incompatible with PR #3's unconditional disallowed-extension CI gate; do not merge both unchanged without a narrowly controlled reviewed exception or conversion to non-binary fixture.

## What causes model gains? Current evidence ceiling

| Hypothesis / intervention | Dataset | Observed effect | Attribution |
|---|---|---|---|
| Liquid 1.2B vs Insilico Qwen3 0.6B | 38 frozen discovery cases | 25/38 vs 27/38; exact McNemar p=0.6875; interval includes zero | NEGATIVE superiority, different model weights; NOT an FCG/leaf gain |
| FCO context projection vs none | Matched model/cases | NOT_EXECUTED | NOT_COMPUTED |
| Full FCG vs no FCG, identical model | Matched model/cases | NOT_EXECUTED | NOT_COMPUTED |
| Single leaf removal/edge removal (LOMO) | Matched model/cases | NOT_EXECUTED | NOT_COMPUTED |
| Antigence admission vs unguarded | Matched model/cases | NOT_EXECUTED | NOT_COMPUTED |
| Claude synthetic byte binding vs incumbent index binding | Synthetic fixture (not a model benchmark) | Specific tamper attacks rejected where incumbent checks accepted | SUPPORTED detection difference under fixture only; NOT model gain |
| Supabase Synthea FHIR source vs prior CSV archive | Different source versions | No paired benchmark | NOT_TESTED and not interchangeable roots |

**Causal attribution protocol:** freeze the identical case list and gold oracle separately; pin model checkpoint/API version, temperature, seed where supported, prompt, parser, context budget, and training status; change *one leaf or edge* with a valid counterfactual; replay several inference seeds; use paired McNemar and patient-cluster bootstrap; apply multiplicity guard for many LOMO choices; record adverse events and cost. A root identifies a version; *root differences are not performance deltas*. Publish negative tests and leaf-impact descendant dependencies.

## Remaining highest-priority gaps

- **P0 source/database:** independently verify the reported Supabase schema, actual row counts, migrations, RLS policies, rights and transaction-consistent source snapshot. The helper's 100 patients / 8,252 fact/source rows are team-reported, NOT independently queried. Rotate any previously shared credentials before connection.
- **P0 stable identity:** PR #4 importer uses random UUIDs and delete/reinsert for source/facts; ordinal `SYN-xxxxx` may change referents. Use deterministic source-occurrence identifiers and an additive append-only provenance/outbox lane; do not rewrite the teammate's operational tables without review.
- **P0 statistical inference:** no actual matched Qwen/JEV/Fireworks EHR comparison, patient/template-held-out evaluation or controlled LOMO leaf attribution. No model-gain claim admitted.
- **P1 EHR security:** OCR-rendered dataset, clinically valid FHIR mappings, hallucination checks, blinded oracle and PHI/PII assessment still need independent evidence.
- **P1 reproducibility:** true cross-engine canonicalization and independent verifier, complete drift/invalidation tests, signature and MMR are NOT_TESTED/NOT_COMPUTED; Lean4 compilation and authenticated Snyk are NOT_TESTED.
- **P1 independent review:** Claude PR #6 is draft and fixture-driven; no independently confirmed model performance. PR #1 unique dashboard/form fixture work should be reviewed separately before closing/superseding.
- **P1 public CI:** a future merge of Claude's `.bin` fixture conflicts with current forbidden-extension scanner. Enforce explicit exception digest or serialize fixture as reviewable text.

All conclusions are bounded to tested machines and accessible source bytes. No Merkle root, hash or statistical delta in this report is used as a causal claim.
