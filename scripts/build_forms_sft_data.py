#!/usr/bin/env python3
"""Write data/forms_sft_v1/{train,validation}.jsonl and MANIFEST.json (no test data)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frontier_forms.forms import sft_data  # noqa: E402
from frontier_forms.forms.cohort import cohort_root, load_cohort, sha256_bytes  # noqa: E402
from frontier_forms.forms.passport import build_passport  # noqa: E402
from frontier_forms.forms.templates import load_templates  # noqa: E402

members, bundles = load_cohort(ROOT / "data/forms_cohort_v1/bundles")
passports = {m.patient_id: build_passport(bundles[m.patient_id], m.path.name, f"SYN-{m.patient_id[:8]}") for m in members}
rows = sft_data.build(members, bundles, load_templates(), passports)
out = ROOT / "data/forms_sft_v1"
out.mkdir(parents=True, exist_ok=True)
man = {"dataset_id": "FF-FORMS-SFT-V1", "lane": "frontier-forms", "prompt_version": sft_data.PROMPT_VERSION,
       "cohort_root": cohort_root(members), "excluded": "test-split patients; urgent_care_history_v1 (held-out layout)"}
for split, rs in rows.items():
    data = b"".join(json.dumps(r, sort_keys=True).encode() + b"\n" for r in rs)
    (out / f"{split}.jsonl").write_bytes(data)
    man[split] = {"examples": len(rs), "patients": len({r['patient_id'] for r in rs}), "sha256": sha256_bytes(data)}
(out / "MANIFEST.json").write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
print(json.dumps(man, indent=1))
