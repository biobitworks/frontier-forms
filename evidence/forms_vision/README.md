# Vision arms on the synthetic form images

Every arm runs locally, with no hosted inference. Each one reads the same 57 rendered synthetic forms in `data/forms_vision_v1`:
- 3 blank forms
- 54 B0-filled test-split forms, of which 18 use the held-out urgent-care layout.

Gold is the DOM input box and the value written in it.

| arm | weights / tool | box recall IoU≥0.5 | mean IoU | label match | filled value read exactly | false boxes | s/page (median) |
|---|---|---|---|---|---|---|---|
| T1 Tesseract 5.5.3 (red-team runner) | eng.traineddata 7d4322bd… | n/a (text-line boxes) | n/a | 0.967 (found above box) | 0.787 | n/a | ~0.3 |
| V1 qwen2.5vl:3b (Ollama, Q4_K_M) | digest fb90415c… | 0.821 | 0.715 | 0.798 | 0.736 | 213 | 24.0 |
| V2 trained YOLOv8n field detector + Tesseract crop validator, seen layouts (72 test renders) | trained weights sha256 94ab462f… (not published) | 1.000 | 0.965 | class 0.999 | 0.350 (OCR on crop) | 5 | 0.41 |
| V2, held-out urgent-care layout (36 test renders) | same | 0.997 | 0.958 | class 0.780 | 0.124 (OCR on crop) | 16 | 0.30 |

Neither T1 nor V1 is a trained detector. They are inference baselines, and V2 is the trained one. V2 is scored on its own 108 test renders (default plus randomized layouts, 7 perturbation types), not the 57 images above, so compare its rows with care. V2 finds the boxes almost perfectly, even on the layout it never trained on, but its value validator is not usable yet: it catches 94% of wrong values on seen layouts (33% held-out) while flagging about 58% of correct values, because Tesseract misreads the small crops. Details: `../forms_detector/V2-yolov8n/summary.json`. Figures: `../FIGURES.html`. Text areas that hold long lists are cut off in the screenshots, so no image-only arm can read those values in full.
