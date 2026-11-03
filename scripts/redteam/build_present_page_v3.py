#!/usr/bin/env python3
"""Build judge presentation v3; preserve immutable v1/v2 HTML and source evidence."""
import json
from pathlib import Path
from build_present_page import R,data
TEMPLATE=R/'scripts/redteam/present_page_template_v3.html'
OUT=R/'docs/judges/present_v3.html'
def main():
    source=TEMPLATE.read_text(encoding='utf-8')
    assert source.count('__DATA__')==1
    assert '<meta charset="utf-8">' in source
    html=source.replace('__DATA__',json.dumps(data(),separators=(',',':')).replace('</','<\\/'))
    OUT.write_text(html,encoding='utf-8')
    print('WROTE',OUT.relative_to(R),OUT.stat().st_size,'bytes')
if __name__=='__main__':main()
