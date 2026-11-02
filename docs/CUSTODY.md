# Source-of-truth custody contract

The authority is the exact-byte source, atom/FCO, typed FCG edge, transformation receipt, measurement, bounded claim and immutable artifact. GitHub is a *review and synchronization* surface; a content hash is byte identity, not correctness or causality.

The original project freeze lives at `fireworks-antigence-eval-20261102/custody/project_freezes/ASI-FRONTIER-9e4d4df8aa7a887e` on magicSTUDIObox. Ordered-leaf scheme: leaf SHA256(0x00 || compact sorted JSON UTF-8); internal SHA256(0x01 || left 32-byte digest || right 32-byte digest); duplicate the last digest at odd width. Predecessor root: `5f9a7e51f1ee03d70d34e99358fe14230efa396f7fd851df21f424e6843f61b1`. Project freeze root: `9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a`.

Public release of the predecessor's original leaves is NOT_AUTHORIZED; `governance/public_projection.json` records non-secret locators and evidence states only. Run `scripts/verify_freeze.py` against authorized original data for independent cryptographic recomputation. It verifies the raw file hashes as well as the leaf and parent hashes.

For every source, actor, model, tool, API call, Git change, prediction, statistical test, safety finding, and human approval, record a separate FCO with content identity and occurrence identity, input/output bytes or restricted pointer, execution environment and typed dependency edges. Corrections produce successor state, never overwrite their predecessors. No MMR without ordered leaves/peaks/root and verification; no SIGNED without independently checked signature.

Negative and incomplete results must persist: PROPOSED, IMPLEMENTED, EXECUTED, OBSERVED, SUPPORTED, FAILED, NEGATIVE, NULL, DEFERRED, NOT_TESTED, NOT_COMPUTED, UNKNOWN.

For healthcare: synthetic patient record → rendered form → image spans → OCR fields → Antigence admission → draft FHIR resource → human approval. Actual EHR write is NOT_AUTHORIZED. Do not send hidden answer labels to models.
