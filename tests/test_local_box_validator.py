"""Standard-library-only provenance and isolation tests for the local CPU vision lane."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"data/forms_vision_v1"
OUT=ROOT/"evidence/forms_box_validator/run_v3"
CANON=lambda x: json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
SHA=lambda b:hashlib.sha256(b).hexdigest()


def independent_root(items):
    nodes=[hashlib.sha256(b"\x00"+CANON(x)).digest() for x in items]
    if not nodes:return hashlib.sha256(b"\x00EMPTY").hexdigest()
    while len(nodes)>1:
        nxt=[]
        for i in range(0,len(nodes),2):
            right=nodes[i+1] if i+1<len(nodes) else nodes[i]
            nxt.append(hashlib.sha256(b"\x01"+nodes[i]+right).digest())
        nodes=nxt
    return nodes[0].hex()


class LocalBoxEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary=json.loads((OUT/"summary.json").read_text())
        cls.weights=json.loads((OUT/"weights.json").read_text())
        cls.manifest=json.loads((OUT/"input_manifest.json").read_text())
        cls.rows=[json.loads(l) for l in (OUT/"predictions.jsonl").read_text().splitlines() if l]
        cls.gold=json.loads((SRC/"GOLD_BOXES.json").read_text())

    def test_training_is_blank_only_with_no_patient_identity(self):
        self.assertEqual(len(self.manifest["train_keys"]),3)
        self.assertTrue(all(self.gold[k]["patient_id"] is None for k in self.manifest["train_keys"]))
        self.assertEqual(self.summary["n_train_images"],3)
        self.assertEqual(self.summary["n_test_patients"],18)

    def test_all_image_bytes_pinned(self):
        self.assertEqual(len(self.manifest["images"]),57)
        for r in self.manifest["images"]:
            self.assertEqual(SHA((SRC/r["image"]).read_bytes()),r["sha256"])
        self.assertEqual(SHA((SRC/"GOLD_BOXES.json").read_bytes()),self.summary["source_metadata_sha256"])

    def test_learned_weights_identity(self):
        bare={k:v for k,v in self.weights.items() if k!="model_sha256"}
        self.assertEqual(SHA(CANON(bare)),self.summary["weights_sha256"])
        self.assertEqual(self.weights["model_sha256"],self.summary["weights_sha256"])
        self.assertEqual(len(self.weights["coef"]),len(self.weights["features"]))

    def test_prediction_root_independent_exact_byte_replay(self):
        leaves=[]
        self.assertEqual(len(self.rows),54)
        for row in self.rows:
            self.assertIsNotNone(self.gold[row["id"]]["patient_id"])
            self.assertEqual(len(row["trained_detector"]["field_hits"]),len(self.gold[row["id"]]["fields"]))
            leaves.append({"id":row["id"],"image_sha256":row["image_sha256"],
                           "pred_box_sha256":SHA(CANON(row["box_predictions"])),
                           "learned_hit":row["trained_detector"]["true_positive"],
                           "control_hit":row["control_contour_detector"]["true_positive"]})
        self.assertEqual(independent_root(leaves),self.summary["prediction_root"])

    def test_claim_gate_does_not_promote_zero_gain(self):
        s=self.summary
        self.assertEqual(s["n_field_boxes"],540)
        self.assertEqual(s["learned_minus_baseline_recall"],0)
        self.assertEqual(s["mcnemar_exact_two_sided"],1.0)
        self.assertEqual(s["paired_patient_bootstrap_95_ci"],[0,0])
        self.assertEqual(s["model_answer_correctness"],"NOT_TESTED")
        self.assertEqual(s["promotion"],"DISCOVERY_ONLY_NOT_INDEPENDENT_LAYOUT_REPLICATION")
        self.assertEqual(s["external_inference"],"NONE")

    def test_mutation_detected_by_hash(self):
        r=self.manifest["images"][0]
        self.assertNotEqual(SHA((SRC/r["image"]).read_bytes()+b"X"),r["sha256"])

if __name__=="__main__":unittest.main()
