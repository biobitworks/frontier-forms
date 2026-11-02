import importlib.util,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(name):
    p=R/'scripts'/name
    spec=importlib.util.spec_from_file_location(name.replace('.py',''),p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class CustodyTests(unittest.TestCase):
    def test_stable_canonical(self):
        m=load('verify_freeze.py')
        self.assertEqual(m.canonical({'b':2,'a':1}),b'{"a":1,"b":2}')
    def test_merkle_changes_on_reordered_leaves(self):
        m=load('verify_freeze.py')
        a=[{'path':'a'},{'path':'b'}]
        self.assertNotEqual(m.root(a),m.root(list(reversed(a))))
    def test_project_root_is_pinned(self):
        m=load('verify_freeze.py')
        self.assertEqual(len(m.EXPECTED),64)
class MetricTests(unittest.TestCase):
    def test_auroc_perfect(self):
        m=load('quality_metrics.py')
        self.assertEqual(m.auroc([0,1,0,1],[.1,.9,.2,.8]),1.)
    def test_auroc_single_class_null(self):
        m=load('quality_metrics.py')
        self.assertIsNone(m.auroc([1,1],[.2,.8]))
    def test_fpr_fdr(self):
        m=load('quality_metrics.py')
        s=m.confusion([1,0,0,1],[.8,.9,.1,.2])
        self.assertEqual(s['FPR'],.5)
        self.assertEqual(s['FDR'],.5)
    def test_null_denominator(self):
        m=load('quality_metrics.py')
        self.assertIsNone(m.confusion([1],[0])['FDR'])
    def test_holm(self):
        m=load('quality_metrics.py')
        self.assertEqual(m.holm([.01,.1]),[.02,.1])
if __name__=='__main__':unittest.main()
