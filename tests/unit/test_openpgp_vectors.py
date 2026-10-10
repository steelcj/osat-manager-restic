"""Test vectors for the OpenPGP verifier.

Every vector records two expected verdicts: the verifier's, and gpg's.
The signatures are crafted by hand (pgpcraft.py), so gpg is the
independent check that each vector is what it claims to be: a vector
meant to be valid except for one property must verify in gpg wherever
gpg does not enforce that property. The verifier may differ from gpg
only where POLICY names the rule that makes it stricter; any other
disagreement, or gpg giving a verdict other than the recorded one,
fails the tests.

restic's real 0.19.1 signature is a vector too, so the strict rules can
never start rejecting a genuine release.
"""

import os
import random
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import support  # noqa: F401

from pgpcraft import (CREATED, Spec, armor, created, issuer_fpr, issuer_id,
                      key_block, load_key, packet, sign, signature_body, sub)
from support import REPO, zip_member

from osat_manager_restic.manifest import load_manifest
from osat_manager_restic.openpgp import SignatureError, verify

DATA = b"0123abcd  restic_0.19.1_linux_amd64.bz2\n"
KEY = load_key("rsa2048")
OTHER = load_key("other2048")
SMALL = load_key("rsa1024")
BLOCK = key_block(KEY)
SUBKEY_BLOCK = key_block(KEY, subkey=OTHER)
NOW = CREATED + 3600
GPG = shutil.which("gpg")
RESTIC_KEY = load_manifest(REPO / "manager.yaml")["verification"]["signing_key"]

# Rules under which the verifier is deliberately stricter than gpg.
POLICY = {
    "hash": "SHA-256, SHA-384 and SHA-512 only; gpg also accepts SHA-1 and SHA-224",
    "prefix": "the 16-bit hash prefix must match; gpg treats it as a hint",
    "issuer": "the hashed area must name the pinned fingerprint, and every issuer "
              "named must be the pinned key; gpg finds the key by any issuer",
    "unhashed": "the unhashed area, which nothing signs, may hold only issuer "
                "subpackets naming the pinned key; gpg ignores what it does not use",
    "subkey": "pinning a subkey's own fingerprint is the trust decision; gpg "
              "requires a binding signature from the primary key",
    "range": "the signature value must be below n, as RFC 8017 requires; gpg "
             "reduces it modulo n",
    "time": "a signature dated in the future is refused; gpg warns and verifies",
    "strict": "a signature block holds one canonically encoded signature packet "
              "and nothing else, in PGP SIGNATURE armor; gpg is lenient",
}


@dataclass
class Vector:
    name: str
    signature: Union[str, bytes]
    ours: str                      # "accept", or a phrase the refusal contains
    gpg: Optional[bool]            # gpg's verdict; None when gpg cannot be asked
    policy: str = ""               # a POLICY key, when ours and gpg differ
    data: bytes = DATA
    block: str = BLOCK
    fingerprint: str = KEY.fingerprint
    now: Optional[float] = NOW


def garbage_after_hash(k, t):
    return (b"\x00\x01" + b"\xff" * 8 + b"\x00" + t).ljust(k, b"\x00")


def short_padding(k, t):
    pad = k - len(t) - 3
    return b"\x00\x01" + b"\xff" * (pad - 9) + b"\x00" + b"\x01" * 8 + t


def block_type_two(k, t):
    return b"\x00\x02" + b"\xff" * (k - len(t) - 3) + b"\x00" + t


SHA512_PREFIX = bytes.fromhex("3051300d060960864801650304020305000440")
GOOD = signature_body(DATA, Spec(KEY))
GOOD_ARMOR = armor(packet(2, GOOD))
HASHED = created() + issuer_fpr(KEY)


def no_crc(text):
    return "\n".join(l for l in text.splitlines() if not l.startswith("=")) + "\n"


