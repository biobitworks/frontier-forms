"""Local synthetic form server, frozen cohort, frozen B0 and gold oracle."""
import hashlib
import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "src"))

from frontier_forms.forms import b0  # noqa: E402
from frontier_forms.forms.cohort import cohort_root, load_cohort, merkle_root  # noqa: E402
from frontier_forms.forms.harness import jsonl, run_arm, score_field, summarize, per_field_accuracy  # noqa: E402
from frontier_forms.forms.oracle import GOLD_RULES  # noqa: E402
from frontier_forms.forms.server import FormState, serve  # noqa: E402
from frontier_forms.forms.templates import load_templates, public_schema, render_html  # noqa: E402

COHORT = R / "data/forms_cohort_v1"
FREEZE = json.loads((R / "evidence/forms_b0/B0_FREEZE_V1.json").read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class TestFrozenCohort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((COHORT / "MANIFEST.json").read_text())
        cls.members, cls.bundles = load_cohort(COHORT / "bundles")

    def test_exactly_100_distinct_patients(self):
        self.assertEqual(len(self.members), 100)
        self.assertEqual(len({m.patient_id for m in self.members}), 100)
        self.assertEqual(self.manifest["n_patients"], 100)

    def test_subset_bytes_match_manifest(self):
        by_id = {m.patient_id: m for m in self.members}
        for row in self.manifest["members"]:
            self.assertEqual(by_id[row["patient_id"]].sha256, row["subset_sha256"])
            self.assertEqual(by_id[row["patient_id"]].split, row["split"])

    def test_cohort_root_matches_freeze(self):
        root = cohort_root(self.members)
        self.assertEqual(root, self.manifest["subset_cohort_root"])
        self.assertEqual(root, FREEZE["dataset"]["subset_cohort_root"])
        self.assertEqual(sha(COHORT / "MANIFEST.json"), FREEZE["dataset"]["manifest_sha256"])

    def test_all_patients_synthetic_and_living(self):
        for b in self.bundles.values():
            p = next(e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == "Patient")
            self.assertNotIn("deceasedDateTime", p)

    def test_merkle_root_detects_single_leaf_mutation(self):
        leaves = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(7)]
        mutated = list(leaves)
        mutated[3] = hashlib.sha256(b"x").hexdigest()
        self.assertNotEqual(merkle_root(leaves), merkle_root(mutated))
        self.assertNotEqual(merkle_root(leaves), merkle_root(leaves[::-1]))


class TestFreezePins(unittest.TestCase):
    def test_b0_oracle_harness_importer_pinned(self):
        self.assertEqual(sha(R / FREEZE["arm"]["file"]), FREEZE["arm"]["sha256"], "B0 changed: supersede, do not edit")
        self.assertEqual(sha(R / FREEZE["oracle"]["file"]), FREEZE["oracle"]["sha256"])
        self.assertEqual(sha(R / FREEZE["harness"]["file"]), FREEZE["harness"]["sha256"])
        self.assertEqual(sha(R / FREEZE["teammate_passport_builder"]["file"]),
                         FREEZE["teammate_passport_builder"]["sha256"])

    def test_templates_pinned(self):
        tdir = R / "src/frontier_forms/forms/templates"
        self.assertEqual({p.name: sha(p) for p in sorted(tdir.glob("*.json"))}, FREEZE["templates"])

    def test_oracle_is_independent_of_b0_and_passport(self):
        src = (R / "src/frontier_forms/forms/oracle.py").read_text()
        for banned in ("import b0", "from .b0", "passport", "import_fhir"):
            self.assertNotIn(banned, src.split('"""', 2)[-1])

    def test_every_canonical_key_has_a_declared_rule(self):
        for t in load_templates().values():
            for f in t["fields"]:
                self.assertIn(f["canonical_key"], GOLD_RULES)


