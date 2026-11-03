# Presentation successor V3 — visual and provenance review

**Purpose:** fix broken UTF-8 display, misleading Claude-only heading, and judge entry hierarchy without changing experiment bytes or claiming a trained-model gain.

| Surface | Predecessor observation | V3 successor change | Validation |
| --- | --- | --- | --- |
| Presentation characters | Unicode arrows/separators appeared as mojibake in a browser; original lacked charset | New V3 HTML5 doctype, language, UTF-8 declaration and complete document wrapper | Desktop headless Chrome render displays 18/54 → 30/54 and 14/46 → 22/46 correctly |
| Attribution | Earlier headline credited only Claude despite team/app and independent ChatGPT contributions | Team-wide headline, four conservative contributor lanes, explicit mixed/unknown lane | Browser screenshot and PR-source links |
| First impression | Detailed original, README leading with unfinished SFT | Two result cards, scientific hold, quick navigation, Gantt/training figures; README training moved below established evidence | Unit tests and unchanged updater block |
| Frozen scientific source | V1/V2 pages and receipt bytes already frozen | Preserve original pages, source JSON, model outputs; create V3 template, builder, page, preview and manifest | Successor SHA verification; zero new scientific claims |
| Interactive access | GitHub only exposes the HTML source, not a hosted browser app | Static screenshot preview available in README and Notion; local HTTP for charts | Local 200 and browser rendering observed |

## Scientific scope

FCO deterministic filtering on 54 synthetic complete forms improved 18/54 to 30/54 (+22.22 percentage points). Fitted OCR text correction on 46 different synthetic image renders improved 14/46 to 22/46 (+17.39 points; Holm-adjusted p=0.0234). These are not Qwen SFT neural model improvements. Prospective clinical replication has not occurred and FCAR scientific promotion remains HOLD.

## Append-only lineage

- present.html: frozen V1 predecessor.
- present_v2.html: frozen V2 generated successor.
- present_v3.html: V3 visual-only successor built by scripts/redteam/build_present_page_v3.py.
- PRESENTATION_VISUAL_V3_SUCCESSOR_20261102.json: SHA-256 identities of both predecessors, V3 page and template, sample synthetic sources and screenshot preview; no new Merkle root.
- figures/fig21_presentation_v3_preview_20261102.png: captured actual desktop browser screenshot, cropped to title, measured outcomes and navigation; no model inference.

## Access and open gates

Interactive HTML requires serving the repository over local HTTP and opening /docs/judges/present_v3.html. External judges can view the static README preview and linked figure PNGs or Notion research page. Anonymous Notion publication and external HackerSquad submission are UNKNOWN. Qwen SFT is ongoing and remains separated from the completed discovery figures.
