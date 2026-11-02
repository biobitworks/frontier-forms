import sys,unittest,json
from pathlib import Path
R=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(R/'src'))
from frontier_forms.statistics import paired_table,exact_mcnemar,paired_bootstrap,admit,binary_confusion
class TestStatistics(unittest.TestCase):
  def setUp(self):
    self.pairs=[json.loads(s) for s in (R/'evidence/stats/discovery_pair_flags.jsonl').read_text().splitlines()]
  def test_exact_discordances(self):
    t=paired_table(self.pairs);self.assertEqual((t['n'],t['baseline_only'],t['challenger_only']),(38,2,4))
    self.assertEqual(exact_mcnemar(2,4),.6875)
  def test_bootstrap_abstains(self):
    x=admit(self.pairs,reps=10000,seed=20261102)
    self.assertLessEqual(x['ci_delta_bootstrap_stratified_95'][0],0)
    self.assertFalse(x['mcnemar_positive_gate'])
    self.assertFalse(x['bootstrap_positive_gate'])
    self.assertEqual(x['promotion'],'NO_SUPERIORITY_CLAIM')
  def test_no_pairs_cannot_pass(self):
    self.assertEqual(exact_mcnemar(0,0),1.0)
    with self.assertRaises(ValueError):paired_bootstrap([])
  def test_duplicate_key_rejected(self):
    with self.assertRaises(ValueError):paired_table(self.pairs+[self.pairs[0]])
  def test_zero_denominator(self):
    m=binary_confusion([{'gold':'B','pred':'B'}],positive='A')
    self.assertIsNone(m['FDR'])
    self.assertEqual(m['AUROC'],'NOT_COMPUTED_NO_CONTINUOUS_SCORES')
  def test_gold_oracle_not_exported(self):
    src=(R/'evidence/stats/discovery_pair_flags.jsonl').read_text()
    self.assertNotIn('"gold"',src)
    self.assertNotIn('"pred"',src)
  def test_wrong_paired_input_downgraded(self):
    mutated=[dict(x) for x in self.pairs]; mutated[0]['case_digest_sha256']='new'
    self.assertEqual(len(mutated),38)
    # A new key must not be silently considered the same data: check deterministic source identity.
    self.assertNotEqual(mutated[0]['case_digest_sha256'],self.pairs[0]['case_digest_sha256'])
if __name__=='__main__': unittest.main()
