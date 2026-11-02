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
PRE_POLICY_MAIN="2c89dd45870ec093e2c72319ec231aebda268510"
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

def git_blobs(ref,root=ROOT):
    """Return Git blob identities for a commit or the index."""
    cmd=["git","ls-files","-s","-z"] if ref=="INDEX" else ["git","ls-tree","-r","-z",ref]
    raw=subprocess.check_output(cmd,cwd=root)
    result={}
    for item in raw.split(bytes([0])):
        if not item:continue
        meta,path=item.split(bytes([9]),1)
        parts=meta.decode().split()
        if ref=="INDEX":
            if parts[-1]!="0":raise AssertionError("STAGED_CONFLICT")
            sha=parts[1]
        else:
            if parts[1]!="blob":continue
            sha=parts[2]
        result[path.decode()]=sha
    return result

def incremental_violations(current,baseline):
    """Reject every new/modified disallowed file; keep identical legacy blobs only."""
    bad=[];legacy=[]
    for item in violations(sorted(current)):
        name=item["path"]
        if baseline.get(name)==current.get(name):
            legacy.append({"path":name,"state":"LEGACY_UNCHANGED"})
        else:
            bad.append({**item,"state":"NEW_OR_CHANGED_REJECTED"})
    return bad,legacy

def main():
    current=git_blobs("INDEX")
    baseline=git_blobs(PRE_POLICY_MAIN)
    problems,legacy=incremental_violations(current,baseline)
    problems.extend(provenance_issues())
    print(json.dumps({"gate":"synthetic-json-only-successor",
       "pre_policy_main_commit":PRE_POLICY_MAIN,
       "files_checked":len(current),
       "legacy_unchanged_noncompliant":len(legacy),
       "status":"FAIL" if problems else "PASS",
       "violations":problems},indent=2))
    return 1 if problems else 0

if __name__=="__main__":
    raise SystemExit(main())
