"""Regression tests for append-only training evidence heatmap."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("heatmap",ROOT/"scripts"/"validate_training_history.py")
lib=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)
class HeatmapHistoryTests(unittest.TestCase):
    def setUp(self): self.doc=json.loads((ROOT/"dashboard"/"training_history.json").read_text())
    def test_valid_history(self): self.assertEqual(lib.validate(self.doc),[])
    def test_no_supported_model_gains(self):
        self.assertEqual(sum(e["state"]=="SUPPORTED" for e in self.doc["events"]),0)
    def test_bad_parent(self):
        d=copy.deepcopy(self.doc); d["events"][1]["parent"]="invented"
        self.assertTrue(lib.validate(d))
    def test_forged_root(self):
        d=copy.deepcopy(self.doc); d["events"][1]["merkle_root"]="0"*64
        self.assertTrue(lib.validate(d))
    def test_forged_promotion(self):
        d=copy.deepcopy(self.doc); d["events"][-2]["state"]="SUPPORTED"
        self.assertTrue(lib.validate(d))
    def test_metric_integrity(self):
        d=copy.deepcopy(self.doc); d["events"][0]["metrics"]["paired_delta_pp"]=999
        self.assertTrue(lib.validate(d))
    def test_secrets_not_allowed(self):
        d=copy.deepcopy(self.doc); d["events"][0]["notes"]="DATABASE_URL=postgresql://something"
        self.assertTrue(lib.validate(d))
    def test_project_lanes_not_chained(self):
        e={x["id"]:x for x in self.doc["events"]}
        self.assertIsNone(e["VITA-DAISY-PARALLEL"]["parent"])
        self.assertIsNone(e["FF-LOCAL-B0-LOMO"]["parent"])
if __name__=="__main__": unittest.main()
