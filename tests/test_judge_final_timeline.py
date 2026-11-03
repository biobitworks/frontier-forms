import sys,unittest,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import build_judge_final_timeline as a
class FinalJudgeTimeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.x=json.loads((R/a.OUT).read_text())
    def test_source_and_pngs(self):
        self.assertEqual(a.verify()['training_epochs'],100)
        self.assertEqual(a.verify_successor()['prs'],63)
    def test_distinct_time_bases(self):
        self.assertEqual(len(self.x['pr_events']),63)
        self.assertIn('NOT actual human work',self.x['pr_time_basis'])
        self.assertEqual(self.x['new_yolo_v2_40_epochs']['per_epoch_utc'],'NOT_RECORDED_IN_V2_SUMMARY')
        self.assertTrue(all(len(x['epochs'])==30 for x in self.x['older_yolo_30_epochs'].values()))
        self.assertTrue(all(r['utc'].endswith('Z') for x in self.x['older_yolo_30_epochs'].values() for r in x['epochs']))
    def test_new_v2_mixed_quality(self):
        x=self.x['new_yolo_v2_40_epochs']
        self.assertEqual((x['train_images'],x['validation_images'],x['test_images']),(252,38,108))
        self.assertAlmostEqual(x['held_out_layout_test']['box_recall_iou50'],.9972)
        self.assertAlmostEqual(x['held_out_layout_test']['class_accuracy_matched'],.7799)
        self.assertAlmostEqual(x['held_out_layout_test']['false_flag_rate'],.5763)
        self.assertEqual(self.x['scientific_promotions'],0)
    def test_distinct_discoveries(self):
        self.assertEqual((self.x['fco_full_form']['baseline'],self.x['fco_full_form']['challenger']),(18,30))
        self.assertEqual((self.x['ocr_all_seven_fields']['baseline'],self.x['ocr_all_seven_fields']['correction']),(14,22))
        self.assertEqual(self.x['ocr_all_seven_fields']['holm_p'],.0234375)
    def test_failed_predecessor_preserved(self):
        x=json.loads((R/'docs/judges/FINAL_JUDGE_TIMELINE_PRESENTATION_CORRECTION_V2.json').read_text())
        self.assertEqual(a.verify_successor()['mixed_untagged'],43)
        self.assertEqual(x['predecessor_gantt_state'],'FAILED_DISPLAY_LABEL_MISMATCH_MIXED_LANE_SHOWN_ZERO')
        self.assertFalse(x['source_data_changed'])
    def test_readme_notebook_links(self):
        text=(R/'README.md').read_text()
        for marker in ('fig20_contributor_gantt_corrected_v2.png','fig19_actual_training_epochs_20261102.png','40c58ec71eb28161b79ddfbb083cb7c0','FINAL_SUBMISSION_REVIEW_AND_TRAINING_20261102.md'):
            self.assertIn(marker,text)
    def test_figure_hash(self):
        for path,sha in self.x['png_sha256'].items():
            self.assertEqual(a.SHA(a.READ(path)),sha)
        self.assertEqual(a.verify_successor()['state'],'PASS')
if __name__=='__main__':unittest.main()
