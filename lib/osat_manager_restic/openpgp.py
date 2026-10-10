"""Verifying an OpenPGP detached signature with the standard library.

restic signs each release's SHA256SUMS with an RSA key and publishes the
signature as SHA256SUMS.asc. This module checks such a signature against
one pinned key (RFC 4880, RFC 9580 where they differ):

- the armor is a PGP SIGNATURE or PGP PUBLIC KEY BLOCK, with strict
  base64 and, when present, a correct checksum;
- every packet, subpacket and MPI is read with bounds checks, MPIs must
  be canonical, and nothing may follow the signature's value;
- the signature is version 4, of a document (type 0x00 or 0x01), made
  with RSA and the key's own algorithm, over SHA-256, SHA-384 or SHA-512
  only;
- its hashed area names the pinned fingerprint as issuer, every issuer
  it names anywhere is the pinned key, no critical subpacket is unknown,
  and it has not expired; its unhashed area, which nothing signs, may
  hold only issuer subpackets naming the pinned key;
- the 16-bit hash prefix matches, the signature value lies in [1, n-1],
  and the PKCS#1 v1.5 encoding is compared byte for byte with the one
  expected, which has at least eight bytes of padding;
- the pinned key is the RSA key that actually signs, primary or subkey,
  named by its own fingerprint, of at least 2048 bits, with an odd
  exponent of at least 3. A subkey's binding to its primary is not
  checked: pinning the subkey's own fingerprint is the trust decision.

Anything else fails closed with SignatureError. Nothing secret is
involved; verification uses public values only.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import time
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

from .errors import ManagerError

RSA_ALGORITHMS = (1, 3)                 # RSA (encrypt or sign), RSA sign-only
HASHES = {8: ("sha256", bytes.fromhex("3031300d060960864801650304020105000420")),
          9: ("sha384", bytes.fromhex("3041300d060960864801650304020205000430")),
          10: ("sha512", bytes.fromhex("3051300d060960864801650304020305000440"))}
TAG_SIGNATURE, TAG_PUBLIC_KEY = 2, 6
KEY_PACKETS = (6, 14)                   # public key, public subkey
SUB_CREATED, SUB_EXPIRES, SUB_ISSUER, SUB_ISSUER_FPR = 2, 3, 16, 33
# Subpackets understood well enough that a critical one may be accepted.
KNOWN_SUBPACKETS = {SUB_CREATED, SUB_EXPIRES, SUB_ISSUER, SUB_ISSUER_FPR}
MIN_RSA_BITS = 2048
MIN_PADDING = 8
CLOCK_SKEW = 24 * 3600


class SignatureError(ManagerError):
    """The signature does not verify, or cannot be checked."""


def crc24(data: bytes) -> int:
    crc = 0xB704CE
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= 0x1864CFB
    return crc & 0xFFFFFF


def dearmor(text: str, kind: str) -> bytes:
    """The binary packets inside one ASCII-armored block of the given
    kind, such as SIGNATURE, with strict base64 and checksum."""
    if not isinstance(text, str):
        raise SignatureError("armored input must be text")
    if not text.isascii():
        raise SignatureError("armored input is not ASCII")
    lines = [ln.strip() for ln in text.strip().splitlines()]
    begin, end = f"-----BEGIN PGP {kind}-----", f"-----END PGP {kind}-----"
    if lines.count(begin) != 1 or lines.count(end) != 1:
        raise SignatureError(f"expected exactly one armored PGP {kind}")
    start, stop = lines.index(begin), lines.index(end)
    if stop < start:
        raise SignatureError("armor ends before it begins")
    body = lines[start + 1: stop]
    while body and body[0] and ":" in body[0]:          # armor headers
        body.pop(0)
    if body and body[0] == "":
        body.pop(0)
    checksum = None
    if body and body[-1].startswith("="):
        checksum = body.pop()[1:]
    try:
        data = base64.b64decode("".join(body), validate=True)
        expected = (int.from_bytes(base64.b64decode(checksum, validate=True),
                                   "big") if checksum is not None else None)
    except (binascii.Error, ValueError):
        raise SignatureError("armor is not valid base64") from None
    if not data:
        raise SignatureError("armor holds no data")
    if checksum is not None and (len(checksum) != 4 or crc24(data) != expected):
        raise SignatureError("armor checksum does not match")
    return data


class Reader:
    """Bounds-checked reads from a byte string."""

    def __init__(self, data: bytes):
        self.data, self.pos = data, 0

    def take(self, count: int) -> bytes:
        if count < 0 or self.pos + count > len(self.data):
            raise SignatureError("truncated data")
        chunk = self.data[self.pos: self.pos + count]
        self.pos += count
        return chunk

    def byte(self) -> int:
        return self.take(1)[0]

    def number(self, size: int) -> int:
        return int.from_bytes(self.take(size), "big")

    def done(self) -> bool:
        return self.pos == len(self.data)

    def mpi(self) -> int:
        bits = self.number(2)
        value = int.from_bytes(self.take((bits + 7) // 8), "big")
        if value.bit_length() != bits or value == 0:
            raise SignatureError("non-canonical MPI")
        return value


def packets(data: bytes) -> Iterator[Tuple[int, bytes]]:
    """(tag, body) for each packet, in old or new format. Partial and
    indeterminate lengths, empty bodies and reserved tag 0 are refused."""
    reader = Reader(data)
    while not reader.done():
        header = reader.byte()
        if not header & 0x80:
            raise SignatureError("malformed packet header")
        if header & 0x40:                                   # new format
            tag = header & 0x3F
            first = reader.byte()
            if first < 192:
                length = first
            elif first < 224:
                length = ((first - 192) << 8) + reader.byte() + 192
            elif first == 255:
                length = reader.number(4)
            else:
                raise SignatureError("partial packet lengths are not supported")
        else:                                               # old format
            tag = (header >> 2) & 0x0F
            kind = header & 0x03
            if kind == 3:
                raise SignatureError("indeterminate packet lengths are not "
                                     "supported")
            length = reader.number((1, 2, 4)[kind])
        if tag == 0:
            raise SignatureError("reserved packet tag 0")
        body = reader.take(length)
        if not body:
            raise SignatureError("empty packet")
        yield tag, body


@dataclass
class PublicKey:
    fingerprint: str
    primary: bool
    algorithm: int
    n: int
    e: int


def read_key(tag: int, body: bytes) -> Optional[PublicKey]:
    """An RSA v4 public key or subkey, or None for other kinds of key."""
    if len(body) > 0xFFFF:
        raise SignatureError("key packet too large")
    reader = Reader(body)
    version = reader.byte()
    reader.take(4)                                          # creation time
    algorithm = reader.byte()
    if version != 4 or algorithm not in RSA_ALGORITHMS:
        return None
    n, e = reader.mpi(), reader.mpi()
    if not reader.done():
        raise SignatureError("unexpected data after the RSA key")
    material = b"\x99" + len(body).to_bytes(2, "big") + body
    # The v4 fingerprint is defined as SHA-1 over the key packet.
    fingerprint = hashlib.sha1(material).hexdigest().upper()  # nosec
    return PublicKey(fingerprint, tag == TAG_PUBLIC_KEY, algorithm, n, e)


def keys(armored: str) -> List[PublicKey]:
    return [key for tag, body in packets(dearmor(armored, "PUBLIC KEY BLOCK"))
            if tag in KEY_PACKETS
            for key in [read_key(tag, body)] if key is not None]


@dataclass
class Signature:
    sig_type: int
    algorithm: int
    hash_algorithm: int
    hashed: bytes                       # version through the hashed subpackets
    hashed_subpackets: List[Tuple[int, bool, bytes]]
    unhashed_subpackets: List[Tuple[int, bool, bytes]]
    left16: bytes
    value: int


def subpackets(data: bytes) -> List[Tuple[int, bool, bytes]]:
    """(type, critical, body) for each subpacket in an area."""
    reader = Reader(data)
    found = []
    while not reader.done():
        first = reader.byte()
        if first < 192:
            length = first
        elif first < 255:
            length = ((first - 192) << 8) + reader.byte() + 192
        else:
            length = reader.number(4)
        if length == 0:
            raise SignatureError("empty subpacket")
        content = reader.take(length)
        found.append((content[0] & 0x7F, bool(content[0] & 0x80), content[1:]))
    return found


def read_signature(armored: str) -> Signature:
    found = list(packets(dearmor(armored, "SIGNATURE")))
    if len(found) != 1 or found[0][0] != TAG_SIGNATURE:
        raise SignatureError("expected exactly one signature packet and "
                             "nothing else")
    reader = Reader(found[0][1])
    version = reader.byte()
    if version != 4:
        raise SignatureError(f"signature version {version} is not supported")
    sig_type, algorithm, hash_algorithm = reader.byte(), reader.byte(), reader.byte()
    hashed_area = reader.take(reader.number(2))
    hashed = found[0][1][: reader.pos]
    unhashed_area = reader.take(reader.number(2))
    left16 = reader.take(2)
    value = reader.mpi()
    if not reader.done():
        raise SignatureError("unexpected data after the signature value")
    return Signature(sig_type, algorithm, hash_algorithm, hashed,
                     subpackets(hashed_area), subpackets(unhashed_area),
                     left16, value)


def check_subpackets(sig: Signature, fingerprint: str, now: float) -> None:
    hashed_fprs = []
    created = expires = None
    for kind, critical, body in sig.hashed_subpackets:
        if critical and kind not in KNOWN_SUBPACKETS:
            raise SignatureError(f"unknown critical subpacket {kind}")
        if kind == SUB_ISSUER_FPR:
            hashed_fprs.append(body)
        elif kind == SUB_CREATED:
            if len(body) != 4:
                raise SignatureError("malformed creation time")
            created = int.from_bytes(body, "big")
        elif kind == SUB_EXPIRES:
            if len(body) != 4:
                raise SignatureError("malformed expiration time")
            expires = int.from_bytes(body, "big")
    if created is None:
        raise SignatureError("the signature has no hashed creation time")
    if created > now + CLOCK_SKEW:
        raise SignatureError("the signature was made in the future")
    if expires and created + expires < now:
        raise SignatureError("the signature has expired")
    want = b"\x04" + bytes.fromhex(fingerprint)
    if not hashed_fprs:
        raise SignatureError("the signature does not name its issuer's "
                             "fingerprint in its hashed area")
    for kind, _, _ in sig.unhashed_subpackets:
        if kind not in (SUB_ISSUER, SUB_ISSUER_FPR):
            raise SignatureError(f"unexpected subpacket {kind} in the "
                                 f"unhashed area, which nothing signs")
    for area in (sig.hashed_subpackets, sig.unhashed_subpackets):
        for kind, _, body in area:
            if kind == SUB_ISSUER_FPR and body != want:
                raise SignatureError(f"the signature names issuer "
                                     f"{body.hex().upper()}, not the pinned "
                                     f"key {fingerprint}")
            if kind == SUB_ISSUER and body.hex().upper() != fingerprint[-16:]:
                raise SignatureError(f"the signature names issuer key ID "
                                     f"{body.hex().upper()}, not the pinned "
                                     f"key {fingerprint[-16:]}")


def verify(data: bytes, signature_armored: str, key_armored: str,
           fingerprint: str, now: Optional[float] = None) -> str:
    """Verify a detached signature over data with the pinned key.
    Return the fingerprint that signed, or raise SignatureError."""
    try:
        return _verify(data, signature_armored, key_armored, fingerprint,
                       time.time() if now is None else now)
    except SignatureError:
        raise
    except (IndexError, ValueError, TypeError, OverflowError,
            binascii.Error, UnicodeError) as exc:
        # Every read is bounds-checked; this is the last line of defence.
        raise SignatureError(f"malformed input: {exc}") from None


def _verify(data, signature_armored, key_armored, fingerprint, now):
    if not isinstance(data, bytes):
        raise SignatureError("the signed data must be bytes")
    fingerprint = fingerprint.replace(" ", "").upper()
    if len(fingerprint) != 40:
        raise SignatureError("the pinned fingerprint is not 40 hex digits")
    candidates = [k for k in keys(key_armored) if k.fingerprint == fingerprint]
    if not candidates:
        raise SignatureError(f"the pinned key {fingerprint} is not in the "
                             f"key block")
    key = candidates[0]
    if key.n.bit_length() < MIN_RSA_BITS or key.e < 3 or key.e % 2 == 0:
        raise SignatureError("the pinned key is not a sound RSA key")
    sig = read_signature(signature_armored)
    if sig.algorithm != key.algorithm:
        raise SignatureError("the signature's algorithm is not the key's")
    if sig.hash_algorithm not in HASHES:
        raise SignatureError(f"hash algorithm {sig.hash_algorithm} is not "
                             f"accepted; SHA-256 or stronger only")
    if sig.sig_type not in (0x00, 0x01):
        raise SignatureError(f"signature type {sig.sig_type:#x} is not a "
                             f"document signature")
    check_subpackets(sig, fingerprint, now)
    if sig.sig_type == 0x01:
        data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    name, prefix = HASHES[sig.hash_algorithm]
    trailer = b"\x04\xff" + len(sig.hashed).to_bytes(4, "big")
    digest = hashlib.new(name, data + sig.hashed + trailer).digest()
    if digest[:2] != sig.left16:
        raise SignatureError("signature does not match the data")
    if not 0 < sig.value < key.n:
        raise SignatureError("signature value out of range")
    size = (key.n.bit_length() + 7) // 8
    expected = prefix + digest
    padding_length = size - len(expected) - 3
    if padding_length < MIN_PADDING:
        raise SignatureError("the key is too small for this hash")
    encoded = b"\x00\x01" + b"\xff" * padding_length + b"\x00" + expected
    if pow(sig.value, key.e, key.n).to_bytes(size, "big") != encoded:
        raise SignatureError("signature does not match the data")
    return fingerprint
