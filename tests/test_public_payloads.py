import hashlib,tempfile,unittest
from pathlib import Path
from scripts.check_public_payloads import check,ALLOWED_SYNTHETIC,ROOT
class PublicPayloadTests(unittest.TestCase):
    def test_valid_public_synthetic_file(self):
        self.assertEqual(check(list(ALLOWED_SYNTHETIC),ROOT),"PASS")
    def test_unallowlisted_binary_fails(self):
        with self.assertRaisesRegex(AssertionError,"PUBLIC_PROHIBITED_FILE"):
            check(["private/model.safetensors"],ROOT)
    def test_allowlisted_exact_bytes_pass(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"fixtures/public.bin"; p.parent.mkdir(parents=True); p.write_bytes(b"public")
            allowed={"fixtures/public.bin":hashlib.sha256(b"public").hexdigest()}
            self.assertEqual(check(list(allowed),Path(t),allowed),"PASS")
    def test_mutated_allowlisted_fixture_fails(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"fixtures/public.bin"; p.parent.mkdir(parents=True); p.write_bytes(b"forged-but-public")
            allowed={"fixtures/public.bin":hashlib.sha256(b"public").hexdigest()}
            with self.assertRaisesRegex(AssertionError,"PUBLIC_ALLOWLIST_HASH_MISMATCH"):
                check(list(allowed),Path(t),allowed)
