import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parent.parent

class TestSupabaseFreezeGate(unittest.TestCase):
    def setUp(self):
        self.o=json.loads((R/'evidence/sources/supabase_source_intake.json').read_text())
    def test_not_prematurely_frozen(self):
        self.assertEqual(self.o['state'],'REPORTED_IN_PROGRESS')
        self.assertEqual(self.o['snapshot_merkle_root'],'NOT_COMPUTED')
        self.assertIsNone(self.o['rows_observed'])
        self.assertEqual(self.o['actual_supabase_query'],'NOT_EXECUTED')
    def test_private_raw_export_not_authorized(self):
        self.assertEqual(self.o['private_export'],'NOT_AUTHORIZED')
        self.assertEqual(self.o['data_classification'],'UNKNOWN')
    def test_fcg_has_only_proposed_edge(self):
        self.assertEqual(self.o['source_to_fcg_edge']['state'],'NOT_TESTED')
        self.assertEqual(self.o['chain_parent'],'513cb1f8e83d0eae653c94000552fa6680b37827bcc8100af35fed3fc7d0f730')
