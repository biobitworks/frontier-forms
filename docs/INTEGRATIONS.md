# Model and EHR integration matrix

| Component | Correct role | Status |
|---|---|---|
| MITRE Synthea | synthetic EHR source for independently rendered forms; not labeled OCR | source ZIP hashed, form pipeline NOT_TESTED in predecessor |
| open.epic | FHIR technical specs/SMART authentication; not a dataset | documentation only, live access NOT_TESTED |
| magicSTUDIObox Qwen2.5-VL | on-device OCR and field extraction comparator | model present; form task NOT_TESTED |
| Fireworks serverless | direct inference versus same-model DAISY and Antigence harness | environment key absent, NOT_TESTED |
| Azure Document Intelligence | OCR Read/Layout comparator | NOT_TESTED |
| NVIDIA Megatron | pre/post-training toolkit for CUDA-based DGX, not OCR | downloaded source, training NOT_TESTED |
| Snyk | code, dependency, license, IaC and agent security checks | NOT_TESTED in this repo |
| Antigence / FCG | provenance-aware challenge/abstain/admit control | proposed integration, NOT_TESTED |
| Epic/FHIR resource validation | syntactic+semantic FHIR R4 draft, human approval before write | NOT_TESTED |

No private patient data or credentials should enter the repo, prompts, or unaudited cloud APIs. Only simulated EHR drafts are in scope. Hold exact model, cases, prompts, temperature and pricing time across harness comparisons. Different weights imply a system comparison, not a clean harness ablation.

Sources: https://synthea.mitre.org/downloads ; https://open.epic.com/TechnicalSpecifications ; https://github.com/NVIDIA/Megatron-LM ; https://docs.fireworks.ai/ ; https://learn.microsoft.com/azure/ai-services/document-intelligence/ ; https://docs.snyk.io/.
