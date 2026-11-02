import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from check_synthetic_json_policy import violations,incremental_violations,git_blobs,PRE_POLICY_MAIN

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


class TestLegacyFrozenException(unittest.TestCase):
    def test_already_committed_legacy_bytes_unchanged(self):
        current=git_blobs("INDEX")
        baseline=git_blobs(PRE_POLICY_MAIN)
        problems,legacy=incremental_violations(current,baseline)
        self.assertEqual(problems,[])
        self.assertGreater(len(legacy),0)
    def test_modified_legacy_image_fails(self):
        current={"data/forms_vision_v1/example.png":"2222222"}
        baseline={"data/forms_vision_v1/example.png":"1111111"}
        bad,old=incremental_violations(current,baseline)
        self.assertEqual(len(bad),1)
        self.assertEqual(old,[])
    def test_added_json_allowed_modified_jsonl_rejected(self):
        current={"data/forms_vision_v1/existing.jsonl":"abc",
                 "data/forms_cohort_v1/new.json":"def"}
        baseline={"data/forms_vision_v1/existing.jsonl":"abc"}
        bad,old=incremental_violations(current,baseline)
        self.assertFalse(bad)
        current["data/forms_vision_v1/existing.jsonl"]="f00"
        bad,old=incremental_violations(current,baseline)
        self.assertEqual(len(bad),1)
        self.assertEqual(bad[0]["state"],"NEW_OR_CHANGED_REJECTED")
