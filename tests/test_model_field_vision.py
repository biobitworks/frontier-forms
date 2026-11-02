"""No-network regression tests for model answer/weight/box custody."""
import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/"experiments"/"form_error_factorial"
def load(name,file):
 spec=importlib.util.spec_from_file_location(name,BASE/file)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
m=load("vision_compare","compare_vision_models.py")
v=load("vision_verify","verify_model_field_answers.py")
class ModelEvidenceTests(unittest.TestCase):
 def test_real_receipt_recomputation(self):
  r=v.verify(BASE/"sample_vision"/"model_field_answers.json",BASE/"sample_vision"/"fixture.json",
    BASE/"sample_vision"/"vision_boxes.json",BASE/"sample_vision"/"synthetic_intake.pdf",
    BASE/"sample_vision"/"synthetic_intake.png")
  self.assertEqual(r["recorded_executed_models"],2)
  self.assertEqual(r["fields_per_arm"],8)
 def test_real_weight_digest_presence(self):
  x=json.loads((BASE/"sample_vision"/"model_field_answers.json").read_bytes())
  for arm in x["arms"]:
   if arm["status"]=="EXECUTED":
    self.assertEqual(len(arm["weight_digest"]),64)
    self.assertEqual(arm["model_id"],arm["runtime_model_id"])
    self.assertEqual(arm["fields_exact"],8)
 def test_json_non_object_rejected(self):
  self.assertEqual(m.parse_json_answer("[]")[1],"MODEL_NON_OBJECT")
 def test_non_json_rejected(self):
  self.assertEqual(m.parse_json_answer("I cannot read the form")[1],"MODEL_NON_JSON")
 def test_field_numbers_not_stripped(self):
  x={"first":"Lanny564","postcode":"02038"}
  fields=m.per_field(x,x,{"pages":[]})
  self.assertTrue(all(z["exact_match"] for z in fields))
  wrong=m.per_field({"first":"Lanny","postcode":"2038"},x,{"pages":[]})
  self.assertFalse(any(z["exact_match"] for z in wrong))
 def test_bbox_out_of_bounds_fails(self):
  data={"pages":[{"page_index":0,"lines":[{"text":"FIRST: A","bbox_norm_bl":[.95,.5,.2,.2],"confidence":.9}]}]}
  with self.assertRaisesRegex(ValueError,"out of bounds"):m.validate_bbox(data)
 def test_root_changes_on_changed_model_output(self):
  leaves=[{"arm":"a","answer":"one"},{"arm":"b","answer":"two"}]
  a=m.leafroot(leaves)
  leaves[0]["answer"]="three"
  self.assertNotEqual(a,m.leafroot(leaves))
if __name__=="__main__":unittest.main()
