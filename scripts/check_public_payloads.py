#!/usr/bin/env python3
"""Reject private payloads; exact-byte exception for public synthetic red-team fixture."""
import hashlib
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
ALLOWED_SYNTHETIC={
    "lanes/frontier-forms/dataset-freeze-redteam/fixtures/synthetic_pseudobulk_v1.bin":
    "6dcb568dfa631b1030f7e47d1f36029681986becee314f006c25e3739f2421b5",
}
DENIED={".safetensors",".parquet",".zip",".p12",".pfx",".pem",".key",".bin"}
def check(paths,root=ROOT):
    for name in paths:
        path=Path(name)
        if path.suffix.lower() not in DENIED:
            continue
        expected=ALLOWED_SYNTHETIC.get(path.as_posix())
        if not expected or not (root/path).is_file():
            raise AssertionError("PUBLIC_PROHIBITED_FILE "+path.as_posix())
        h=hashlib.sha256((root/path).read_bytes()).hexdigest()
        if h!=expected:
            raise AssertionError("PUBLIC_ALLOWLIST_HASH_MISMATCH "+path.as_posix())
    return "PASS"
if __name__=="__main__":
    raw=subprocess.check_output(["git","ls-files","-z"],cwd=ROOT)
    names=[x.decode() for x in raw.split(b"\0") if x]
    print("PUBLIC_FILE_POLICY",check(names),len(names))
