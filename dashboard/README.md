# Training evidence heatmap — local/private Frontier Forms

**Scope:** Static, public-safe FCO/FCG validation evidence viewer. No Supabase or Epic credentials. The dashboard is **not a production model monitor** or a claim of newly observed improvement.

## Run locally

```bash
python3 scripts/validate_training_history.py dashboard/training_history.json
python3 -m unittest discover -s tests -p test_training_heatmap.py -v
cd dashboard && python3 -m http.server 8787 --bind 127.0.0.1
```

Open `http://127.0.0.1:8787/training_heatmap.html`. The HTML loads `training_history.json` as a read-only local file. No CDN or third-party endpoint calls are made.

## Current scope and exact meaning

- **n=100** means target number of distinct synthetic MITRE Synthea patients. The teammate reports 100 imported into PostgreSQL, but this PR does not query the database. Until independently verified with a read-only snapshot, N=100 is REPORTED, **not OBSERVED**.
- `open.epic` provides technical specifications and an Epic FHIR R4 sandbox with **different test patients**. It is not interchangeable with Synthea and it does not establish patient ground truth. Epic sandbox read operations are optional, scoped and authorization-gated; no production writes.
- Freeze teammate's local form-filling baseline **B0**, then create versioned successor modules and evaluate **Bfull**, followed by **LOMO = Bfull minus one module** with identical cases/weights/scorer and isolated intervention receipts.
- Local/private/approved model inference only. Fireworks/NVIDIA comparisons are deferred for this particular benchmark.
- This dashboard covers Frontier Forms only. Other programs are not tracked here.

## Scoring

For matched patient × form cases, freeze full-form binary correctness and critical-field guardrails. Run exact two-sided paired McNemar (discordant b/c counts), patient-cluster paired bootstrap with preregistered seed and CI. **AUROC is a separate incorrect/unsupported field detection task** requiring gold error labels and continuous risk/confidence scores. No AUROC can be inferred from two accuracies or binary McNemar tables.

Only append immutable event successors with exact input/output digests, model/checkpoint IDs when known, parser/scorer version, source archive/readback, test and benchmark receipts. **No roots are written unless actually computed from declared bytes** and independently verified. UNKNOWN ≠ PASS; statistical NEGATIVE ≠ code FAIL.

## Feed contract

`dashboard/training_history.json` is a **public-safe, static projection** containing historical and planned milestones; each cell opens its supporting GitHub source. Notion task database <https://app.notion.com/p/6e93fd12139a4246af794503436db290> contains explicit local-only acceptance criteria and outstanding tests.

Once the separate teammate performs GitHub JSON writeback, independently re-read exact committed bytes, verify SHA-256 and add a *new* run row. Corrections append successors; never rewrite a frozen source record. This page is not an authoritative PostgreSQL snapshot or a proof of live training.

Related PRs: [team Supabase MVP #4](https://github.com/biobitworks/frontier-forms/pull/4), [FCG comparison #5](https://github.com/biobitworks/frontier-forms/pull/5), [synthetic freeze method #6](https://github.com/biobitworks/frontier-forms/pull/6).
