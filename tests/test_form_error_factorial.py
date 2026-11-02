"""Bounded challenge generator and factorial LOMO regression tests."""
import copy,importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"experiments"/"form_error_factorial"/"run.py"
spec=importlib.util.spec_from_file_location("factorial",SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class FactorialChecks(unittest.TestCase):
    def setUp(self):
        self.source={"p1":dict(id="p1",name_given="Lanny564",name_family="Volkman526",postcode="02110",source_sha256="0"*64),
                     "p2":dict(id="p2",name_given="Keren761",name_family="Hoppe518",postcode="00000",source_sha256="1"*64)}
    def test_names_digits_are_significant(self):
        row={"patient_id":"p1","field":"given_name","observed":"Lanny","observed_patient":"p1"}
        self.assertEqual(m.recover(row,self.source,set()),"Lanny")
        self.assertEqual(m.recover(row,self.source,{"name_suffix"}),"Lanny564")
    def test_confusable_preserves_numeric_suffix(self):
        row={"patient_id":"p2","field":"family_name","observed":"H0ppe518","observed_patient":"p2"}
        self.assertEqual(m.recover(row,self.source,{"ocr_confusable"}),"Hoppe518")
        self.assertEqual(m.recover(row,self.source,set()),"H0ppe518")
    def test_postal_all_zero(self):
        row={"patient_id":"p2","field":"postcode","observed":"0","observed_patient":"p2"}
        self.assertEqual(m.recover(row,self.source,{"postcode"}),"00000")
    def test_wrong_patient_binding(self):
        row={"patient_id":"p1","field":"family_name","observed":"Hoppe518","observed_patient":"p2"}
        self.assertEqual(m.recover(row,self.source,{"patient_bind"}),"Volkman526")
    def test_clean_control_unchanged(self):
        row={"patient_id":"p1","field":"family_name","observed":"Volkman526","observed_patient":"p1"}
        for module in (set(),set(m.MODULES)):
            self.assertEqual(m.recover(row,self.source,module),"Volkman526")
    def test_case_hash_mutation(self):
        x=[{"index":0,"patient_id":"x","observed":"A"},{"index":1,"patient_id":"y","observed":"B"}]
        _,a=m.merkle(x)
        y=copy.deepcopy(x);y[0]["observed"]="C"
        _,b=m.merkle(y)
        self.assertNotEqual(a,b)
        self.assertEqual(a,m.merkle(x)[1])
    def test_paired_mcnemar(self):
        self.assertAlmostEqual(m.mcnemar(2,4),0.6875)
        self.assertEqual(m.mcnemar(0,0),1)
    def test_form_html_escapes(self):
        row={"field":"family_name","observed":"<script>","patient_id":"X1"}
        self.assertNotIn("<script>",m.case_html(row))
        self.assertIn("&lt;script&gt;",m.case_html(row))
if __name__=="__main__":unittest.main()
