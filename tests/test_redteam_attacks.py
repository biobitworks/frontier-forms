"""Claude red-team attacks against the FCO/FCG custody layer.

Tests named test_weakness_* PASS when the weakness is REPRODUCED. They document
behaviour of the predecessor verifier (scripts/verify_predecessor.py); they are
not endorsements. Tests named test_defence_* PASS when the defence holds.
"""
import copy
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "scripts"))
sys.path.insert(0, str(R / "redteam"))
from verify_predecessor import root_of, verify  # noqa: E402
import merkle_independent as M  # noqa: E402
import stats_independent as S  # noqa: E402

PIN_15 = "9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a"
BUNDLE = R / "evidence/freeze/predecessor"


def load():
    man = json.loads((BUNDLE / "manifest.json").read_text())
    leaves = [json.loads(x) for x in (BUNDLE / "leaves.jsonl").read_text().splitlines() if x.strip()]
    return man, leaves


def write_bundle(d: Path, man, leaves, raw_lines=None):
    (d / "manifest.json").write_text(json.dumps(man))
    lines = raw_lines if raw_lines is not None else [json.dumps(x) for x in leaves]
    (d / "leaves.jsonl").write_text("\n".join(lines) + "\n")


class CrossImplementation(unittest.TestCase):
    def test_defence_independent_impl_matches_predecessor_on_real_bundle(self):
        _, leaves = load()
        self.assertEqual(M.root_of_records(leaves), PIN_15)
        self.assertEqual(root_of(leaves), PIN_15)

    def test_defence_independent_impl_matches_on_random_trees(self):
        rng = random.Random(7)
        for n in range(1, 41):
            recs = [{"i": i, "v": rng.random()} for i in range(n)]
            self.assertEqual(M.root_of_records(recs), root_of(recs), n)

    def test_defence_all_inclusion_proofs_verify(self):
        for n in (1, 2, 3, 5, 15, 16, 17, 729):
            lh = [M.leaf_hash({"i": i}) for i in range(n)]
            root = M.root_from_leaf_hashes(lh).hex()
            for i in range(n):
                self.assertTrue(M.verify_inclusion(lh[i].hex(), M.inclusion_proof(lh, i), root))

    def test_defence_domain_separation(self):
        a, b = M.leaf_hash({"x": 1}), M.leaf_hash({"x": 2})
        node = M.node_hash(a, b)
        # without the 00/01 prefixes a 2-leaf root could be replayed as a leaf; with them it cannot
        self.assertNotEqual(M.h(a + b), node)
        self.assertNotEqual(M.leaf_hash({"x": 1}), M.h(M.canonical({"x": 1})))


