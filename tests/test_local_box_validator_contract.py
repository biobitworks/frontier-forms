import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUB=ROOT/"evidence"/"local_box_validator"
SCRIPT=ROOT/"experiments"/"local_box_validator"/"verify_receipts.py"
spec=importlib.util.spec_from_file_location("local_cv_receipts",SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class PublicVisionReceipts(unittest.TestCase):
    def test_synthetic_reports_all_three_scales(self):
        for size in ("tiny","small","medium"):
            p=PUB/("v2_"+size+".json")
            self.assertTrue(p.is_file(),str(p))
            x=json.loads(p.read_bytes())
            self.assertEqual(x["n_test_patient"],18)
            self.assertEqual(x["n_test_images"],54)
            self.assertEqual(x["n_validation_patient"],19)
            self.assertEqual(len(x["results"]),8)
            self.assertTrue(x["no_external_calls"])
            self.assertTrue(x["no_new_png_or_weights_pushed"])
            self.assertEqual(x["fco_merkle_root"],module.merkle(x["fco_leaves"]))
            for row in x["results"]:
                self.assertGreaterEqual(row["f1"],0)
                self.assertLessEqual(row["f1"],1)
                self.assertEqual(row["n_test_images"],54)
    def test_no_promoted_false_gain(self):
        for s in ("tiny","small","medium"):
            x=json.loads((PUB/("v2_"+s+".json")).read_bytes())
            cv=next(z for z in x["results"] if z["arm"]=="CV_B0_contours")
            full=next(z for z in x["results"] if z["arm"]=="RF_geometry+shape+pixels")
            self.assertEqual(cv["f1"],1.0)
            self.assertLessEqual(full["f1"],cv["f1"])
            self.assertIn("EXPLORATORY",x["claim_ceiling"])
    def test_mutating_merkle_leaf_breaks_commitment(self):
        x=json.loads((PUB/"v2_medium.json").read_bytes())
        bad=copy.deepcopy(x["fco_leaves"])
        bad[0]["n_images"]=53
        self.assertNotEqual(module.merkle(bad),x["fco_merkle_root"])
    def test_registry_predecessor_identical_bytes(self):
        registry=json.loads((PUB/"registry.json").read_bytes())
        self.assertEqual(len(registry["events"]),6)
        seen={}
        for event in registry["events"]:
            p=PUB/event["file"]
            self.assertEqual(module.hfile(p),event["public_sha256"])
            if event["parent"] is not None:
                self.assertIn(event["parent"],seen)
            seen[event["id"]]=event
        self.assertFalse(any(z.get("state")=="SUPPORTED_GAIN" for z in registry["events"]))
if __name__=="__main__":
    unittest.main()
