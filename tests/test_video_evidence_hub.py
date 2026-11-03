"""Independent source-byte and claim-ceiling checks for video presentation.

No new inference, external API or statistical resampling.
"""
import hashlib,json,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"docs/judges/VIDEO_EVIDENCE_MANIFEST_20261102.json"
class VideoEvidenceHub(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=json.loads(PATH.read_bytes())
 def test_source_exact_bytes_from_predecessor(self):
  for s in self.d["source_receipts"]:
   blob=subprocess.check_output(["git","show",self.d["parent_git_sha"]+":"+s["path"]],cwd=ROOT)
   self.assertEqual(hashlib.sha256(blob).hexdigest(),s["sha256"],s["path"])
   self.assertEqual(len(blob),s["byte_count"])
 def test_complete_scope_and_identity(self):
  self.assertEqual(self.d["program_id"],"frontier-forms")
  self.assertEqual(len(self.d["results"]),8)
  self.assertEqual(len(self.d["source_receipts"]),10)
  self.assertEqual(self.d["scientific_superiority_promotions"],0)
  self.assertEqual(len(self.d["roots"]),4)
  self.assertEqual(sum(len(x["epochs"]) for x in self.d["yolo_epoch_groups"]),60)
 def test_matched_causal_claim_bounds(self):
  byid={x["id"]:x for x in self.d["results"]}
  self.assertAlmostEqual(byid["FF-FCO-L1L3"]["delta"],12/54)
  self.assertAlmostEqual(byid["FF-OCR-A1"]["delta"],8/46)
  self.assertAlmostEqual(byid["FF-OCR-A2"]["delta"],-5/46)
  self.assertEqual(byid["FF-BOX-LOGISTIC"]["delta"],0)
  for x in self.d["results"]:
   self.assertEqual(x["delta"],(x["challenger_correct"]-x["baseline_correct"])/x["n_cases"])
   self.assertIn(x["scientific_admission"],("HOLD","NOT_PROMOTED"))
   self.assertTrue(x["evidence_admission"].startswith("ADMITTED_"))
   self.assertNotIn("SUPPORTED_GAIN",x["finding"])
   self.assertTrue(x["source_file_sha256"])
 def test_source_roots_are_independent(self):
  roots=[x["root"] for x in self.d["roots"]]
  self.assertEqual(len(set(roots)),len(roots))
  self.assertTrue(all(len(x)==64 and set(x)<=set("0123456789abcdef") for x in roots))
  self.assertIn("identity",self.d["roots"][3]["scope"])
 def test_software_and_model_claim_separated(self):
  self.assertFalse(any("NVIDIA" in c["model_or_weight"] for c in self.d["results"]))
  for t in self.d["sponsor_next"]:
   self.assertIn(t["state"],("PROPOSED_NOT_EXECUTED_THIS_LANE","TEAMMATE_SYNTHETIC_PILOT_ONLY","CI_IN_USE; ATTESTATIONS_PROPOSED"))
  hosted=self.d["hosted_benchmark"]
  self.assertEqual((hosted["n_runs"],hosted["n_pairs"]),(48,24))
  self.assertGreater(hosted["n_quality_regressions"],0)
 def test_admission_prevents_false_promotion(self):
  self.assertEqual(self.d["scientific_admission"],"HOLD_NO_INDEPENDENT_PI_ADMISSION")
  self.assertIn("REQUIRES prospective",self.d["evidence_admission_policy"]["SCIENTIFIC_PROMOTION"])
  for r in self.d["results"]:
   if r["delta"]>0:self.assertNotEqual(r["scientific_admission"],"SCIENTIFIC_GAIN_ADMITTED")
 def test_video_entry_html_exists(self):
  html=(ROOT/"docs/judges/VIDEO_EVIDENCE_STORYBOARD_20261102.html").read_text()
  self.assertIn("VIDEO_EVIDENCE_MANIFEST_20261102.json",html)
  self.assertIn("scientific",html.lower())
  self.assertIn("selected",html)
 def test_future_unverified_paths_not_promoted(self):
  self.assertEqual(self.d["presentation"]["github_pages"],"NOT_CONFIGURED_OR_UNVERIFIED")
  self.assertEqual(self.d["presentation"]["demo_url_local"].split(":",1)[0],"http")
if __name__=="__main__":unittest.main()
