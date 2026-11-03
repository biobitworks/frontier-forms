"""Negative and mutation cases for the Merkle commitments, using the red-team's independent implementation."""
import json, sys, unittest
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'scripts/redteam'))
from redteam_verify_sources import canon, leaf, node, root, proof_ok, sha_hex


def proofs_for(leaves):
    out = []
    for j in range(len(leaves)):
        at, level, seq = j, list(leaves), []
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            other = at ^ 1
            seq.append({'sibling': level[other].hex(), 'side': 'left' if other < at else 'right'})
            at //= 2
            level = [node(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        out.append(seq)
    return out


class TestRedteamMerkle(unittest.TestCase):
    def setUp(self):
        self.rows = [json.loads(x) for x in (R / 'evidence/freeze/predecessor/leaves.jsonl').read_text().splitlines()]
        self.leaves = [leaf(x) for x in self.rows]
        self.root = root(self.leaves).hex()

    def test_independent_root_matches_predecessor(self):
        self.assertEqual(self.root, '9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a')

    def test_inclusion_proofs_round_trip_and_break_on_corruption(self):
        pr = proofs_for(self.leaves)
        for i, l in enumerate(self.leaves):
            self.assertTrue(proof_ok(l, pr[i], bytes.fromhex(self.root)))
        forged = leaf(dict(self.rows[3], sha256='f' * 64))
        self.assertFalse(proof_ok(forged, pr[3], bytes.fromhex(self.root)))
        # a proof for leaf i must not validate leaf j
        self.assertFalse(proof_ok(self.leaves[2], pr[3], bytes.fromhex(self.root)))

    def test_mutations_change_root(self):
        for mutate in (lambda L: L[:-1], lambda L: L[1:], lambda L: L[:2] + L[3:], lambda L: [L[1], L[0]] + L[2:],
                       lambda L: L[:5] + [leaf({'forged': 1})] + L[6:]):
            self.assertNotEqual(root(mutate(list(self.leaves))).hex(), self.root)
        self.assertNotEqual(root(self.leaves, dup_odd=False).hex(), self.root)
        self.assertNotEqual(root(self.leaves, prefix=b'\x00').hex(), self.root)
        self.assertNotEqual(root([leaf(x, b'\x01') for x in self.rows]).hex(), self.root)

    def test_duplicate_last_leaf_collision_is_real_and_bound_by_manifest(self):
        # F-01: duplicate-last-odd scheme: appending a copy of the last leaf keeps the root.
        self.assertEqual(root(self.leaves + [self.leaves[-1]]).hex(), self.root)
        man = json.loads((R / 'evidence/freeze/predecessor/manifest.json').read_text())
        self.assertEqual(man['leaf_count'], len(self.leaves))  # count is bound outside the root; verifier must check it
        # an even tree is immune: 16 leaves + duplicate changes root
        even = self.leaves + [leaf({'pad': 1})]
        self.assertNotEqual(root(even + [even[-1]]).hex(), root(even).hex())

    def test_canonicalization_sensitivity(self):
        a = {'b': 1, 'a': [1, 2]}; b = {'a': [1, 2], 'b': 1}
        self.assertEqual(canon(a), canon(b))
        self.assertNotEqual(sha_hex(canon({'a': 1})), sha_hex(canon({'a': 1.0})))
        self.assertNotEqual(sha_hex(canon({'a': 'é'})), sha_hex(json.dumps({'a': 'é'}).encode()))  # ensure_ascii matters

    def test_review_successors_chain_to_declared_parents(self):
        mans = {p.parent.name: json.loads(p.read_text()) for p in (R / 'evidence/freeze/review_successor').glob('*/manifest.json')}
        self.assertEqual(mans['REVIEW-513cb1f8e83d0eae']['parent_project_root'], mans['REVIEW-37152dc823a8009f']['root'])
        self.assertEqual(mans['REVIEW-2f1cfafda7de0153']['parent_project_root'], mans['REVIEW-513cb1f8e83d0eae']['root'])
        for m in mans.values():
            rows = [json.loads(x) for x in (R / 'evidence/freeze/review_successor' / ('REVIEW-' + m['root'][:16]) / 'leaves.jsonl').read_text().splitlines()]
            self.assertEqual(root([leaf(x) for x in rows]).hex(), m['root'])
            self.assertEqual(len(rows), m['leaf_count'])


if __name__ == '__main__':
    unittest.main()