def vectors():
    restic_sums = zip_member("restic-release-signature.zip", "SHA256SUMS")
    restic_sig = zip_member("restic-release-signature.zip", "SHA256SUMS.asc").decode()
    v = [
        # Genuine and well formed
        Vector("restic 0.19.1, real", restic_sig, "accept", True,
               data=restic_sums, block=RESTIC_KEY["public_key"],
               fingerprint=RESTIC_KEY["fingerprint"], now=None),
        Vector("restic 0.19.1, changed data", restic_sig, "does not match", False,
               data=restic_sums.replace(b"darwin", b"darwen", 1),
               block=RESTIC_KEY["public_key"],
               fingerprint=RESTIC_KEY["fingerprint"], now=None),
        Vector("valid, SHA-256", sign(DATA, Spec(KEY)), "accept", True),
        Vector("valid, SHA-384", sign(DATA, Spec(KEY, hash_alg=9)), "accept", True),
        Vector("valid, SHA-512", sign(DATA, Spec(KEY, hash_alg=10)), "accept", True),
        Vector("valid, no armor checksum", no_crc(sign(DATA, Spec(KEY))), "accept", True),
        Vector("changed data", sign(DATA, Spec(KEY)), "does not match", False,
               data=DATA + b"x"),
        # Property 1: exact padding
        Vector("garbage after the hash", sign(DATA, Spec(KEY, encode=garbage_after_hash)),
               "does not match", False),
        Vector("short padding, garbage in front", sign(DATA, Spec(KEY, encode=short_padding)),
               "does not match", False),
        Vector("block type 2", sign(DATA, Spec(KEY, encode=block_type_two)),
               "does not match", False),
        Vector("DigestInfo for another hash", sign(DATA, Spec(KEY, prefix=SHA512_PREFIX)),
               "does not match", False),
        Vector("value not below n", sign(DATA, Spec(KEY, value=lambda s, n: s + n)),
               "out of range", True, policy="range"),
        Vector("1024-bit key", sign(DATA, Spec(SMALL)), "not a sound RSA key", True,
               block=key_block(SMALL), fingerprint=SMALL.fingerprint,
               policy="hash"),
        # Property 2: issuer
        Vector("no issuer", sign(DATA, Spec(KEY, hashed=created(), unhashed=b"")),
               "issuer", None),
        Vector("issuer only unhashed",
               sign(DATA, Spec(KEY, hashed=created(), unhashed=issuer_fpr(KEY))),
               "hashed area", False),
        Vector("second, conflicting issuer",
               sign(DATA, Spec(KEY, hashed=HASHED + issuer_fpr(OTHER))),
               "not the pinned", True, policy="issuer"),
        Vector("conflicting unhashed key ID",
               sign(DATA, Spec(KEY, unhashed=issuer_id(OTHER))),
               "key ID", True, policy="issuer"),
        Vector("issuer fingerprint of version 5 beside it",
               sign(DATA, Spec(KEY, hashed=HASHED + issuer_fpr(KEY, version=5))),
               "not the pinned", True, policy="issuer"),
        Vector("unknown critical subpacket",
               sign(DATA, Spec(KEY, hashed=HASHED + sub(100, b"x", critical=True))),
               "critical", False),
        Vector("expired", sign(DATA, Spec(KEY, hashed=HASHED + sub(3, (60).to_bytes(4, "big")))),
               "expired", False),
        Vector("made in the future",
               sign(DATA, Spec(KEY, hashed=created(CREATED + 400 * 86400) + issuer_fpr(KEY))),
               "future", True, policy="time"),
        Vector("unknown subpacket in the unhashed area",
               sign(DATA, Spec(KEY, unhashed=issuer_id(KEY) + sub(66, b"x"))),
               "unhashed area", True, policy="unhashed"),
        # Property 3: hashes
        Vector("MD5", sign(DATA, Spec(KEY, hash_alg=1)), "not accepted", False),
        Vector("SHA-1", sign(DATA, Spec(KEY, hash_alg=2)), "not accepted", True,
               policy="hash"),
        Vector("SHA-224", sign(DATA, Spec(KEY, hash_alg=11)), "not accepted", True,
               policy="hash"),
        # Property 4: hash prefix
        Vector("wrong hash prefix", sign(DATA, Spec(KEY, left16=b"\x00\x00")),
               "does not match", True, policy="prefix"),
        # A different key
        Vector("another key, naming itself",
               sign(DATA, Spec(OTHER, hashed=created() + issuer_fpr(OTHER),
                               unhashed=issuer_id(OTHER))),
               "not the pinned", False),
        Vector("another key, naming the pinned key",
               sign(DATA, Spec(OTHER, hashed=HASHED, unhashed=issuer_id(KEY))),
               "does not match", False),
        # Subkeys: pin the key that actually signs
        Vector("pinned subkey signs", sign(DATA, Spec(OTHER, hashed=created() + issuer_fpr(OTHER),
                                                      unhashed=b"")),
               "accept", False, policy="subkey",
               block=SUBKEY_BLOCK, fingerprint=OTHER.fingerprint),
        Vector("subkey signs, primary pinned",
               sign(DATA, Spec(OTHER, hashed=created() + issuer_fpr(OTHER), unhashed=b"")),
               "not the pinned", False, block=SUBKEY_BLOCK),
    ]
    # Property 5: malformed and truncated input
    malformed = [
        ("header only", armor(b"\xc2")),
        ("two-octet length cut short", armor(b"\xc2\xc5")),
        ("five-octet length cut short", armor(b"\xc2\xff\x00\x00")),
        ("zero-length packet", armor(b"\xc2\x00")),
        ("old format, length missing", armor(b"\x88")),
        ("old format, length cut short", armor(b"\x89\x00")),
        ("old format, indeterminate length", armor(b"\x8b" + GOOD)),
        ("partial length", armor(b"\xc2\xe0" + GOOD)),
        ("version byte only", armor(packet(2, b"\x04"))),
        ("version 3", armor(packet(2, b"\x03" + GOOD[1:]))),
        ("length runs past the end", armor(packet(2, GOOD)[:-5])),
        ("valid, then a stray header", armor(packet(2, GOOD) + b"\xc2")),
        ("valid, then a marker packet", armor(packet(2, GOOD) + packet(10, b"PGP"))),
        ("two signatures", armor(packet(2, GOOD) * 2)),
        ("trailing bytes after the value", armor(packet(2, GOOD + b"\x00"))),
        ("MPI bit count too large",
         armor(packet(2, GOOD[:-258] + (2049).to_bytes(2, "big") + GOOD[-256:]))),
        ("empty subpacket",
         armor(packet(2, signature_body(DATA, Spec(KEY, hashed=b"\x00" + HASHED))))),
        ("subpacket length cut short",
         armor(packet(2, signature_body(DATA, Spec(KEY, hashed=HASHED + b"\xff\x00"))))),
        ("message armor", armor(packet(2, GOOD), "MESSAGE")),
        ("public key armor", armor(packet(2, GOOD), "PUBLIC KEY BLOCK")),
        ("not armored", "not armored at all"),
        ("bad base64 character", GOOD_ARMOR.replace("\n\n", "\n\n!", 1)),
        ("short armor checksum", GOOD_ARMOR.replace("\n=", "\n=AB\n#", 1)),
    ]
    lenient = {"valid, then a marker packet", "two signatures",
               "trailing bytes after the value", "empty subpacket",
               "message armor", "public key armor"}
    v += [Vector(f"malformed: {name}", sig, "", name in lenient,
                 policy="strict" if name in lenient else "")
          for name, sig in malformed]
    v += [
        Vector("malformed: non-ASCII", GOOD_ARMOR.replace("\n\n", "\n\né", 1), "", None),
        Vector("malformed: bytes, not text", GOOD_ARMOR.encode(), "", None),
    ]
    return v


