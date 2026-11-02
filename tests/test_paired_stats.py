import importlib.util, unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts"/"paired_stats.py"
spec=importlib.util.spec_from_file_location("ablation_stats",P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PairedTests(unittest.TestCase):
    def test_zero_discordance(self): self.assertEqual(m.exact_mcnemar(0,0),1)
    def test_all_discordant(self): self.assertAlmostEqual(m.exact_mcnemar(0,10),0.001953125)
    def test_symmetric(self): self.assertEqual(m.exact_mcnemar(2,4),m.exact_mcnemar(4,2))
    def test_no_change_ci(self):
        rows=[{"task":"x","baseline_correct":True,"challenger_correct":True} for _ in range(6)]
        self.assertEqual(m.paired_bootstrap(rows,200),[0.0,0.0])
    def test_strict_pairing(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as d:
            b=Path(d)/"b.jsonl";c=Path(d)/"c.jsonl"
            b.write_text(json.dumps({"row_key_sha256":"one","status":"EXECUTED","correct":True,"gold":"A","task":"T"})+"\n")
            c.write_text(json.dumps({"row_key_sha256":"two","status":"EXECUTED","correct":False,"gold":"A","task":"T"})+"\n")
            with self.assertRaisesRegex(ValueError,"paired IDs differ"):m.analyze(b,c)
if __name__=="__main__":unittest.main()
