# T1: Tesseract 5.5.3 on the forms vision set (run by the red-team thread)

The red-team thread ran this OCR on the 57 PNGs in data/forms_vision_v1 at commit a603980. Their sparse checkout held only the PNGs, so they never read GOLD_BOXES.json. Their runner is redteam/ehr/tesseract_generic.py (PR #11), and receipt.json records its version and hashes. Scoring is done here with scripts/score_ocr_lines.py.

Tesseract returns text-line boxes rather than input boxes, so box IoU is not comparable. Scoring uses label proximity instead: a value read is the set of OCR lines whose centre falls inside each gold input box.

| metric | value |
|---|---|
| labels found above their box | 0.967 (570 fields) |
| filled values read exactly | 0.787 |
| images where the printed injection note was read as text | 19 |

Where the misses come from:
- Text areas (conditions, medications, allergies). The screenshot only shows the visible part of a long value, and Tesseract reads the text-area resize handle as a trailing "J". This is a limit of the rendered image, so it applies to every vision arm.
- Character confusions: 555→585, Married→Martied, Krajcik→Krajeik, Hilll→Hill.
