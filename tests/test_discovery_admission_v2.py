"""Fail-closed evidence admission tests: discovery != scientific promotion."""
import collections,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import build_discovery_admission_v2 as a
class AdmissionV2(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.source=json.loads(a.OUT.read_text())
 def test_exact_source_replay_and_root(self):
  r=a.verify();self.assertEqual(r['status'],'PASS_FROZEN_V2_AND_PRESENTATION_SUCCESSOR')
  self.assertEqual((r['entries'],r['source_heatmap_cells']), (89,52))
  self.assertEqual(r['root'],a.merkle(self.source['admitted_entries']))
 def test_distinct_promotions_and_discovery(self):
  self.assertEqual(self.source['scientific_promotion_count'],0)
  self.assertEqual(self.source['scientific_admission'],'HOLD_NO_INDEPENDENT_PI_ADMISSION')
  self.assertTrue(all(e['admission']=='ADMITTED_TO_EVIDENCE_LEDGER' and e['scientific_promotion'] is False for e in self.source['admitted_entries']))
  self.assertEqual(self.source['daisy_specific_model_gain'],'NOT_COMPUTED')
 def test_discovery_arms_model_identity(self):
  oc=next(x for x in self.source['admitted_entries'] if x['id']=='OCR:A1')
  self.assertEqual(oc['status'],'DISCOVERY_POSITIVE')
  self.assertAlmostEqual(oc['delta'],8/46)
  self.assertEqual((oc['mcnemar_p'],oc['holm_p']),(.0078125,.0234375))
  self.assertGreater(oc['patient_ci95'][0],0)
  self.assertIn('NOT neural',oc['source_claim_limits']['learned_component'])
  fco=next(x for x in self.source['admitted_entries'] if x['category']=='FCO_LEAF_LOMO' and x['id'].endswith('B0+L1+L3'))
  self.assertIs(fco['weights_changed'],False)
  self.assertGreater(fco['delta'],0)
 def test_all_negative_neutral_failure_states(self):
  s=collections.Counter(x['status'] for x in self.source['admitted_entries'])
  self.assertEqual(sum(s.values()),89)
  for k,n in [('NEGATIVE',9),('NULL',12),('NEUTRAL',48),('FAILED_PRESERVED',1),('NOT_COMPUTED',1)]:
   self.assertEqual(s[k],n)
 def test_yolo_epoch_checkpoint_identity(self):
  rows=[x for x in self.source['admitted_entries'] if x['category']=='TRAINED_YOLO_CHECKPOINT_DEV']
  self.assertEqual(len(rows),60)
  self.assertEqual({x['id'].split(':')[1] for x in rows},{'full','no_scan'})
  for x in rows:
   self.assertEqual(len(x['recorded_checkpoint_sha256']),64)
   self.assertFalse(x['source_claim_limits']['checkpoint_bytes_independently_rehashed'])
 def test_no_algorithm_novelty_claim(self):
  cells=self.source['novel_vs_standard']
  self.assertEqual(len(cells),5)
  self.assertTrue(all('standard' in x and 'project_integration' in x and 'novelty' in x for x in cells))
 def test_source_bytes(self):
  successor=a.presentation_successor()
  self.assertEqual(len(a.verify_root_scheme_successor()),64)
  self.assertEqual(successor['current_source_ledger_leaf_root'],self.source['admission_event_root'])
  self.assertEqual(successor['scientific_promotions'],0)
  self.assertEqual(successor['heatmap_cells_unchanged'],52)
  for p,h in self.source['source_inputs_file_sha256'].items():
   if p=='docs/figures/gains_heatmap.json':
    self.assertNotEqual(hashlib.sha256((R/p).read_bytes()).hexdigest(),h)
   else:self.assertEqual(hashlib.sha256((R/p).read_bytes()).hexdigest(),h)
 def test_mutation_detected(self):
  with patch.object(a,'src_sha',side_effect=lambda p:'0'*64):
   with self.assertRaisesRegex(AssertionError,'UNEXPECTED_SOURCE_DRIFT'):a.verify()
if __name__=='__main__':unittest.main()
