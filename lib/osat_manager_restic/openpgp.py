"""Verifying an OpenPGP detached signature with the standard library.

restic signs each release's SHA256SUMS with an RSA key and publishes the
signature as SHA256SUMS.asc. This module checks such a signature against
one pinned public key (RFC 4880): it reads the armored key and
signature, confirms the key's v4 fingerprint is the pinned one and that
the signature names it as issuer, hashes the data with the signature's
hashed subpackets, and checks the RSA PKCS#1 v1.5 signature.

It verifies only what it needs to: version 4 packets, RSA keys, binary
or text signatures, and the SHA-2 hashes. Anything else is refused.
Nothing secret is involved; verification uses public values only.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

from .errors import ManagerError

RSA_ALGORITHMS = (1, 3)                 # RSA (encrypt or sign), RSA sign-only
HASHES = {8: ("sha256", bytes.fromhex("3031300d060960864801650304020105000420")),
          9: ("sha384", bytes.fromhex("3041300d060960864801650304020205000430")),
          10: ("sha512", bytes.fromhex("3051300d060960864801650304020305000440")),
          11: ("sha224", bytes.fromhex("302d300d06096086480165030402040500041c"))}
TAG_SIGNATURE, TAG_PUBLIC_KEY, TAG_PUBLIC_SUBKEY = 2, 6, 14
SUBPACKET_ISSUER, SUBPACKET_ISSUER_FPR = 16, 33


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


def dearmor(text: str) -> bytes:
    """The binary packets inside one ASCII-armored block, checksum checked."""
    lines = [ln.strip() for ln in text.strip().splitlines()]
    try:
        start = next(i for i, ln in enumerate(lines)
                     if ln.startswith("-----BEGIN PGP "))
        end = next(i for i, ln in enumerate(lines)
                   if i > start and ln.startswith("-----END PGP "))
    except StopIteration:
        raise SignatureError("not an ASCII-armored OpenPGP block") from None
    body = lines[start + 1: end]
    while body and body[0] and ":" in body[0]:          # armor headers
        body.pop(0)
    if body and body[0] == "":
        body.pop(0)
    checksum = None
    if body and body[-1].startswith("="):
        checksum = body.pop()[1:]
    data = base64.b64decode("".join(body))
    if checksum is not None:
        expected = int.from_bytes(base64.b64decode(checksum), "big")
        if crc24(data) != expected:
            raise SignatureError("armor checksum does not match")
    return data


def packets(data: bytes) -> Iterator[Tuple[int, bytes]]:
    """(tag, body) for each packet, in old or new format."""
    i = 0
    while i < len(data):
        header = data[i]
        if not header & 0x80:
            raise SignatureError("malformed packet header")
        if header & 0x40:                                   # new format
            tag = header & 0x3F
            first = data[i + 1]
            if first < 192:
                length, i = first, i + 2
            elif first < 224:
                length, i = ((first - 192) << 8) + data[i + 2] + 192, i + 3
            elif first == 255:
                length, i = int.from_bytes(data[i + 2: i + 6], "big"), i + 6
            else:
                raise SignatureError("partial packet lengths are not supported")
        else:                                               # old format
            tag = (header >> 2) & 0x0F
            kind = header & 0x03
            if kind == 3:
                raise SignatureError("indeterminate packet lengths are not "
                                     "supported")
            size = (1, 2, 4)[kind]
            length = int.from_bytes(data[i + 1: i + 1 + size], "big")
            i += 1 + size
        body = data[i: i + length]
        if len(body) != length:
            raise SignatureError("truncated packet")
        yield tag, body
        i += length


def read_mpi(data: bytes, i: int) -> Tuple[int, int]:
    bits = int.from_bytes(data[i: i + 2], "big")
    size = (bits + 7) // 8
    return int.from_bytes(data[i + 2: i + 2 + size], "big"), i + 2 + size


@dataclass
class PublicKey:
    fingerprint: str
    n: int
    e: int


def read_key(body: bytes) -> Optional[PublicKey]:
    """An RSA v4 public key or subkey packet, or None for other kinds."""
    if body[0] != 4 or body[5] not in RSA_ALGORITHMS:
        return None
    n, i = read_mpi(body, 6)
    e, _ = read_mpi(body, i)
    material = b"\x99" + len(body).to_bytes(2, "big") + body
    fingerprint = hashlib.sha1(material).hexdigest().upper()  # nosec: the v4 fingerprint is defined as SHA-1
    return PublicKey(fingerprint, n, e)


def keys(armored: str) -> List[PublicKey]:
    found = []
    for tag, body in packets(dearmor(armored)):
        if tag in (TAG_PUBLIC_KEY, TAG_PUBLIC_SUBKEY):
            key = read_key(body)
            if key is not None:
                found.append(key)
    return found


@dataclass
class Signature:
    sig_type: int
    algorithm: int
    hash_algorithm: int
    hashed: bytes                 # version through the hashed subpackets
    left16: bytes
    value: int
    issuer_fingerprint: Optional[str]
    issuer_key_id: Optional[str]


def subpackets(data: bytes) -> Iterator[Tuple[int, bytes]]:
    i = 0
    while i < len(data):
        first = data[i]
        if first < 192:
            length, i = first, i + 1
        elif first < 255:
            length, i = ((first - 192) << 8) + data[i + 1] + 192, i + 2
        else:
            length, i = int.from_bytes(data[i + 1: i + 5], "big"), i + 5
        yield data[i] & 0x7F, data[i + 1: i + length]
        i += length


def read_signature(armored: str) -> Signature:
    sigs = [body for tag, body in packets(dearmor(armored))
            if tag == TAG_SIGNATURE]
    if len(sigs) != 1:
        raise SignatureError(f"expected one signature, found {len(sigs)}")
    body = sigs[0]
    if body[0] != 4:
        raise SignatureError(f"signature version {body[0]} is not supported")
    sig_type, algorithm, hash_algorithm = body[1], body[2], body[3]
    hashed_len = int.from_bytes(body[4:6], "big")
    hashed_end = 6 + hashed_len
    unhashed_len = int.from_bytes(body[hashed_end: hashed_end + 2], "big")
    unhashed_start = hashed_end + 2
    left16 = body[unhashed_start + unhashed_len: unhashed_start + unhashed_len + 2]
    value, _ = read_mpi(body, unhashed_start + unhashed_len + 2)
    issuer_fpr = issuer_id = None
    for area in (body[6:hashed_end],
                 body[unhashed_start: unhashed_start + unhashed_len]):
        for kind, data in subpackets(area):
            if kind == SUBPACKET_ISSUER_FPR and data[:1] == b"\x04":
                issuer_fpr = issuer_fpr or data[1:].hex().upper()
            elif kind == SUBPACKET_ISSUER:
                issuer_id = issuer_id or data.hex().upper()
    return Signature(sig_type, algorithm, hash_algorithm, body[:hashed_end],
                     left16, value, issuer_fpr, issuer_id)


def verify(data: bytes, signature_armored: str, key_armored: str,
           fingerprint: str) -> str:
    """Verify a detached signature over data with the pinned key. Return
    the fingerprint that signed, or raise SignatureError."""
    fingerprint = fingerprint.replace(" ", "").upper()
    candidates = [k for k in keys(key_armored) if k.fingerprint == fingerprint]
    if not candidates:
        raise SignatureError(f"the pinned key {fingerprint} is not in the "
                             f"key block")
    key = candidates[0]
    sig = read_signature(signature_armored)
    if sig.algorithm not in RSA_ALGORITHMS:
        raise SignatureError("only RSA signatures are supported")
    if sig.hash_algorithm not in HASHES:
        raise SignatureError(f"hash algorithm {sig.hash_algorithm} is not "
                             f"accepted")
    if sig.sig_type not in (0x00, 0x01):
        raise SignatureError(f"signature type {sig.sig_type:#x} is not a "
                             f"document signature")
    if sig.issuer_fingerprint not in (None, fingerprint) or (
            sig.issuer_key_id is not None
            and sig.issuer_key_id != fingerprint[-16:]):
        raise SignatureError(f"signed by {sig.issuer_fingerprint or sig.issuer_key_id}, "
                             f"not the pinned key {fingerprint}")
    if sig.sig_type == 0x01:
        data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    name, prefix = HASHES[sig.hash_algorithm]
    trailer = b"\x04\xff" + len(sig.hashed).to_bytes(4, "big")
    digest = hashlib.new(name, data + sig.hashed + trailer).digest()
    if digest[:2] != sig.left16:
        raise SignatureError("signature does not match the data")
    size = (key.n.bit_length() + 7) // 8
    expected = prefix + digest
    padding = b"\x00\x01" + b"\xff" * (size - len(expected) - 3) + b"\x00"
    recovered = pow(sig.value, key.e, key.n).to_bytes(size, "big")
    if recovered != padding + expected:
        raise SignatureError("signature does not match the data")
    return fingerprint
