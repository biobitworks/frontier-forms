"""Provenance and negative control gates for read-only synthetic discovery admissions."""
import importlib.util, json,sys,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/'scripts/build_frontier_forms_discovery_admission.py'
spec=importlib.util.spec_from_file_location('ff_discovery_gate',MOD)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestSyntheticDiscoveryAdmission(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data,cls.sha=mod.checked_inputs()
  cls.ledger=mod.build(cls.data,cls.sha)
 def test_source_identity_is_actual_bytes(self):
  import hashlib
  for key,v in self.sha.items():
   raw=(ROOT/v['path']).read_bytes()
   self.assertEqual(hashlib.sha256(raw).hexdigest(),v['sha256'])
   self.assertEqual(len(raw),v['bytes'])
 def test_synthetic_registry_no_clinical_promotion(self):
  self.assertEqual(self.ledger['scientific_admission'],'HOLD_NO_INDEPENDENT_PI_ADMISSION')
  self.assertEqual(self.ledger['independent_replication'],'NOT_TESTED')
  self.assertFalse(any(r['scientific_admitted'] for r in self.ledger['admission_rows']))
 def test_training_vs_correction_must_be_distinct(self):
  a=next(r for r in self.ledger['admission_rows'] if r['id']=='FF-OCR-01')
  self.assertIn('correction table',a['limits'].lower())
  self.assertIn('NOT_SCIENTIFIC',a['evidence_state'])
  self.assertEqual(self.ledger['discovery_ocr_independent_status'],'NOT_PROMOTED_EXTERNAL_REPLICATION_PENDING')
 def test_all_negatives_preserved(self):
  ids={r['id'] for r in self.ledger['admission_rows']}
  self.assertTrue({'FF-BASE-M0','FF-CROP-A2A3','FF-BBOX-LOGIT','FF-BBOX-D1D2','FF-HOSTED-PILOT'}.issubset(ids))
 def test_reject_misreported_fine_tune_promotion(self):
  clone=json.loads(json.dumps(self.data))
  clone['ocr']['arms'][0]['status']='ADMITTED_SCIENTIFIC'
  with self.assertRaises(AssertionError):mod.build(clone,self.sha)
 def test_reject_unauthorized_replicated_admission(self):
  clone=json.loads(json.dumps(self.data))
  clone['fcar']['replicate']['independent_prospective_replication']='PASS'
  with self.assertRaises(AssertionError):mod.build(clone,self.sha)
 def test_reject_fabricated_improvement(self):
  clone=json.loads(json.dumps(self.data))
  clone['m0']['metrics']['overall']['full_form_success_required']=1.0
  with self.assertRaises(AssertionError):mod.build(clone,self.sha)
 def test_global_novelty_not_claimed(self):
  self.assertEqual(self.ledger['true_external_novelty'],'UNKNOWN_PRIOR_ART_NOT_REVIEWED')
  self.assertTrue(all(x['prior_art']=='NOT_REVIEWED' for x in self.ledger['novelty_matrix']))
 def test_daisy_transfer_absent(self):
  self.assertEqual(self.ledger['vithia_daisy_cross_program_transfer'],'NONE')
 def test_no_new_merkle_root_claim(self):
  self.assertEqual(self.ledger['new_merkle_root'],'NOT_COMPUTED')

if __name__=='__main__':unittest.main()
