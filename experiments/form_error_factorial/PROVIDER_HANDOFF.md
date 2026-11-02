# Provider / checkpoint evidence handoff — Frontier Forms

**Updated:** 2026-11-02. **Program:** FRONTIER_FORMS only, not Cloudmer, knots or Vita DAISY.

## Implemented, executed, observed

The local test runner in `compare_vision_models.py` compared four modalities on the **same frozen synthetic intake PDF**:

| Arm | Input | Exact demographic fields | Observed latency | Exact checkpoint identity |
|---|---|---|---|---|
| Apple Vision | raster image | 8/8 | NOT_MEASURED | OS native; weight hash NOT_AVAILABLE |
| Apple PDFKit | original PDF text | 8/8 | NOT_MEASURED | OS native; weight hash NOT_AVAILABLE |
| local `qwen2.5vl:3b` | raster image directly | 8/8 | 40.905s | Ollama SHA-256 `fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1` |
| local `qwen3:1.7b` | Apple OCR text | 8/8 | 9.806s | Ollama SHA-256 `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7` |

Full per-field answers, raw model replies, prompt hashes, weights, time/tokens, source PDF/raster hashes, and Apple Vision bounding-box coordinates are in `sample_vision/model_field_answers.json`. The independent verifier recomputes its leaf Merkle root from declared bytes. This is **one synthetic form**, therefore no ranking, fine-tuning gain, AUROC or statistically supported model superiority is claimed.

**Apple Vision bounding boxes** are normalized as `[x, y, width, height]` with bottom-left origin. `vision_overlay.html` converts these into top-left CSS coordinates and displays **actual model answers** per corresponding field. Model arms reuse *Apple's* boxes; do not attribute those detections to a Qwen model.

## Teammate-provided inference adapter contract

Teammates own Fireworks, NVIDIA and any Mistral external inference. Do not send credentials to GitHub, Notion or the browser. Do not upload or transmit real patient data. For a synthetic form test, freeze the exact same image SHA-256 and field list; return one immutable JSON record per request and per field:

```json
{
  "schema": "frontier_forms.provider_field_receipt.v1",
  "status": "EXECUTED",
  "provider": "fireworks|nvidia|mistral|local",
  "model_id": "exact API model identifier",
  "model_revision": "explicit returned revision or UNKNOWN",
  "base_weight_sha256": "actual verified digest or null",
  "fine_tune_adapter_sha256": null,
  "effective_checkpoint_digest": "actual digest or null",
  "checkpoint_identity_status": "VERIFIED|REPORTED|UNKNOWN",
  "input_sha256": "sha256 of exact synthetic raster or PDF bytes",
  "prompt_sha256": "sha256 of exact prompt bytes",
  "generation_parameters": {"temperature": 0, "seed": null},
  "request_id": "actual provider ID or null",
  "raw_response_sha256": "sha256 of provider response bytes",
  "inference_elapsed_seconds": null,
  "tokens_input": null,
  "tokens_output": null,
  "fields": [
    {
      "field_id": "postcode",
      "answer": "02038",
      "bbox": {"page": 0, "xywh_norm_topleft": [0.1, 0.1, 0.3, 0.03]},
      "bbox_producer": "Apple Vision|YOLO|Mistral OCR|other|NONE",
      "field_confidence": null,
      "answer_source_ref": "input_sha256 + crop/line/source path"
    }
  ],
  "evaluation": {
    "source_gold_manifest_sha256": "actual independently frozen hash",
    "paired_case_ids_sha256": "actual digest",
    "accuracy": null,
    "mcnemar_exact_p": null,
    "patient_cluster_bootstrap_ci95": null,
    "auroc": null,
    "fco_parent": "exact predecessor receipt"
  }
}
```

An absent model weight digest MUST be `null`/`UNKNOWN`, not fabricated or inferred from the model name. Distinguish an Ollama package digest from upstream checkpoint bytes or a LoRA adapter checksum.

### Impact attribution

Report the **same field/case set** for each arm; compare unchanged model weights against module-on versus module-off (LOMO), and unchanged modules against different checkpoints. For each comparison, record the exact fields gained/lost, paired full-form endpoint, exact McNemar discordances, **patient-cluster** paired bootstrap CI, bbox IoU/F1 if ground-truth geometry is annotated, and separate continuous error-risk score AUROC if present. Only claim fine-tuning impact for a baseline/tuned **matched checkpoint family** under identical harness and held-out cases.

Use explicit module-specific labels:
`OCR_SOURCE = AppleVision|PDFKit|QwenVL|MistralOCR|YOLO+OCR`,
`FORM_FIELD_PARSER = deterministic|qwen3_1.7b|...`,
`SOURCE_BINDING = on|off`,
`NORMALIZATION = on|off`,
`VALIDATION = on|off`,
`PROVENANCE = on|off`.

A field bounding box does not establish the semantic accuracy of an answer. Its source label and text recognition result must be scored separately.

## Selection decision

- **RUN NOW:** Apple Vision bboxes + PDFKit + local 3B Qwen VLM + small 1.7B text extractor, as implemented, on the 100 synthetic patient form cohort once matched rendering and gold labels are frozen.
- **OPTIONAL:** YOLO-based form-region/field detector only after documented missed-box or reading-order cases; initialize on the smallest practical layout model and validate IoU and recall rather than assuming it recognizes text.
- **TEAMMATE / DEFERRED:** Fireworks vision inference using a verified *actually available* vision endpoint. Fireworks' OpenAI-compatible vision API accepts images, not PDFs natively. The Mistral OCR 4 processor with structured block boxes and confidence is a **Mistral Document AI API** capability; verify actual availability separately rather than assuming it is an exposed Fireworks model.
- **NO_PROMOTION:** One form with 8/8 across all modalities provides zero empirical advantage to any checkpoint.

## Commands

```bash
python3 experiments/form_error_factorial/verify_model_field_answers.py experiments/form_error_factorial/sample_vision
python3 -m unittest discover -s tests -p test_model_field_vision.py -v
python3 -m http.server 8893 --bind 127.0.0.1 --directory experiments/form_error_factorial
# Open http://127.0.0.1:8893/vision_overlay.html
```

New model executions append successor `sample_vision/model_field_answers_<run-id>.json` files. Never overwrite the original.
