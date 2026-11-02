import unittest,sys,json,tempfile,shutil
from pathlib import Path
R=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(R/'scripts'))
from validate_pair_export import check
class TestPairAlignment(unittest.TestCase):
    def test_valid_pair_split(self):
        result=check(R)
        self.assertEqual((result['state'],result['pairs'],result['heldout_overlap']),('PASS',38,0))
    def test_cross_split_tamper_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            temp=Path(td);(temp/'evidence/stats').mkdir(parents=True);(temp/'evidence/freeze').mkdir(parents=True)
            shutil.copy(R/'evidence/freeze/longebench_split_manifest.json',temp/'evidence/freeze/longebench_split_manifest.json')
            rows=[json.loads(x) for x in (R/'evidence/stats/discovery_pair_flags.jsonl').read_text().splitlines()]
            split=json.loads((R/'evidence/freeze/longebench_split_manifest.json').read_text())
            rows[0]['case_digest_sha256']=next(iter(next(iter(split['task_partitions'].values()))['heldout']))
            (temp/'evidence/stats/discovery_pair_flags.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
            with self.assertRaises(AssertionError):
                check(temp)