class TestScoring(unittest.TestCase):
    def test_list_is_order_insensitive(self):
        g = {"decision": "fill", "value": ["a", "B"], "kind": "list", "required": True}
        self.assertTrue(score_field(g, {"decision": "fill", "value": "b; A"})["correct"])
        self.assertFalse(score_field(g, {"decision": "fill", "value": "a"})["correct"])

    def test_fabricated_answer_is_unsupported(self):
        g = {"decision": "needs_user_input", "value": None, "kind": "scalar", "required": True}
        self.assertEqual(score_field(g, {"decision": "fill", "value": "None"})["outcome"], "unsupported_fill")
        self.assertTrue(score_field(g, {"decision": "needs_user_input", "value": None})["correct"])

    def test_number_tolerance(self):
        g = {"decision": "fill", "value": 70.1, "kind": "number", "required": False}
        self.assertTrue(score_field(g, {"decision": "fill", "value": 70.12})["correct"])
        self.assertFalse(score_field(g, {"decision": "fill", "value": 154.5})["correct"])


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        members, bundles = load_cohort(COHORT / "bundles", limit=3)
        cls.members = members
        cls.state = FormState(members, bundles, load_templates())
        cls.httpd = serve(cls.state)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return r.status, r.read().decode()

    def post(self, path, payload):
        req = urllib.request.Request(self.base + path, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_refuses_non_loopback_bind(self):
        with self.assertRaises(ValueError):
            serve(self.state, host="0.0.0.0")

    def test_form_and_schema_hide_canonical_keys(self):
        for key, t in load_templates().items():
            _, html = self.get(f"/forms/{key}")
            _, schema = self.get(f"/forms/{key}/schema")
            self.assertIn("SYNTHETIC DEMO FORM", html)
            for f in t["fields"]:
                self.assertNotIn(f["canonical_key"], html)
                self.assertNotIn(f["canonical_key"], schema)

    def test_fhir_read_only_r4(self):
        _, meta = self.get("/fhir/R4/metadata")
        self.assertEqual(json.loads(meta)["fhirVersion"], "4.0.1")
        pid = self.members[0].patient_id
        _, pat = self.get(f"/fhir/R4/Patient/{pid}")
        self.assertEqual(json.loads(pat)["id"], pid)
        _, bundle = self.get(f"/fhir/R4/Condition?patient={pid}")
        self.assertEqual(json.loads(bundle)["type"], "searchset")
        code, _ = self.post("/fhir/R4/Patient", {"resourceType": "Patient"})
        self.assertEqual(code, 405)

    def test_submit_rejects_unknown_field_keys(self):
        pid = self.members[0].patient_id
        code, body = self.post("/forms/new_patient_registration_v1/submit",
                               {"patient_id": pid, "answers": [{"field_key": "ssn", "decision": "fill", "value": "x"}]})
        self.assertEqual((code, body["error"]), (422, "FIELD_KEY_CONTRACT_VIOLATION"))

    def test_b0_reads_only_served_html(self):
        t = load_templates()["urgent_care_history_v1"]
        fields = b0.inspect_form(render_html(t))
        self.assertEqual([f["name"] for f in fields], [f["field_key"] for f in t["fields"]])
        self.assertNotIn("canonical_key", json.dumps(public_schema(t)))


class TestB0Replay(unittest.TestCase):
    def test_full_run_reproduces_frozen_predictions(self):
        members, bundles = load_cohort(COHORT / "bundles", limit=100)
        state = FormState(members, bundles, load_templates())
        httpd = serve(state)
        try:
            rows = run_arm(f"http://127.0.0.1:{httpd.server_address[1]}", members, bundles,
                           load_templates(), b0.fill_plan, b0.B0_VERSION)
        finally:
            httpd.shutdown()
            httpd.server_close()
        self.assertEqual(len(rows), FREEZE["run_v1"]["n_cases"])
        self.assertTrue(all(r["echo_validated"] for r in rows))
        self.assertEqual(hashlib.sha256(jsonl(rows)).hexdigest(), FREEZE["run_v1"]["predictions_sha256"])
        committed = (R / "evidence/forms_b0/run_v1/predictions.jsonl").read_bytes()
        self.assertEqual(jsonl(rows), committed)
        s = summarize(rows)
        self.assertEqual(s["overall"]["forms"], 218)
        self.assertTrue(per_field_accuracy(rows))


if __name__ == "__main__":
    unittest.main()
