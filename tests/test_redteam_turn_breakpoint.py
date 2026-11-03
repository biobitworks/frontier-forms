"""Final red-team TURN_BREAKPOINT: every pinned pointer re-hashes, nothing is SUPPORTED."""
import hashlib, json, unittest
from pathlib import Path

R = Path(__file__).resolve().parent.parent
BP = R / 'evidence/breakpoints/CLAUDE_REDTEAM_TURN_BREAKPOINT_FINAL.json'


class TestRedteamTurnBreakpoint(unittest.TestCase):
    def test_pointers_rehash(self):
        d = json.loads(BP.read_text())
        self.assertTrue(d['pointers'])
        for e in d['pointers']:
            self.assertEqual(hashlib.sha256((R / e['path']).read_bytes()).hexdigest(), e['sha256'], e['path'])

    def test_nothing_supported(self):
        d = json.loads(BP.read_text())
        self.assertEqual(d['states']['SUPPORTED'], [])
        self.assertTrue(d['synthetic_only'])
        self.assertFalse(d['weights_published'])


if __name__ == '__main__':
    unittest.main()
