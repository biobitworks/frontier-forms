import json,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_final_public_data_coverage import verify
class FinalPublicDataCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.j=verify()
    def test_all_open_pr_resolved_at_predecessor(self):
        p=self.j['github_pull_requests']
        self.assertEqual((p['merged'],p['closed_without_merge'],p['open_at_predecessor']),(60,4,0))
    def test_not_all_remote_branches_integrated(self):
        self.assertEqual(self.j['branch_count_not_ancestor_of_main'],13)
        self.assertTrue(any(x['ref'].endswith('/fix/main-ci-yaml-final-20261102') for x in self.j['branches_not_ancestor_of_main_at_snapshot']))
    def test_data_vs_weight_availability(self):
        self.assertIn('NOT_PUBLISHED',self.j['restrictions']['v2_yolo_weights'])
        self.assertEqual(self.j['restrictions']['scientific_gain_admissions'],0)
        self.assertEqual(self.j['restrictions']['qwen_lora_paired_effect'],'NOT_COMPUTED')
    def test_original_ci_receipt_exactly_preserved(self):
        x=self.j['imported_historical_receipt']
        self.assertEqual(x['exact_sha256'],'cbe7d67eb961e960068b13e22ba297877bd3dab03eda464c1fe6497d5f35d5cc')
    def test_15_source_hashes(self):
        self.assertEqual(len(self.j['public_source_identity_checks']),15)
    def test_disallowed_legacy_fixture_not_imported(self):
        arr=self.j['branches_not_ancestor_of_main_at_snapshot']
        self.assertTrue(any('synthetic_pseudobulk_v1.bin' in name for x in arr for name in x['unique_paths_absent_from_main']))
        self.assertFalse((ROOT/'lanes/frontier-forms/dataset-freeze-redteam/fixtures/synthetic_pseudobulk_v1.bin').exists())
if __name__=='__main__':unittest.main()
