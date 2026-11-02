import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from check_synthetic_json_policy import violations

class TestJsonPublication(unittest.TestCase):
    def test_good_json(self):
        self.assertEqual(violations(["data/forms_cohort_v1/bundles/test.json",
                                      "data/forms_cohort_v1/README.md",
                                      "evidence/forms_bbox/receipt.json"]),[])
    def test_reject_rendered_and_weights(self):
        x=violations(["data/forms_vision_v1/case.png",
                      "evidence/forms_apple/case.pdf",
                      "data/forms_sft_v1/train.jsonl",
                      "experiments/form_error_factorial/prebuilt_forms/a.html",
                      "experiments/form_error_factorial/weights.pt"])
        self.assertEqual(len(x),5)
if __name__=="__main__": unittest.main()
