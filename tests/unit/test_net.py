"""The network layer: size caps on downloads."""

import io
import unittest
from unittest import mock

from support import ManagerError

from osat_manager_restic.net import Network


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class SizeCaps(unittest.TestCase):

    def fetch(self, size, max_bytes):
        with mock.patch("urllib.request.urlopen",
                        lambda *a, **k: Response(b"x" * size)):
            return Network().fetch("https://example.invalid/f", max_bytes=max_bytes)

    def test_a_download_within_the_cap_is_returned(self):
        self.assertEqual(len(self.fetch(1024, 1024)), 1024)

    def test_a_download_over_the_cap_is_refused(self):
        with self.assertRaises(ManagerError) as caught:
            self.fetch(1025, 1024)
        self.assertIn("larger than", str(caught.exception))

    def test_the_signature_and_checksums_are_capped_small(self):
        from osat_manager_restic import manager
        self.assertLessEqual(manager.SMALL_FILE, 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
