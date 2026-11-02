# Vision arms on the synthetic form images

Every arm runs locally, with no hosted inference. Each one reads the same 57 rendered synthetic forms in `data/forms_vision_v1`:
- 3 blank forms
- 54 B0-filled test-split forms, of which 18 use the held-out urgent-care layout.

Gold is the DOM input box and the value written in it.

| arm | weights / tool | box recall IoU≥0.5 | mean IoU | label match | filled value read exactly | false boxes | s/page (median) |
|---|---|---|---|---|---|---|---|
| T1 Tesseract 5.5.3 (red-team runner) | eng.traineddata 7d4322bd… | n/a (text-line boxes) | n/a | 0.967 (found above box) | 0.787 | n/a | ~0.3 |
| V1 qwen2.5vl:3b (Ollama, Q4_K_M) | digest fb90415c… | 0.821 | 0.715 | 0.798 | 0.736 | 213 | 24.0 |
| V2 trained YOLOv8n field detector + Tesseract validator | see `../forms_detector/V2-yolov8n/receipt.json` | see that folder | | | | | |

Neither T1 nor V1 is a trained detector. They are inference baselines, and V2 is the trained one. Text areas that hold long lists are cut off in the screenshots, so no image-only arm can read those values in full.
