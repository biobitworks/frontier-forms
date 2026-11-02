# Apple-native comparison arm: Vision OCR + PDFKit (Preview's form engine)

Run v1 was executed on MacBookPro (arm64, macOS 27.2) with `tools/apple_forms/AppleForms.swift`, which uses PDFKit and Vision with the CPU pinned. A second full run gave byte-identical predictions. Both arms apply the frozen B0 mapping rules, so the only difference from B0 is the form front end.

- **A1 (OCR labels + PDFKit fill):** Vision read every printed label from the frozen PDF forms in `forms/`. It misread one label, "Weight (lb)" as "Weight (Ib)", but the keyword rules still matched it. PDFKit then filled the widgets as Preview would. Every form outcome is identical to B0 (218/218 pairs agree).
- **A2 (A1 + OCR read-back of the filled PDF):** field accuracy fell from 0.856 to 0.802 and full-form success from 0.463 to 0.454. Two forms that B0 got right failed (exact McNemar p=0.5, not significant). The read-back exposed two failure modes:
  1. Dropdown (choice) values set through PDFKit do not render on the flattened page, so OCR reads them as blank. Smoking-field accuracy dropped from 1.00 to 0.23.
  2. Long medication lists overflow the multi-line box and are cut off. Accuracy fell from 1.00 to 0.77 on the intake form and to 0.89 on the urgent-care form.

`run_v1/samples/` holds two filled PDFs per form, each paired with its OCR read-back JSON, for spot checks.
