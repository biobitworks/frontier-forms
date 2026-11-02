import tempfile,unittest
from pathlib import Path
from scripts.check_public_payloads import check,ALLOWED_SYNTHETIC,ROOT
class PublicPayloadTests(unittest.TestCase):
    def test_valid_public_synthetic_file(self):
        self.assertEqual(check(list(ALLOWED_SYNTHETIC),ROOT),"PASS")
    def test_unallowlisted_binary_fails(self):
        with self.assertRaisesRegex(AssertionError,"PUBLIC_PROHIBITED_FILE"):
            check(["private/model.safetensors"],ROOT)
    def test_mutated_allowlisted_fixture_fails(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/next(iter(ALLOWED_SYNTHETIC))
            p.parent.mkdir(parents=True)
            p.write_bytes(b"forged-but-public")
            with self.assertRaisesRegex(AssertionError,"PUBLIC_ALLOWLIST_HASH_MISMATCH"):
                check(list(ALLOWED_SYNTHETIC),Path(t))
