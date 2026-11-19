"""Regressions from the adversarial review of the assembled library."""

import unittest

from tests import support as S


class HealthVerdict(unittest.TestCase):

    def setUp(self):
        self.vit = S.load_vitals()

    def test_zero_healthy_checks_is_incomplete(self):
        state, note = self.vit._verdict_health(
            "0 out of 260 checks are healthy\n"
            "0 out of 260 checks are unhealthy\n")
        self.assertEqual(state, self.vit.INCOMPLETE)
        self.assertIn("no positive healthy-check evidence", note)

    def test_positive_healthy_checks_still_pass(self):
        state, _note = self.vit._verdict_health(
            "260 out of 260 checks are healthy\n"
            "0 out of 260 checks are unhealthy\n")
        self.assertEqual(state, self.vit.PASS)

    def test_skipped_or_unaccounted_checks_are_incomplete(self):
        for text in (
                "259 out of 260 checks are healthy\n"
                "0 out of 260 checks are unhealthy\n"
                "1 out of 260 checks are skipped\n",
                "1 out of 2 checks are healthy\n"
                "0 out of 2 checks are unhealthy\n"):
            with self.subTest(text=text):
                state, _note = self.vit._verdict_health(text)
                self.assertEqual(state, self.vit.INCOMPLETE)


if __name__ == "__main__":
    unittest.main()
