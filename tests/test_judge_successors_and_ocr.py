"""Independent judge evidence roots, patient bootstrap and no unsupported promotion."""
import json,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import verify_ocr_correction_successor as ocr
import verify_judge_outcome_successor as outcome
import verify_judge_demo_manifest as assets
class JudgeSuccessorTests(unittest.TestCase):
    def test_exact_demo_asset_bytes(self):
        r=assets.verify()
        self.assertEqual(r['assets'],62)
        self.assertEqual(r['repaired_annotation_json'],10)
    def test_demo_predecessor_still_failed(self):
        r=json.loads((R/'docs/demo/MANIFEST_REPAIR_V2.json').read_text())
        self.assertEqual(r['original_verification_state'],'FAILED_10_ANNOTATION_HASHES')
        self.assertTrue((R/'docs/demo/manifest_v1_pre_repair.json').is_file())
    def test_all_82_original_event_leaves_immutable(self):
        x=outcome.verify()
        self.assertEqual(x['events'],82)
        self.assertEqual(x['training_epochs'],60)
        self.assertEqual(x['scientific_promotions'],0)
    def test_new_ocr_independent_46_case_statistics(self):
        x=ocr.verify()
        self.assertEqual((x['n_images'],x['n_patients'],x['arms']), (46,23,3))
        self.assertEqual(x['scientific_promotions'],0)
        self.assertGreater(x['patient_ci'][0],0)
    def test_ocr_discovery_multiplicity_and_nulls(self):
        z=json.loads((R/'docs/judges/OCR_CORRECTION_SUCCESSOR_V2.json').read_text())
        a={v['arm']:v for v in z['arms']}
        self.assertEqual((a['A1']['challenger_all7'],a['A2']['challenger_all7'],a['A3']['challenger_all7']), (22,9,15))
        self.assertEqual(a['A1']['discordant_challenger_only'],8)
        self.assertEqual(a['A1']['discordant_baseline_only'],0)
        self.assertEqual(a['A1']['mcnemar_exact'],.0078125)
        self.assertEqual(a['A1']['p_holm_3_comparisons'],.0234375)
        self.assertTrue(a['A1']['discovery_positive'])
        self.assertFalse(a['A2']['discovery_positive'])
        self.assertFalse(a['A3']['discovery_positive'])
    def test_no_neural_model_promotion_false_claims(self):
        z=json.loads((R/'docs/judges/OCR_CORRECTION_SUCCESSOR_V2.json').read_text())
        self.assertEqual(z['source_form_weight_type'],'FITTED_OCR_CORRECTION_TABLE_NOT_NEURAL_WEIGHTS')
        self.assertFalse(z['detector_checkpoint_bytes_independently_rehashed'])
        self.assertEqual(z['daisy_performance_gain'],'NOT_COMPUTED')
        self.assertTrue(z['scientific_admission'].startswith('HOLD'))
    def test_no_source_tamper(self):
        raw=(R/'evidence/redteam/trained_gain/trained_gain_rows.json').read_bytes()
        frozen=json.loads((R/'docs/judges/OCR_CORRECTION_SUCCESSOR_V2.json').read_text())
        self.assertEqual(ocr.SHA(raw),frozen['source_file_sha256'][ocr.ROWS])
        self.assertNotEqual(ocr.SHA(raw+b'x'),frozen['source_file_sha256'][ocr.ROWS])
    def test_figures_labeled_agents_and_claim_ceiling(self):
        for n in ('JUDGE_OUTCOME_HEATMAP_V1.html','FIG12_OCR_CORRECTION_ABLATION_V1.html'):
            t=(R/'docs/judges'/n).read_text()
            self.assertIn('Figure',t)
            self.assertIn('Claude',t)
            self.assertIn('ChatGPT',t)
        fig=(R/'docs/judges/FIGURES.md').read_text()
        self.assertIn('Figure 11',fig)
        self.assertIn('Figure 12',fig)
    def test_pr_history_successor_preserves_predecessor(self):
        a=json.loads((R/'docs/judges/PR_HISTORY_SUCCESSOR_V1.json').read_text())
        b=json.loads((R/'docs/judges/PR_HISTORY_SUCCESSOR_V2.json').read_text())
        self.assertTrue({v['number'] for v in a['rows']}.issubset({v['number'] for v in b['rows']}))
        self.assertGreaterEqual(b['pr_count'],a['count'])
if __name__=='__main__':unittest.main()
