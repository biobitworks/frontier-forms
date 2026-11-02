# Medical form benchmark scaffold

This suite generates unbranded synthetic forms, deterministic gold answers and patient/form splits. A small real Pi-versus-Frontier-Tools development pilot and horizontal charts are available at `../charts/README.md`. The full held-out comparison and longitudinal study remain incomplete. See `../SUPERVISION_STATUS.md` for the local checkpoint.

From the repository root, with Python 3.12:

```sh
python3 -m venv bench/.venv
bench/.venv/bin/python -m pip install -r bench/harness/requirements.txt
bench/.venv/bin/python -m playwright install chromium
mkdir -p bench/harness/data
```

The current browser checks use the macOS ARM Chromium path in `check_forms.py`; adjust `CHROME` for a different platform or Playwright revision. The Pi sandbox requires macOS `sandbox-exec`, and `sandbox.py` currently expects Node in `~/.local/bin` on the development machine. This is a local research harness, not a portable production runner or a general security boundary.

Provide a private synthetic-only export at `bench/harness/data/synthea_passports.json`. If the repository's Supabase schema has been populated, `export_passports.py` can produce it using `DATABASE_URL` from the root `.env`. The database operation is read-only. Do not use real patient records.

```sh
bench/.venv/bin/python bench/harness/export_passports.py
bench/.venv/bin/python bench/harness/freeze.py
bench/.venv/bin/python bench/harness/check_forms.py --patients 100
bench/.venv/bin/python bench/harness/freeze.py --check
bench/.venv/bin/python bench/harness/serve.py --port 8787
```

The initial freeze writes generated files; `--refreeze` is permitted only before held-out model results have been inspected. These commands use private local data and do not call a model. The oracle and blank checks validate fixtures and scoring; their scores are not model accuracy measurements.

For the Pi runner, install pinned packages with `npm ci --prefix bench/pi`. Their normal install scripts are required for the agent-browser launcher; using `--ignore-scripts` requires repairing that launcher before runs will work. Configure only `FIREWORKS_API_KEY` in the root `.env`. Model calls incur API charges; run development cases first and estimate a full run before launching it. `fill.py --help` lists supported options. The computer-use adapter exercises CDP browser controls, not desktop interaction.

Patient exports, derived passports, schemas, answer keys, freeze manifests, rendered pages and raw agent logs are ignored by Git. Keep them in controlled local storage; a fresh clone needs the private export and a new build before validation. The job-form pilot's aggregate ablation metrics are tracked separately at `../results_ablation.jsonl`; older local result files are intentionally not published.

The vendored browser-tools skill comes from [badlogic/pi-skills](https://github.com/badlogic/pi-skills/tree/main/browser-tools), under the included MIT license, with a configurable CDP port. Its original upstream commit was not recorded during initial setup, so the smoke tests are not yet a fully pinned baseline.
