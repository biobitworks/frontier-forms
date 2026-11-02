"""A fabricated result with the same 38 keys must never inherit the frozen root."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import export_private_stats as exp

ROOT=Path(__file__).resolve().parent.parent
class SourceByteGate(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.r=Path(self.t.name)
        b=self.r/'evidence/freeze/predecessor'
        b.mkdir(parents=True)
        for name in ('manifest.json','leaves.jsonl'):
            shutil.copyfile(ROOT/'evidence/freeze/predecessor'/name,b/name)
        self.src=self.r/'source'
        (self.src/'eval').mkdir(parents=True)
    def test_identical_keys_fake_content_fails_before_export(self):
        e=self.src/'eval'
        for name in exp.REQUIRED_FROZEN_INPUTS:
            p=self.src/name
            p.write_text('{"row_key_sha256":"can-be-matched","gold":"A","correct":true}\n')
        with patch.object(exp,'repo',self.r):
            with self.assertRaisesRegex(AssertionError,'PRIVATE_SOURCE_HASH_MISMATCH'):
                exp.export(self.src)
        self.assertFalse((self.r/'evidence/stats/discovery_pair_flags.jsonl').exists())
    def test_missing_input_fails_closed(self):
        with patch.object(exp,'repo',self.r):
            with self.assertRaisesRegex(AssertionError,'PRIVATE_SOURCE_MISSING'):
                exp.verify_private_export_inputs(self.src)
    def test_forged_manifest_root_fails(self):
        p=self.r/'evidence/freeze/predecessor/manifest.json'
        m=json.loads(p.read_text())
        m['root']='0'*64;p.write_text(json.dumps(m))
        with patch.object(exp,'repo',self.r):
            with self.assertRaises(AssertionError):
                exp.verify_private_export_inputs(self.src)
