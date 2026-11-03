"""Deterministic audit: completeness, nonpromotion, source hashes, Merkle index."""
import importlib.util,json,hashlib,copy,unittest,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("promotion",ROOT/"scripts/build_outcome_ledger.py")
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)
OUT=ROOT/"evidence/governance/OUTCOMES_AND_PROMOTIONS_20261102_V2.json"
def frozen_bytes(commit,path):
 return subprocess.check_output(["git","show",commit+":"+path],cwd=ROOT)
class OutcomeLedgerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=json.loads(OUT.read_bytes())
 def test_source_complete(self):
  self.assertEqual(self.d["evidence_counts"]["total"],24)
  self.assertEqual(len(self.d["scientific_events"]),24)
  self.assertEqual(self.d["evidence_counts"]["by_status"]["DISCOVERY_POSITIVE_NOT_PROMOTED"],8)
  self.assertEqual(self.d["evidence_counts"]["by_status"]["NEGATIVE_NO_GAIN"],4)
  self.assertEqual(self.d["evidence_counts"]["by_status"]["NEGATIVE_OR_TIE"],10)
 def test_not_promoted(self):
  self.assertEqual(self.d["admission"]["scientifically_supported_promotions"],0)
  self.assertEqual(self.d["admission"]["prospective_replication"],"NOT_TESTED")
  self.assertTrue(all(x["scientific_promotion"]=="NOT_ADMITTED" for x in self.d["scientific_events"]))
 def test_method_transfer_has_no_weights_or_gains(self):
  mth=next(x for x in self.d["scientific_events"] if x["family"]=="methodology_only")
  self.assertIsNone(mth["model_weights_sha256"])
  self.assertIsNone(mth["delta"])
  self.assertEqual(mth["status"],"NOT_COMPUTED")
 def test_inventory_integrity(self):
  items=self.d["inventory"]
  self.assertEqual(len(items),self.d["inventory_count"])
  self.assertEqual(len({x["path"] for x in items}),len(items))
  self.assertEqual(m.merkle(items),self.d["inventory_sha256_merkle_root"])
  for x in items:
   self.assertEqual(m.sha(frozen_bytes(self.d["parent_main_commit"],x["path"])),x["sha256"])
 def test_corruption_changes_root(self):
  items=copy.deepcopy(self.d["inventory"])
  items[0]["sha256"]="0"*64
  self.assertNotEqual(m.merkle(items),self.d["inventory_sha256_merkle_root"])
 def test_source_receipts_match(self):
  for path,expected in self.d["source_sha256"].items():
   self.assertEqual(m.sha(frozen_bytes(self.d["parent_main_commit"],path)),expected)
 def test_frozen_source_snapshot_not_current_head(self):
  parent=self.d["parent_main_commit"]
  self.assertEqual(self.d["inventory_sha256_merkle_root"],m.merkle(self.d["inventory"]))
  self.assertNotEqual(parent,"")
  self.assertEqual(len(frozen_bytes(parent,"bench/charts/live_metrics.json"))>0,True)
 def test_bench_matched_and_quality_loss_preserved(self):
  bench=self.d["teammate_hosted_benchmark"]
  self.assertEqual(bench["n_runs"],48)
  self.assertEqual(bench["n_matched_pairs"],24)
  self.assertEqual(len(bench["run_metrics"]),48)
  self.assertGreater(bench["n_quality_regressions"],0)
  self.assertEqual(bench["model_revision"],"UNKNOWN")
 def test_predecessor_preserved(self):
  p=self.d["predecessor"]
  self.assertEqual(m.sha((ROOT/p["path"]).read_bytes()),p["file_sha256"])
 def test_no_patient_values_exported(self):
  for x in self.d["inventory"]:
   self.assertEqual(set(x),{"path","sha256","size_bytes"})
  self.assertNotIn("patient_occurrences",self.d)
if __name__=="__main__":unittest.main()
