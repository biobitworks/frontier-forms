"""Judge synthetic demo assets must match committed SHA256 and sizes."""
import sys,json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
from verify_judge_demo_manifest import verify,sha,D
class JudgeDemoAudit(unittest.TestCase):
 def test_asset_hashes(self):
  v=verify()
  self.assertEqual((v['assets'],v['repaired_annotation_json']), (62,10))
 def test_prior_failure_preserved(self):
  j=json.loads((D/'MANIFEST_REPAIR_V2.json').read_text())
  self.assertEqual(sha((D/'manifest_v1_pre_repair.json').read_bytes()),j['predecessor_manifest_sha256'])
  self.assertEqual(j['original_verification_state'],'FAILED_10_ANNOTATION_HASHES')
 def test_ocr_negative(self):
  x=json.loads((D/'ocr_boxes_vs_clean.json').read_text())
  self.assertEqual((x['images'],x['fields_total']), (10,70))
  self.assertEqual(sum(z['clean']['correct_count'] for z in x['rows'].values()),58)
  self.assertEqual(sum(z['with_boxes']['correct_count'] for z in x['rows'].values()),0)
 def test_no_daisy_gain(self):
  j=json.loads((D/'MANIFEST_REPAIR_V2.json').read_text())
  self.assertIs(j['synthetic_only'],True)
  self.assertEqual(j['daisy_performance_gain'],'NOT_COMPUTED')
 def test_tamper_detection(self):
  import tempfile,shutil
  from unittest.mock import patch
  import verify_judge_demo_manifest as m
  with tempfile.TemporaryDirectory() as t:
   dest=Path(t)/'demo';shutil.copytree(D,dest)
   man=json.loads((dest/'manifest.json').read_text())
   path=dest/next(iter(man['assets']));path.write_bytes(path.read_bytes()+b'bad')
   with patch.object(m,'D',dest):
    with self.assertRaisesRegex(AssertionError,'MANIFEST_INPUT_DRIFT'):m.verify()
if __name__=='__main__':unittest.main()
