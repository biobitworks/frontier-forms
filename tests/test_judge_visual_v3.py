"""Source-backed judge visual fixes; no changes to frozen model receipt or old pages."""
from pathlib import Path
import hashlib
import unittest
from html.parser import HTMLParser
import json
ROOT=Path(__file__).resolve().parents[1]
def sha(name):
    return hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
class HTMLInspect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.imgs=[]
        self.links=[]
        self.meta=[]
        self.headings=[]
        self.ids=set()
    def handle_starttag(self,tag,attrs):
        p=dict(attrs)
        if 'id' in p:self.ids.add(p['id'])
        if tag=='img':self.imgs.append(p)
        if tag=='a':self.links.append(p.get('href',''))
        if tag=='meta':self.meta.append(p)
class JudgeVisualV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page=(ROOT/'docs/judges/present_v3.html').read_text(encoding='utf-8')
        cls.template=(ROOT/'scripts/redteam/present_page_template_v3.html').read_text(encoding='utf-8')
        cls.readme=(ROOT/'README.md').read_text(encoding='utf-8')
        cls.html=HTMLInspect();cls.html.feed(cls.page)
    def test_original_frozen_present_html_unchanged(self):
        audit=json.loads((ROOT/'docs/judges/FINAL_PUBLIC_DATA_COVERAGE_20261102_V1.json').read_text())
        self.assertEqual(sha('docs/judges/present.html'),audit['public_source_identity_checks']['docs/judges/present.html']['sha256'])
    def test_doctype_charset_and_team_headline(self):
        self.assertTrue(self.page.startswith('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">'))
        self.assertIn('team-wide evidence review',self.page)
        self.assertNotIn('Frontier Forms · Claude red-team lane · synthetic intake forms',self.page)
        self.assertIn('</html>',self.page)
        self.assertNotIn('â†',self.page)
        self.assertIn('18/54 → 30/54',self.page)
        self.assertIn('14/46 → 22/46',self.page)
    def test_source_links_and_navigation(self):
        for target in ['#h-team','#h-trained','#h-epochs','#h-models','#h-ledger']:
            self.assertIn(target,self.html.links)
            self.assertIn(target[1:],self.html.ids)
        paths=[p.get('src') for p in self.html.imgs if p.get('src','').startswith('figures/')]
        self.assertEqual(len(paths),2)
        for path in paths:
            self.assertTrue((ROOT/'docs/judges'/path).is_file(),path)
    def test_readme_sft_moved_below_verified_results(self):
        r=self.readme
        self.assertLess(r.index('## Judges — start here'),r.index('<!-- sft-status:start -->'))
        self.assertEqual(r.count('<!-- sft-status:start -->'),1)
        self.assertEqual(r.count('<!-- sft-status:end -->'),1)
        self.assertIn('docs/judges/present_v3.html',r)
        j=json.loads((ROOT/'evidence/forms_model/SFT_STATUS.json').read_text())
        self.assertEqual([v['status'] for v in j['runs']],['training','queued','queued'])
        self.assertIn('matched held-out Qwen-LoRA gain remains NOT_COMPUTED',r)
    def test_append_only_visual_successor_receipt(self):
        m=json.loads((ROOT/'docs/judges/PRESENTATION_VISUAL_V3_SUCCESSOR_20261102.json').read_text())
        self.assertEqual(m['status'],'PRESENTATION_ONLY_OBSERVED_BROWSER_RENDER_NOT_SCIENTIFIC_PROMOTION')
        self.assertEqual(m['parent_main_commit'],'9378a43ed91772c2458dc3635f8ac2f5266bc84d')
        self.assertEqual(m['new_merkle_root'],'NOT_COMPUTED')
        self.assertEqual(m['new_model_inference'],'NOT_EXECUTED')
        self.assertEqual(m['scientific_promotion'],'HOLD')
        for f,h in m['source_sha256'].items():
            self.assertEqual(sha(f),h,'BYTE_DRIFT:'+f)
        self.assertEqual(m['prior_present_v1_sha256'],sha('docs/judges/present.html'))
        self.assertEqual(m['prior_present_v2_sha256'],sha('docs/judges/present_v2.html'))
        self.assertEqual(m['source_sha256']['docs/judges/present_v3.html'],sha('docs/judges/present_v3.html'))
        self.assertEqual(m['reported_discoveries']['fco']['baseline'],18)
        self.assertEqual(m['reported_discoveries']['fitted_ocr']['challenger'],22)
    def test_no_new_model_or_science_claim(self):
        self.assertIn('No weights, new cohort, results, or Merkle roots were computed',self.page)
        self.assertIn('scientific admission unresolved',self.page)
        self.assertIn('replication NOT_TESTED',self.page)
        self.assertIn('HOLD · 0',self.page)
        self.assertIn('__DATA__',self.template)
        self.assertNotIn('__DATA__',self.page)
if __name__=='__main__':unittest.main()
