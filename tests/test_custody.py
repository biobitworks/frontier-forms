import unittest,sys,json
from pathlib import Path
R=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(R/'scripts'))
from verify_predecessor import verify,root_of,canon
class TestMerkle(unittest.TestCase):
  def setUp(self):
    self.dir=R/'evidence/freeze/predecessor'
    self.leaves=[json.loads(x) for x in (self.dir/'leaves.jsonl').read_text().splitlines()]
  def test_root_matches(self):
    x=verify(self.dir)
    self.assertEqual(x['root'],'9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a')
    self.assertEqual(x['leaves'],15)
    self.assertEqual(x['source_sha_verification'],'NOT_TESTED')
  def test_mutation_changes_root(self):
    x=[dict(i) for i in self.leaves]
    x[2]['sha256']='0'*64
    self.assertNotEqual(root_of(x),root_of(self.leaves))
  def test_order_changes_root(self):
    x=list(self.leaves)
    x[2],x[3]=x[3],x[2]
    self.assertNotEqual(root_of(x),root_of(self.leaves))
  def test_context_hash_stable(self):
    x=verify(self.dir)
    self.assertEqual(x['context_digest'],'PASS')
if __name__=='__main__':unittest.main()
