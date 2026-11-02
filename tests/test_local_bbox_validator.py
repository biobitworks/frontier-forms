"""Geometry contracts for locally trained bbox model (stdlib only)."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from train_local_bbox_validator import intersection_over_union, score_boxes

class TestLocalBoundingBox(unittest.TestCase):
    def test_overlap_and_zero_division(self):
        self.assertEqual(intersection_over_union([0,0,10,10],[0,0,10,10]),1.0)
        self.assertEqual(intersection_over_union([0,0,10,10],[20,20,30,30]),0.0)
        self.assertEqual(intersection_over_union([0,0,0,0],[0,0,0,0]),0.0)
    def test_one_prediction_cannot_claim_two_gold_fields(self):
        x=score_boxes([[0,0,10,10],[0,0,10,10]],[[0,0,10,10]])
        self.assertEqual((x["tp"],x["fn"],x["fp"]),(1,1,0))
    def test_extra_prediction_is_false_positive(self):
        x=score_boxes([[0,0,10,10]],[[0,0,10,10],[20,20,30,30]])
        self.assertEqual((x["tp"],x["fn"],x["fp"]),(1,0,1))
    def test_iou50_threshold_is_inclusive(self):
        self.assertEqual(score_boxes([[0,0,2,2]],[[0,0,2,1]])["tp"],1)
        self.assertEqual(score_boxes([[0,0,2,2]],[[0,0,2,1]],threshold=.51)["tp"],0)

if __name__=="__main__": unittest.main()
