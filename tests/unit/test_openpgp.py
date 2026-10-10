"""The OpenPGP verifier, against restic's real 0.19.1 signature and the
pinned key in manager.yaml."""

import base64
import unittest

from support import REPO, zip_member

from osat_manager_restic.manifest import load_manifest
from osat_manager_restic.openpgp import (SignatureError, crc24, dearmor,
                                         keys, verify)

SUMS = zip_member("restic-release-signature.zip", "SHA256SUMS")
SIG = zip_member("restic-release-signature.zip", "SHA256SUMS.asc").decode()
KEY = load_manifest(REPO / "manager.yaml")["verification"]["signing_key"]


def rearmor(data: bytes, kind="SIGNATURE") -> str:
    body = base64.b64encode(data).decode()
    lines = [body[i:i + 64] for i in range(0, len(body), 64)]
    check = base64.b64encode(crc24(data).to_bytes(3, "big")).decode()
    return "\n".join([f"-----BEGIN PGP {kind}-----", "", *lines,
                      f"={check}", f"-----END PGP {kind}-----", ""])


class RealSignature(unittest.TestCase):

    def test_the_pinned_key_has_the_documented_fingerprint(self):
        self.assertIn("CF8F18F2844575973F79D4E191A6868BD3F7A907",
                      [k.fingerprint for k in keys(KEY["public_key"])])

    def test_restic_0_19_1_checksums_verify(self):
        self.assertEqual(verify(SUMS, SIG, KEY["public_key"],
                                KEY["fingerprint"]), KEY["fingerprint"])

    def test_a_changed_checksum_file_is_refused(self):
        changed = SUMS.replace(b"darwin", b"darwen", 1)
        with self.assertRaises(SignatureError):
            verify(changed, SIG, KEY["public_key"], KEY["fingerprint"])

    def test_a_changed_signature_value_is_refused(self):
        data = bytearray(dearmor(SIG, "SIGNATURE"))
        data[-1] ^= 0x01                      # last byte of the RSA value
        with self.assertRaises(SignatureError):
            verify(SUMS, rearmor(bytes(data)), KEY["public_key"],
                   KEY["fingerprint"])

    def test_a_damaged_armor_checksum_is_refused(self):
        damaged = SIG.replace(SIG.strip().splitlines()[3][:4],
                              "AAAA" if SIG.strip().splitlines()[3][:4] != "AAAA" else "BBBB", 1)
        with self.assertRaises(SignatureError):
            verify(SUMS, damaged, KEY["public_key"], KEY["fingerprint"])

    def test_another_pinned_fingerprint_is_refused(self):
        with self.assertRaises(SignatureError):
            verify(SUMS, SIG, KEY["public_key"], "00" * 20)


if __name__ == "__main__":
    unittest.main()
