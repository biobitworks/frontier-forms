#!/usr/bin/env python3
"""Execute the red-team notebooks (notebooks/1*_redteam_*.ipynb) in an ephemeral kernel.

Append-only (addresses the sibling review's P1 on fixed output directories): the output directory
is evidence/notebook_runs_redteam_v<N> where N is the first unused version, so a re-run never
rewrites committed receipts. Executed notebooks are successor receipts; source notebooks are untouched.
Usage: python3 scripts/redteam/execute_redteam_notebooks.py [--only 10,13]
"""
from pathlib import Path
import argparse, hashlib, json, os, platform, sys, tempfile, time
R = Path(__file__).resolve().parent.parent.parent
ap = argparse.ArgumentParser(); ap.add_argument('--only', default='')
a = ap.parse_args()
only = {x.strip() for x in a.only.split(',') if x.strip()}
v = 1
while (R / f'evidence/notebook_runs_redteam_v{v}').exists():
    v += 1
out = R / f'evidence/notebook_runs_redteam_v{v}'
with tempfile.TemporaryDirectory(prefix='ff-redteam-kernels-') as tmp:
    ks = Path(tmp) / 'kernels' / 'frontierforms-evidence'; ks.mkdir(parents=True)
    (ks / 'kernel.json').write_text(json.dumps({'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
                                                'display_name': 'Frontier Forms Evidence', 'language': 'python'}))
    os.environ['JUPYTER_PATH'] = tmp + os.pathsep + os.environ.get('JUPYTER_PATH', '')
    os.environ['REDTEAM_RUN_DIR'] = str(out)
    import nbformat
    from nbclient import NotebookClient
    out.mkdir(parents=True, exist_ok=False)
    (out / 'outputs').mkdir()
    results = []
    for p in sorted((R / 'notebooks').glob('1*_redteam_*.ipynb')):
        if only and p.name[:2] not in only:
            continue
        nb = nbformat.read(str(p), as_version=4)
        state, error = 'PASS', None
        try:
            ran = NotebookClient(nb, timeout=600, kernel_name='frontierforms-evidence', resources={'metadata': {'path': str(R)}}).execute()
            op = out / (p.stem + '_EXECUTED.ipynb'); nbformat.write(ran, str(op))
            sha = hashlib.sha256(op.read_bytes()).hexdigest()
        except Exception as ex:
            state, error, sha = 'FAIL', type(ex).__name__ + ': ' + str(ex)[:900], None
            try:
                op = out / (p.stem + '_FAILED.ipynb'); nbformat.write(nb, str(op))
            except Exception:
                pass
        results.append({'notebook': p.name, 'execution': state, 'receipt_sha256': sha, 'error': error,
                        'source_sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
        print('NOTEBOOK', p.name, state, flush=True)
    outputs = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((out / 'outputs').glob('*.json'))}
    manifest = {'schema': 'notebook.execution.v2', 'run_dir': out.name, 'host': platform.node(), 'python': sys.version.split()[0],
                'executed_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'notebooks': results, 'outputs_sha256': outputs,
                'model_inference': 'NOT_RUN_IN_NOTEBOOKS_REPLAYED_FROM_RECEIPTS', 'append_only': True}
    (out / 'execution_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    if any(x['execution'] != 'PASS' for x in results):
        raise SystemExit(3)
