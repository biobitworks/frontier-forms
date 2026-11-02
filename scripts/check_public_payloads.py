#!/usr/bin/env python3
"""Reject private payloads. Exact-byte exceptions only, by path and SHA-256 (none at present)."""
import hashlib
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
ALLOWED_SYNTHETIC={}
DENIED={".safetensors",".parquet",".zip",".p12",".pfx",".pem",".key",".bin"}
def check(paths,root=ROOT,allowed=None):
    allowed=ALLOWED_SYNTHETIC if allowed is None else allowed
    for name in paths:
        path=Path(name)
        if path.suffix.lower() not in DENIED:
            continue
        expected=allowed.get(path.as_posix())
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
