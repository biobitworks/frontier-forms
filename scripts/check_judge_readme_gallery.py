#!/usr/bin/env python3
"""Ensure public judge README links and image previews resolve to committed local assets."""
import hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=(R/'README.md').read_text()
expected=[
 'docs/figures/gains_heatmap.png',
 'docs/figures/accomplishment_heatmap.png',
 'docs/figures/gains_heatmap.csv',
 'docs/judges/FIGURES.md',
 'docs/judges/VIDEO_START_HERE_20261102.md',
 'docs/judges/present.html',
 'docs/judges/figures/fig07_clean_boxes.png',
 'docs/judges/JUDGE_OUTCOME_HEATMAP_V1.html',
]
for p in expected:
 f=R/p
 assert f.is_file() and f.stat().st_size>0, f"MISSING_GALLERY_ASSET:{p}"
for p in expected[:6]:
 assert p in s, f"README_MISSING_LINK:{p}"
assert s.count('![Frontier Forms source-backed gains heatmap')==1
assert s.count('![Frontier Forms accomplishment heatmap')==1
assert '40d58ec71eb281db9ba2db19e7f7adf6' in s
assert 'Scientific promotion: HOLD' in s
print('JUDGE_README_GALLERY PASS',len(expected),'assets;',len([p for p in expected if (R/p).is_file()]),'local files exist')
