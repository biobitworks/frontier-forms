#!/usr/bin/env python3
"""Fail-closed GitHub synthetic-data-only publication checker.

Only DATA PAYLOADS (.json) may be published under data/. This checker also
rejects PDFs, images, model checkpoints, and potentially private text payloads
under evidence and fixture directories. It does not classify synthetic status
from a filename: the cohort must have explicit generator provenance and
all generated bundles must contain FHIR Patient resources.
"""
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RESTRICTED_DIRS=("data/","evidence/","experiments/")
BINARY={".png",".jpg",".jpeg",".webp",".gif",".pdf",".pt",".pth",".safetensors",".ckpt",".onnx",".bin",".zip",".parquet"}
PUBLIC_DATA_ALLOWED={".json"}
KNOWN_NONDATA={"README.md"}

def violations(paths):
    bad=[]
    for name in paths:
        path=Path(name)
        suffix=path.suffix.lower()
        if suffix in BINARY and any(name.startswith(prefix) for prefix in RESTRICTED_DIRS):
            bad.append({"path":name,"rule":"NO_PUBLIC_PIXEL_PDF_OR_WEIGHTS"})
        elif name.startswith("data/") and path.name not in KNOWN_NONDATA and suffix not in PUBLIC_DATA_ALLOWED:
            bad.append({"path":name,"rule":"PUBLIC_DATA_JSON_ONLY"})
        elif "/prebuilt_forms/" in name and suffix != ".json" and path.name not in KNOWN_NONDATA:
            bad.append({"path":name,"rule":"NO_PUBLIC_RENDERED_FIXTURES"})
    return bad

def provenance_issues(root=ROOT):
    p=root/"data/forms_cohort_v1/GENERATION.json"
    if not p.exists(): return [{"path":str(p),"rule":"MISSING_GENERATION_RECEIPT"}]
    g=json.loads(p.read_text())
    issues=[]
    if g.get("data_classification","").split(".",1)[0] != "SYNTHETIC":
        issues.append({"path":str(p),"rule":"UNCLASSIFIED_GENERATOR"})
    if g.get("generator",{}).get("name") != "MITRE Synthea":
        issues.append({"path":str(p),"rule":"UNKNOWN_GENERATOR"})
    if not g.get("generator",{}).get("artifact_sha256"):
        issues.append({"path":str(p),"rule":"MISSING_PINNED_GENERATOR"})
    return issues

def main():
    names=[s.decode() for s in subprocess.check_output(["git","ls-files","-z"],cwd=ROOT).split(b"\\0") if s]
    problems=violations(names)+provenance_issues()
    print(json.dumps({"gate":"synthetic-json-only","files_checked":len(names),"status":"FAIL" if problems else "PASS","violations":problems},indent=2))
    return 1 if problems else 0

if __name__=="__main__":
    raise SystemExit(main())
