"""Frontier Forms FCAR policy mutations; no new training or external calls."""
from __future__ import annotations
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fcar", ROOT/"scripts/check_fcar_admission.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class FreezeChallengeReplicateAdmitPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.freeze=json.loads((ROOT/"evidence/forms_b0/B0_FREEZE_V1.json").read_text())
        cls.graph=json.loads((ROOT/"evidence/forms_arms/run_v1/FCG_ARMS_V1.json").read_text())
        cls.pointer=json.loads((ROOT/"dashboard/training_progress_latest.json").read_text())
        cls.snapshot=json.loads((ROOT/cls.pointer["source_snapshot"]/"manifest.json").read_text())

    def check(self, mutate=None):
        f,g,p,s=copy.deepcopy((self.freeze,self.graph,self.pointer,self.snapshot))
        if mutate:mutate(f,g,p,s)
        return gate.assess(f,g,p,s)

    def test_current_is_hold(self):
        r=self.check()
        self.assertEqual(r["admit"]["state"],"HOLD_NO_INDEPENDENT_PI_ADMISSION")
        self.assertTrue(r["boundary"]["methodology_only"])
        self.assertEqual(r["replicate"]["independent_prospective_replication"],"NOT_TESTED")
        self.assertFalse(r["admit"]["clinical_or_model_superiority_supported"])

    def test_foreign_dataset_rejected(self):
        with self.assertRaisesRegex(ValueError,"CROSS_PROGRAM_SOURCE"):
            self.check(lambda f,g,p,s: f.__setitem__("lane","vita-daisy"))

    def test_unmatched_cohort_rejected(self):
        with self.assertRaisesRegex(ValueError,"FROZEN_COHORT_ROOT_MISMATCH"):
            self.check(lambda f,g,p,s: g.__setitem__("dataset_root","0"*64))

    def test_foreign_weight_transfer_rejected(self):
        with self.assertRaisesRegex(ValueError,"DAISY_MEASURED_EVIDENCE_TRANSFER"):
            self.check(lambda f,g,p,s: next(e for e in p["events"] if e["family"]=="methodology_only").__setitem__("model_weights_sha256","a"*64))

    def test_foreign_gain_rejected(self):
        with self.assertRaisesRegex(ValueError,"DAISY_MEASURED_EVIDENCE_TRANSFER"):
            self.check(lambda f,g,p,s: next(e for e in p["events"] if e["family"]=="methodology_only").__setitem__("delta",0.02))

    def test_foreign_program_root_rejected(self):
        with self.assertRaisesRegex(ValueError,"DAISY_MEASURED_EVIDENCE_TRANSFER"):
            self.check(lambda f,g,p,s: next(e for e in p["events"] if e["family"]=="methodology_only").__setitem__("source_root","f"*64))

    def test_unreproduced_promotion_rejected(self):
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_PROMOTION"):
            self.check(lambda f,g,p,s: next(e for e in p["events"] if e["family"]=="fco_lomo").__setitem__("promoted",True))

    def test_status_promoted_without_receipt_rejected(self):
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_PROMOTION"):
            self.check(lambda f,g,p,s: next(e for e in p["events"] if e["family"]=="fco_lomo").__setitem__("status","SUPPORTED_GAIN"))

    def test_foreign_model_in_scientific_arm_rejected(self):
        with self.assertRaisesRegex(ValueError,"FOREIGN_MODEL_CHECKPOINT_IN_FORMS"):
            self.check(lambda f,g,p,s: next(e for e in p["events"] if e["family"]=="fco_lomo").__setitem__("model","Vita DAISY neural weights"))

    def test_duplicate_id_rejected(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_EVENT_ID"):
            self.check(lambda f,g,p,s: p["events"].append(copy.deepcopy(p["events"][0])))

    def test_pointer_corruption_rejected(self):
        with self.assertRaisesRegex(ValueError,"POINTER_SNAPSHOT_ROOT_MISMATCH"):
            self.check(lambda f,g,p,s: p.__setitem__("root","1"*64))

if __name__=="__main__":
    unittest.main()
