# Frontier Forms — Verifiable EHR form extraction

**Status:** research prototype; NOT clinically validated. Objective: compare local and Fireworks inference for turning synthetic scanned medical forms into source-grounded, human-reviewed FHIR drafts. The intended customers are clinical operations and EHR integration teams. Primary business benefit to test: fewer unsupported fields and lower verified-form cost.

**Data:** MITRE Synthea provides *synthetic* patient records and is not itself an OCR benchmark. Epic technical specifications define a FHIR interoperability target, not a patient dataset. Rendering synthetic documents and field-level labels is an independent transformation. No live Epic API writes or PHI are authorized.

## Frozen lineage

- Longevity input snapshot: `LN-MINI-ec719d04c3707ca1cb`, 728 FCOs, root `5f9a7e51f1ee03d70d34e99358fe14230efa396f7fd851df21f424e6843f61b1`.
- Project freeze: `ASI-FRONTIER-9e4d4df8aa7a887e`, 15 ordered leaves, root `9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a`.
- Previous frozen project manifest: `public_export=NOT_AUTHORIZED`. This repository publishes a **locator projection**, not confidential frozen leaves, original data, weights or oracle.
- Previous 38 paired longevity *discovery* cases: Liquid 25/38, Insilico 27/38; exact McNemar p=0.6875; bootstrap 95% CI [−0.079,+0.184]; both improvement gates FAIL.
- All signatures NOT_SIGNED, MMR NOT_COMPUTED; no live Fireworks, clinical form evaluation or DGX training in these claims.

## How to review

```sh
python3 -m unittest discover -s tests -v
python3 scripts/verify_freeze.py --source-root /Users/byron/projects/active/fireworks-antigence-eval-20261102 --strict
python3 scripts/build_notebooks.py --check
```

The exact project freeze can be reverified only by a reviewer with authorization to access the original files on Studio; source-file verification is separate from checking a quoted digest. Never promote the public locator to an independently verified Merkle root.

See [custody](docs/CUSTODY.md), [protocol](docs/EXPERIMENT_PROTOCOL.md), [interoperability](docs/INTEGRATIONS.md), [lab notebook](docs/LAB_NOTEBOOK.md), and execution prompts. Each notebook follows requirements → inputs → analysis → outputs → receipt.

**Technology:** Synthea (synthetic EHR test records); open.epic FHIR specifications; local OCR/vision; Fireworks serverless inference; Antigence + Vita DAISY; future NVIDIA Megatron training. All nonexecuted integrations are explicitly NOT_TESTED.

References: https://synthea.mitre.org/downloads · https://open.epic.com/TechnicalSpecifications · https://github.com/NVIDIA/Megatron-LM · https://docs.fireworks.ai/
