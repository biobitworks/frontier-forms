"""Prebuilt error-injected forms, preregistration binding and detector evidence."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "src"))
from frontier_forms.forms.detectors import load_lean_flags, m1_merkle  # noqa: E402

D = R / "data/forms_injected_v1"
E = R / "evidence/forms_detectors/run_v1"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class TestDetectorEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = json.loads((D / "PREREG.json").read_text())
        cls.forms = [json.loads(x) for x in (D / "forms.jsonl").read_text().splitlines()]
        cls.truth = [json.loads(x) for x in (D / "truth.jsonl").read_text().splitlines()]
        cls.result = json.loads((E / "DETECTOR_RESULTS_V1.json").read_text())

    def test_data_bound_to_prereg(self):
        self.assertEqual(sha(D / "forms.jsonl"), self.prereg["dataset"]["forms_sha256"])
        self.assertEqual(sha(D / "truth.jsonl"), self.prereg["dataset"]["truth_sha256"])
        self.assertEqual(self.result["prereg_sha256"], sha(D / "PREREG.json"))

    def test_forms_hide_ground_truth(self):
        for f in self.forms[:50]:
            self.assertNotIn("error", json.dumps(f).lower().replace("error_", ""))

    def test_merkle_breakpoints_are_exactly_the_tampered_fields(self):
        tampered = {}
        for t in self.truth:
            if t["error_type"] == "E5_post_seal_tamper":
                tampered.setdefault(t["form_id"], set()).update(t["fields"])
        for f in self.forms:
            res = m1_merkle(f)
            self.assertEqual(res["flags"], tampered.get(f["form_id"], set()))
            self.assertEqual(res["root_match"], f["form_id"] not in tampered)

    def test_lean_output_bound_to_receipt(self):
        receipt = json.loads((E / "LEAN4_RECEIPT.json").read_text())
        self.assertEqual(sha(E / "lean_flags.jsonl"), receipt["output_sha256"])
        self.assertEqual(sha(R / "lean/FormChecks.lean"), receipt["source_sha256"])
        self.assertEqual(self.result["lean_flags_sha256"], receipt["output_sha256"])
        self.assertEqual(set(load_lean_flags(E / "lean_flags.jsonl")), {f["form_id"] for f in self.forms})

    def test_attribution_only_on_single_leaf_edges(self):
        for e in self.result["edges"]:
            a = set() if e["parent"] == "none" else set(e["parent"].split("+"))
            self.assertEqual(len(set(e["child"].split("+")) - a), 1)


if __name__ == "__main__":
    unittest.main()