class CustodyAttacks(unittest.TestCase):
    def test_weakness_duplicate_last_leaf_same_root(self):
        """15 leaves and 16 leaves (last duplicated) give the SAME root (CVE-2012-2459 class)."""
        man, leaves = load()
        forged = leaves + [copy.deepcopy(leaves[-1])]
        self.assertEqual(root_of(forged), PIN_15)
        self.assertEqual(M.root_of_records(forged), PIN_15)

    def test_weakness_verifier_accepts_16_leaf_bundle_with_pinned_root(self):
        man, leaves = load()
        forged = leaves + [copy.deepcopy(leaves[-1])]
        man2 = dict(man, leaf_count=16, leaf_order=[x["path"] for x in forged])
        with tempfile.TemporaryDirectory() as t:
            write_bundle(Path(t), man2, forged)
            res = verify(Path(t))
        self.assertEqual(res["root"], PIN_15)
        self.assertEqual(res["leaves"], 16)

    def test_weakness_parent_pointer_not_committed(self):
        man, leaves = load()
        man2 = dict(man, parent={"root": "f" * 64, "snapshot": "FORGED"})
        with tempfile.TemporaryDirectory() as t:
            write_bundle(Path(t), man2, leaves)
            res = verify(Path(t))
        self.assertEqual(res["root"], PIN_15)
        self.assertEqual(res["parent_snapshot"]["snapshot"], "FORGED")

    def test_defence_parent_inside_context_leaf_is_committed(self):
        _, leaves = load()
        x = copy.deepcopy(leaves)
        x[0]["context"]["parent"]["root"] = "f" * 64
        self.assertNotEqual(M.root_of_records(x), PIN_15)

    def test_weakness_reorder_passes_when_manifest_self_declares_root(self):
        man, leaves = load()
        x = list(leaves)
        x[2], x[3] = x[3], x[2]
        man2 = dict(man, root=root_of(x), leaf_order=[i["path"] for i in x])
        with tempfile.TemporaryDirectory() as t:
            write_bundle(Path(t), man2, x)
            res = verify(Path(t))
        self.assertEqual(res["root_recomputed"], "PASS")
        self.assertNotEqual(res["root"], PIN_15)  # only an EXTERNAL pin catches it

    def test_weakness_dangling_fcg_edge_accepted(self):
        man, leaves = load()
        x = copy.deepcopy(leaves)
        x[-1]["edges"].append({"relation": "CAUSED_GAIN", "source": "NONEXISTENT_LEAF", "status": "EXECUTED",
                               "target": "eval/paired_discovery_mcnemar_bootstrap.json"})
        import hashlib
        x[-1]["sha256"] = hashlib.sha256(M.canonical(x[-1]["edges"])).hexdigest()
        man2 = dict(man, root=root_of(x))
        with tempfile.TemporaryDirectory() as t:
            write_bundle(Path(t), man2, x)
            res = verify(Path(t))
        self.assertEqual(res["edge_digest"], "PASS")

    def test_weakness_duplicate_json_key_parser_differential(self):
        """A leaf line with two sha256 keys: Python keeps the last; a first-wins parser sees the forged one."""
        man, leaves = load()
        lines = [json.dumps(x) for x in leaves]
        good = leaves[3]["sha256"]
        lines[3] = lines[3].replace('"sha256": "%s"' % good, '"sha256": "%s", "sha256": "%s"' % ("0" * 64, good))
        self.assertIn("0" * 64, lines[3])
        with tempfile.TemporaryDirectory() as t:
            write_bundle(Path(t), man, leaves, raw_lines=lines)
            res = verify(Path(t))
        self.assertEqual(res["root"], PIN_15)

    def test_weakness_phantom_index_proof_verifies(self):
        """For an odd tree, a proof for index n (one past the end) verifies: proof checkers must bound-check."""
        n = 729
        lh = [M.leaf_hash({"i": i}) for i in range(n)]
        root = M.root_from_leaf_hashes(lh).hex()
        levels = M.levels_from_leaf_hashes(lh)
        pos, proof = n, []
        for level in levels[:-1]:
            sib = pos ^ 1
            if sib >= len(level):
                break
            proof.append({"sibling": level[sib].hex(), "side": "left" if sib < pos else "right"})
            pos //= 2
        self.assertTrue(len(proof) == len(levels) - 1)
        self.assertTrue(M.verify_inclusion(lh[-1].hex(), proof, root))


class Stats(unittest.TestCase):
    def test_historical_mcnemar(self):
        self.assertAlmostEqual(S.mcnemar_exact(2, 4), 0.6875)

    def test_mcnemar_symmetry_and_zero(self):
        self.assertEqual(S.mcnemar_exact(0, 0), 1.0)
        self.assertEqual(S.mcnemar_exact(3, 9), S.mcnemar_exact(9, 3))

    def test_holm_monotone(self):
        h = S.holm({"a": 0.01, "b": 0.04, "c": 0.03})
        self.assertAlmostEqual(h["a"], 0.03)
        self.assertGreaterEqual(h["b"], h["c"])

    def test_zero_denominator(self):
        r = S.one_vs_rest(["A", "A", "B"], [None, None, None])
        self.assertIsNone(r["per_label"]["A"]["precision"])
        self.assertIn("A", r["zero_denominator_labels"])

    def test_bootstrap_identical_arms_zero(self):
        x = [True, False] * 10
        r = S.stratified_bootstrap(x, x, ["t"] * 20, reps=200)
        self.assertEqual(r["ci95"], [0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
