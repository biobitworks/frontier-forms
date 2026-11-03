"""Red-team discovery admission ledger: pinned evidence, recomputable numbers, no promotion."""
import hashlib, json, subprocess, sys, unittest
from pathlib import Path

R = Path(__file__).resolve().parent.parent
LEDGER = R / 'evidence/admission/REDTEAM_DISCOVERY_ADMISSION_V1.json'
FORBIDDEN = {'SUPPORTED', 'SUPPORTED_GAIN', 'ADMITTED', 'PROMOTED'}


class TestRedteamDiscoveryAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(LEDGER.read_text())

    def test_ledger_rebuilds_byte_identical(self):
        p = subprocess.run([sys.executable, str(R / 'scripts/redteam/build_discovery_admission.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_evidence_hashes_match(self):
        for r in self.d['records']:
            for e in r['evidence']:
                self.assertEqual(hashlib.sha256((R / e['path']).read_bytes()).hexdigest(), e['sha256'], (r['id'], e['path']))

    def test_nothing_promoted(self):
        for r in self.d['records']:
            self.assertIs(r['promoted'], False, r['id'])
            self.assertEqual(r['scientific_promotion'], 'HOLD', r['id'])
            self.assertNotIn(r['admission_state'], FORBIDDEN, r['id'])
            self.assertNotIn(r['decision'], FORBIDDEN, r['id'])

    def test_admitted_records_meet_rule(self):
        for r in self.d['records']:
            if r['admission_state'] != 'DISCOVERY_LEDGER_ADMITTED':
                continue
            o = r['outcome']
            self.assertLess(o['holm_p'], 0.05, r['id'])
            ci = o.get('ci95_patient_cluster_bootstrap') or o.get('bootstrap_ci95')
            self.assertGreater(ci[0], 0, r['id'])

    def test_posthoc_never_admitted(self):
        for r in self.d['records']:
            if not r['preregistered'] and r['family'] == 'model_weight_comparison':
                self.assertNotEqual(r['admission_state'], 'DISCOVERY_LEDGER_ADMITTED', r['id'])

    def test_trained_gain_numbers(self):
        a1 = next(r for r in self.d['records'] if r['id'] == 'RT-ADM-TRAINED-A1')['outcome']
        self.assertEqual((a1['baseline_success'], a1['challenger_success'], a1['n']), (14, 22, 46))
        self.assertEqual((a1['baseline_only'], a1['challenger_only']), (0, 8))
        self.assertAlmostEqual(a1['mcnemar_p_exact_two_sided'], 0.0078125)

    def test_negatives_and_nulls_kept(self):
        states = self.d['counts_by_admission_state']
        for s in ('NULL_RECORDED', 'NEGATIVE_RECORDED', 'FAILED_RECORDED', 'NOT_TESTED_RECORDED', 'BLOCKED_RECORDED'):
            self.assertGreater(states.get(s, 0), 0, s)


if __name__ == '__main__':
    unittest.main()
