#!/usr/bin/env python3
"""Build the red-team lab notebook (source only; execution writes a separate receipt)."""
import nbformat as nbf
from pathlib import Path
R = Path(__file__).resolve().parent.parent
nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb.cells = [
    md("# 08 Claude red-team: root replay, custody attacks, context ablation\n"
       "Replays only PUBLIC artifacts. Model inference ran on magicSTUDIObox and MacBookPro via "
       "`redteam/ablation_runner.py`; this notebook recomputes every statistic from the public per-case bits. "
       "Hashes prove identity, not causality."),
    code("import json, subprocess, sys\nfrom pathlib import Path\nR = Path.cwd()\nsys.path.insert(0, str(R/'redteam'))\n"
         "r = subprocess.run([sys.executable, 'redteam/verify_roots.py', '--repo', '.'], capture_output=True, text=True, check=True)\n"
         "rep = json.loads(r.stdout)\nprint('pins reproduced from repo-only data:', rep['pins_reproduced'])\n"
         "print('728 root without source bytes:', rep['ln_mini_728'])"),
    code("dev = json.loads((R/'redteam/receipts/ROOT_REPLAY_magicSTUDIObox.json').read_text())\n"
         "print('magicSTUDIObox source-byte replay:', dev['pins_reproduced'], dev['predecessor_15']['source_bytes'])\n"
         "print({k: v for k, v in dev['ln_mini_728'].items() if k != 'pinned_root'})"),
    code("r = subprocess.run([sys.executable, '-m', 'unittest', 'tests.test_redteam_attacks', '-v'], capture_output=True, text=True)\n"
         "print(r.stderr[-2500:]); assert r.returncode == 0"),
    code("subprocess.run([sys.executable, 'redteam/analyze.py', 'report', '--results', 'redteam/results'], check=True)\n"
         "print((R/'redteam/results/EVIDENCE_MATRIX.md').read_text())"),
    code("m = json.loads((R/'redteam/results/EVIDENCE_MATRIX.json').read_text())\n"
         "for a in m['admission']: print(a)\n"
         "assert not any(a['admitted'].startswith('ADMIT') for a in m['admission'] if a['comparison'].startswith('K'))"),
    code("iv = json.loads(subprocess.run([sys.executable, 'redteam/impact_view.py', '.'], capture_output=True, text=True, check=True).stdout)\n"
         "print(json.dumps(iv['arm10_changed_source_version'], indent=1))"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, str(R / "notebooks/08_redteam_context_ablation.ipynb"))
print("WROTE notebooks/08_redteam_context_ablation.ipynb")
