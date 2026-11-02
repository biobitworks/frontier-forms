import json, sys, unittest, tempfile
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'src'))
from frontier_forms.redteam_stats import (exact_mcnemar_p, paired_table, stratified_paired_bootstrap, holm, compare,
                                          admission_rule, load_public_lane, arm_flags, selective_metrics, cost_per_valid)
from frontier_forms import statistics as predecessor


class TestIndependentStats(unittest.TestCase):
    def setUp(self):
        rows = [json.loads(s) for s in (R / 'evidence/stats/discovery_pair_flags.jsonl').read_text().splitlines()]
        self.base = {r['case_digest_sha256']: r['baseline_correct'] for r in rows}
        self.chal = {r['case_digest_sha256']: r['challenger_correct'] for r in rows}
        self.strata = {r['case_digest_sha256']: r['task'] for r in rows}

    def test_frozen_discovery_reproduced_with_scipy(self):
        t = paired_table(self.base, self.chal)
        self.assertEqual((t['n'], t['baseline_only'], t['challenger_only'], t['both_correct'], t['both_wrong']), (38, 2, 4, 23, 9))
        self.assertAlmostEqual(exact_mcnemar_p(2, 4), 0.6875, places=12)
        self.assertAlmostEqual(exact_mcnemar_p(2, 4), predecessor.exact_mcnemar(2, 4), places=12)

    def test_bootstrap_contains_zero_and_is_seed_deterministic(self):
        a = stratified_paired_bootstrap(self.base, self.chal, self.strata, reps=10000, seed=20261102)
        b = stratified_paired_bootstrap(self.base, self.chal, self.strata, reps=10000, seed=20261102)
        self.assertEqual(a, b)
        self.assertLessEqual(a[0], 0.0)
        self.assertGreaterEqual(a[1], 0.0)
        # With n=38 the percentile CI is discrete; a different seed may land on the same bounds, so only
        # determinism under a fixed seed is asserted. RNG/method differences are recorded, never hidden.
        c = stratified_paired_bootstrap(self.base, self.chal, self.strata, reps=500, seed=1)
        self.assertEqual(len(c), 2)

    def test_compare_negative_gates(self):
        r = compare(self.base, self.chal, self.strata, reps=2000)
        self.assertFalse(r['mcnemar_gate']); self.assertFalse(r['bootstrap_gate'])
        self.assertEqual(r['AUROC'], 'NOT_COMPUTED_NO_CONTINUOUS_SCORES')
        self.assertEqual(admission_rule(r['mcnemar_gate'], r['bootstrap_gate'], 'NOT_TESTED', 'NOT_TESTED'), 'NOT_TESTED')
        self.assertEqual(admission_rule(True, True, 'NOT_TESTED', 'PASS'), 'BLOCKED_REPLICATION_OR_GUARDRAIL_NOT_TESTED')
        self.assertEqual(admission_rule(True, True, 'PASS', 'PASS'), 'PASS')
        self.assertEqual(admission_rule(True, False, 'PASS', 'PASS'), 'NEGATIVE')

    def test_holm(self):
        h = holm({'a': 0.01, 'b': 0.04, 'c': 0.03})
        self.assertAlmostEqual(h['a']['p_holm'], 0.03); self.assertAlmostEqual(h['c']['p_holm'], 0.06); self.assertAlmostEqual(h['b']['p_holm'], 0.06)
        self.assertTrue(h['a']['reject']); self.assertFalse(h['b']['reject'])

    def test_unpaired_and_empty_rejected(self):
        with self.assertRaises(ValueError):
            paired_table({'x': True}, {'y': True})
        with self.assertRaises(ValueError):
            paired_table({}, {})
        self.assertEqual(exact_mcnemar_p(0, 0), 1.0)

    def test_public_lane_loader_fails_closed(self):
        good = {'key': 'k1', 'task': 'LB-0307', 'split': 'discovery', 'arms': {'direct': {'strict_correct': True, 'parsed': True, 'status': 'EXECUTED'}}}
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'x.jsonl'
            p.write_text(json.dumps(good) + '\n' + json.dumps(good) + '\n')
            with self.assertRaises(ValueError):
                load_public_lane(p, 'discovery')
            p.write_text(json.dumps(good) + '\n')
            with self.assertRaises(ValueError):
                load_public_lane(p, 'heldout')
            with self.assertRaises(ValueError):
                load_public_lane(p, 'discovery', allowed_keys={'other'})
            leaked = dict(good); leaked['arms'] = {'direct': {'strict_correct': True, 'gold': 'A'}}
            p.write_text(json.dumps(leaked) + '\n')
            with self.assertRaises(ValueError):
                load_public_lane(p, 'discovery')
            p.write_text(json.dumps(good) + '\n')
            rows = load_public_lane(p, 'discovery', allowed_keys={'k1'})
            self.assertEqual(arm_flags(rows, 'direct'), {'k1': True})

    def test_selective_metrics_null_denominators(self):
        rows = [{'key': 'k', 'arms': {'a': {'admitted': False, 'reason': 'X'}}}]
        m = selective_metrics(rows, 'a')
        self.assertIsNone(m['selective_accuracy']); self.assertEqual(m['coverage'], 0.0); self.assertEqual(m['abstention_rate'], 1.0)
        c = cost_per_valid(0, 10.0, 100)
        self.assertIsNone(c['wall_seconds_per_valid']); self.assertEqual(c['usd_per_valid'], 'NOT_COMPUTED_NO_OBSERVED_RATE')


if __name__ == '__main__':
    unittest.main()