def ours_accepts(vector):
    try:
        verify(vector.data, vector.signature, vector.block, vector.fingerprint,
               now=vector.now)
        return True, ""
    except SignatureError as exc:
        return False, str(exc)


class Verdicts(unittest.TestCase):
    """The verifier's verdict on every vector."""

    def test_every_vector(self):
        for vector in vectors():
            with self.subTest(vector=vector.name):
                accepted, message = ours_accepts(vector)
                if vector.ours == "accept":
                    self.assertTrue(accepted, message)
                else:
                    self.assertFalse(accepted, "accepted")
                    self.assertIn(vector.ours, message)

    def test_disagreements_with_gpg_are_named_policies(self):
        for vector in vectors():
            with self.subTest(vector=vector.name):
                ours = vector.ours == "accept"
                if vector.gpg is not None and ours != vector.gpg:
                    self.assertIn(vector.policy, POLICY,
                                  "ours and gpg differ without a policy")
                if vector.policy:
                    self.assertIn(vector.policy, POLICY)


@unittest.skipUnless(GPG, "gpg is not installed to confirm the vectors")
class ConfirmedByGpg(unittest.TestCase):
    """gpg gives each vector the verdict recorded for it."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.homes = {}

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def home(self, block):
        if block not in self.homes:
            home = Path(self._tmp.name) / f"gnupg{len(self.homes)}"
            home.mkdir(mode=0o700)
            subprocess.run([GPG, "--batch", "--quiet", "--import"],
                           input=block.encode(), capture_output=True,
                           env=dict(os.environ, GNUPGHOME=str(home)))
            self.homes[block] = home
        return self.homes[block]

    def gpg_accepts(self, vector):
        work = Path(self._tmp.name)
        (work / "sig.asc").write_text(vector.signature)
        (work / "data").write_bytes(vector.data)
        result = subprocess.run(
            [GPG, "--batch", "--quiet", "--verify", str(work / "sig.asc"),
             str(work / "data")], capture_output=True,
            env=dict(os.environ, GNUPGHOME=str(self.home(vector.block))))
        return result.returncode == 0

    def test_gpg_agrees_with_every_recorded_verdict(self):
        for vector in vectors():
            if vector.gpg is None:
                continue
            with self.subTest(vector=vector.name):
                self.assertEqual(self.gpg_accepts(vector), vector.gpg)


class FailsClosed(unittest.TestCase):
    """Property 5, exhaustively: truncations and byte mutations."""

    def check(self, signature):
        return verify(DATA, signature, BLOCK, KEY.fingerprint, now=NOW)

    def test_every_truncation_fails_closed(self):
        body = packet(2, GOOD)
        for length in range(len(body)):
            with self.subTest(length=length):
                with self.assertRaises(SignatureError):
                    self.check(armor(body[:length]))

    def test_byte_mutations_fail_closed_or_change_nothing(self):
        body = packet(2, GOOD)
        rng = random.Random(4)
        for _ in range(3000):
            mutated = bytearray(body)
            mutated[rng.randrange(len(body))] = rng.randrange(256)
            try:
                self.check(armor(bytes(mutated)))
            except SignatureError:
                continue
            self.assertEqual(bytes(mutated), body, "a changed signature verified")

    def test_malformed_key_blocks_fail_closed(self):
        good = sign(DATA, Spec(KEY))
        blocks = {
            "empty key packet": armor(packet(6, b"\x04"), "PUBLIC KEY BLOCK"),
            "truncated key": armor(packet(6, KEY.body[:-3]), "PUBLIC KEY BLOCK"),
            "oversized key packet": armor(packet(6, b"\x04" + b"\x00" * 70000),
                                          "PUBLIC KEY BLOCK"),
            "signature armor": armor(packet(6, KEY.body), "SIGNATURE"),
            "n is zero": armor(packet(6, b"\x04\x00\x00\x00\x00\x01\x00\x00"
                                         b"\x00\x02\x01\x00\x01"), "PUBLIC KEY BLOCK"),
        }
        for label, block in blocks.items():
            with self.subTest(block=label):
                with self.assertRaises(SignatureError):
                    verify(DATA, good, block, KEY.fingerprint, now=NOW)


if __name__ == "__main__":
    unittest.main()
