"""SFT data for the frontier-forms field mapper: no test leakage, bound to manifest."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "src"))
from frontier_forms.forms.sft_data import parse_completion  # noqa: E402

D = R / "data/forms_sft_v1"


class TestSFTData(unittest.TestCase):
    def test_no_test_patients_or_heldout_layout(self):
        cohort = json.loads((R / "data/forms_cohort_v1/MANIFEST.json").read_text())
        test_ids = {m["patient_id"] for m in cohort["members"] if m["split"] == "test"}
        for split in ("train", "validation"):
            for line in (D / f"{split}.jsonl").read_text().splitlines():
                r = json.loads(line)
                self.assertNotIn(r["patient_id"], test_ids)
                self.assertNotEqual(r["template_key"], "urgent_care_history_v1")

    def test_bound_to_manifest(self):
        man = json.loads((D / "MANIFEST.json").read_text())
        for split in ("train", "validation"):
            self.assertEqual(hashlib.sha256((D / f"{split}.jsonl").read_bytes()).hexdigest(), man[split]["sha256"])

    def test_malformed_output_abstains(self):
        self.assertEqual(parse_completion('{"decision": "fill", "value": "x"} trailing'), ("fill", "x"))
        self.assertEqual(parse_completion("I think the answer is x"), ("needs_user_input", None))
        self.assertEqual(parse_completion('{"decision": "fill", "value": ""}'), ("needs_user_input", None))


if __name__ == "__main__":
    unittest.main()
