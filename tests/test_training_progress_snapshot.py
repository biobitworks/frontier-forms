"""Immutable training progress, multiplicity and no-false-promotion regression tests."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts.verify_training_progress import verify,hash_tree,mcn

R=Path(__file__).resolve().parents[1]
D=R/"dashboard/training_progress_latest.json"

class TrainingProgressProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.view=json.loads(D.read_text())
        cls.path=R/cls.view["source_snapshot"]
        cls.events=cls.view["events"]
    def test_independent_merkle_replay(self):
        res=verify(self.path)
        self.assertEqual(res["root"],self.view["root"])
        self.assertEqual(res["root"],hash_tree(self.events))
        self.assertEqual(res["event_count"],len(self.events))
    def test_all_actual_snapshots_have_predecessors(self):
        cur=json.loads((self.path/"manifest.json").read_text())
        p=cur["predecessor_snapshot_path"]
        self.assertIsNotNone(p)
        previous=R/p
        self.assertEqual(json.loads((previous/"manifest.json").read_text())["root"],cur["predecessor_snapshot_root"])
        self.assertEqual(verify(previous)["root"],cur["predecessor_snapshot_root"])
    def test_holm_family_correction(self):
        for family,expected in [("fco_lomo",12),("detector_lomo",6)]:
            events=[e for e in self.events if e["family"]==family]
            self.assertEqual(len(events),expected)
            self.assertTrue(all(e["hypothesis_family_n"]==expected and e["promoted"] is False for e in events))
            self.assertTrue(all(e["holm_adjusted_p"]>=e["mcnemar_p_two_sided"] for e in events))
    def test_model_weights_not_confused_with_deterministic_rules(self):
        for e in self.events:
            if e["family"] in ("fco_lomo","detector_lomo"):
                self.assertIs(e["model_weights_changed"],False)
                self.assertIsNone(e["model_weights_sha256"])
            if e["family"]=="methodology_only":
                self.assertIsNone(e["delta"])
                self.assertEqual(e["status"],"NOT_COMPUTED")
    def test_qwen_has_no_invented_training_accuracy(self):
        event=next(e for e in self.events if e["family"]=="actual_training_snapshot")
        if len([p for p in event["points"] if p.get("val_loss") is not None])==1:
            self.assertEqual(event["status"],"OBSERVED_BASELINE_ONLY")
            self.assertIsNone(event["heldout_accuracy"])
            self.assertIsNone(event["delta_val_loss"])
            self.assertIsNone(event["model_weights_sha256"])
    def test_source_mutation_fails(self):
        with tempfile.TemporaryDirectory() as t:
            temp=Path(t)
            shutil.copy(self.path/"manifest.json",temp/"manifest.json")
            raw=(self.path/"events.jsonl").read_bytes()
            (temp/"events.jsonl").write_bytes(raw+b" \n")
            with self.assertRaises(AssertionError):
                verify(temp)
    def test_paired_gate_identity_and_ci(self):
        r=json.loads((R/"evidence/training_progress/PAIRED_GATE_SINGLE_FCG_L3_DEMO_V3.json").read_text())
        self.assertEqual(r["intervention"],"SINGLE_FCG_LEAF")
        self.assertEqual(r["weight_model_identity"],"NOT_APPLICABLE: deterministic FCO arms")
        self.assertTrue(r["matched_oracle_sha256"].startswith("NOT_COMPUTED"))
        self.assertEqual(r["paired"]["matched_patients"],18)
        self.assertEqual(r["paired"]["matched_cases"],54)
        self.assertEqual(mcn(r["paired"]["baseline_only"],r["paired"]["challenger_only"]),r["mcnemar_exact_two_sided"])
        self.assertGreater(r["patient_cluster_bootstrap95"][0],0)
        self.assertEqual(r["claim"],"DISCOVERY_ONLY_NO_CAUSAL_PROMOTION")

if __name__=="__main__":unittest.main()
