import sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'src'))
from frontier_forms.forms.templates import load_templates
from frontier_forms.forms.acceptance_preview import render_preview_html
from frontier_forms.forms.cohort import load_cohort
from frontier_forms.forms import b0
class T(unittest.TestCase):
 def test_cohort(self):
  m,b=load_cohort(R/'data/forms_cohort_v1/bundles');self.assertEqual(len(m),100)
  self.assertEqual(len({x.patient_id for x in m}),100)
 def test_styles_no_oracle(self):
  for t in load_templates().values():
   h=render_preview_html(t)
   self.assertIn('@media print',h)
   self.assertNotIn('canonical_key',h)
   self.assertEqual({x['name'] for x in b0.inspect_form(h)},{x['field_key'] for x in t['fields']})
