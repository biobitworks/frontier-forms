import sys, unittest
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'src'))
from frontier_forms.fhir_draft import normalize_field, validate_fields, draft_fhir, score_fields, confusion, FORM_FIELDS

FIXTURE = {'Synthetic case': 'fco-form-test0001', 'Patient first': 'Test123', 'Patient last': 'Case456', 'Birth date': '1970-02-22',
           'Gender': 'F', 'Encounter date': '1988-04-17', 'Visit class': 'wellness'}


class TestFhirDraft(unittest.TestCase):
    def test_normalization_is_deterministic_and_lossless_for_valid_values(self):
        self.assertEqual(normalize_field('Gender', 'F'), 'female')
        self.assertEqual(normalize_field('Birth date', '1970/2/22'), '1970-02-22')
        self.assertEqual(normalize_field('Birth date', 'Feb 22 1970'), 'Feb 22 1970')  # not silently coerced
        self.assertIsNone(normalize_field('Patient first', '   '))

    def test_validation_and_fco_identity_cross_check(self):
        ok = validate_fields(FIXTURE, 'fco-form-test0001')
        self.assertTrue(all(v == 'OK' for v in ok.values()))
        cross = validate_fields(FIXTURE, 'fco-form-OTHER')
        self.assertEqual(cross['Synthetic case'], 'CASE_ID_MISMATCH_WITH_FCO')
        bad = validate_fields(dict(FIXTURE, **{'Encounter date': '1960-01-01', 'Gender': 'X', 'Birth date': '22/02/1970'}), 'fco-form-test0001')
        self.assertEqual(bad['Gender'], 'INVALID_GENDER'); self.assertEqual(bad['Birth date'], 'INVALID_DATE')
        missing = validate_fields({}, 'fco-form-test0001')
        self.assertTrue(all(v == 'MISSING' for v in missing.values()))

    def test_encounter_before_birth_rejected(self):
        bad = validate_fields(dict(FIXTURE, **{'Encounter date': '1960-01-01'}), 'fco-form-test0001')
        self.assertEqual(bad['Encounter date'], 'ENCOUNTER_BEFORE_BIRTH')

    def test_draft_fhir_shape_and_determinism(self):
        a = draft_fhir(FIXTURE, 'fco:abc'); b = draft_fhir(dict(FIXTURE), 'fco:abc')
        self.assertEqual(a, b)
        pat, enc = a['entry'][0]['resource'], a['entry'][1]['resource']
        self.assertEqual(pat['resourceType'], 'Patient'); self.assertEqual(pat['gender'], 'female'); self.assertEqual(pat['birthDate'], '1970-02-22')
        self.assertEqual(enc['class']['code'], 'AMB'); self.assertEqual(enc['subject']['reference'], 'Patient/' + pat['id'])
        self.assertEqual(a['meta']['tag'][0]['code'], 'PROHIBITED')
        self.assertNotEqual(draft_fhir(FIXTURE, 'fco:other')['entry'][0]['resource']['id'], pat['id'])
        self.assertNotIn('Test123', pat['id'])  # identifiers never derive from field values

    def test_scorer_and_confusion_null_denominators(self):
        s = score_fields(dict(FIXTURE, Gender='M'), FIXTURE)
        self.assertFalse(s['Gender']); self.assertEqual(sum(s.values()), len(FORM_FIELDS) - 1)
        c = confusion({f: False for f in FORM_FIELDS}, {f: True for f in FORM_FIELDS})
        self.assertIsNone(c['FDR']); self.assertEqual(c['FN'], 7); self.assertEqual(c['AUROC'], 'NOT_COMPUTED_NO_CONTINUOUS_SCORES')
        c2 = confusion({f: True for f in FORM_FIELDS}, {f: (f != 'Gender') for f in FORM_FIELDS})
        self.assertEqual(c2['FP'], 1); self.assertAlmostEqual(c2['FDR'], 1 / 7)


if __name__ == '__main__':
    unittest.main()
