"""Crafting OpenPGP keys and signatures by hand, for test vectors.

Signs with the throwaway RSA keys in data/crafted-test-keys.json, so a
test can produce a signature with any hash, issuer, subpackets or
tampering it needs, and check the verifier's answer against gpg's.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from support import DATA

from osat_manager_restic.openpgp import crc24

CREATED = 1791590400                     # 2026-10-09T00:00:00Z
HASH_NAMES = {1: "md5", 2: "sha1", 8: "sha256", 9: "sha384", 10: "sha512",
              11: "sha224"}
PREFIXES = {
    1: bytes.fromhex("3020300c06082a864886f70d020505000410"),
    2: bytes.fromhex("3021300906052b0e03021a05000414"),
    8: bytes.fromhex("3031300d060960864801650304020105000420"),
    9: bytes.fromhex("3041300d060960864801650304020205000430"),
    10: bytes.fromhex("3051300d060960864801650304020305000440"),
    11: bytes.fromhex("302d300d06096086480165030402040500041c"),
}


@dataclass
class Key:
    n: int
    e: int
    d: int

    @property
    def body(self) -> bytes:
        return b"\x04" + CREATED.to_bytes(4, "big") + b"\x01" + mpi(self.n) + mpi(self.e)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha1(b"\x99" + len(self.body).to_bytes(2, "big")
                            + self.body).hexdigest().upper()

    @property
    def fpr_bytes(self) -> bytes:
        return bytes.fromhex(self.fingerprint)


def load_key(name: str) -> Key:
    data = json.loads((DATA / "crafted-test-keys.json").read_text())[name]
    return Key(int(data["n"], 16), data["e"], int(data["d"], 16))


def mpi(value: int) -> bytes:
    return value.bit_length().to_bytes(2, "big") + \
        value.to_bytes((value.bit_length() + 7) // 8, "big")


def packet(tag: int, body: bytes) -> bytes:
    n = len(body)
    if n < 192:
        length = bytes([n])
    elif n < 8384:
        length = bytes([((n - 192) >> 8) + 192, (n - 192) & 0xFF])
    else:
        length = b"\xff" + n.to_bytes(4, "big")
    return bytes([0xC0 | tag]) + length + body


def sub(kind: int, data: bytes, critical: bool = False) -> bytes:
    content = bytes([kind | (0x80 if critical else 0)]) + data
    return bytes([len(content)]) + content


def created(at: int = CREATED) -> bytes:
    return sub(2, at.to_bytes(4, "big"))


def issuer_fpr(key: Key, version: int = 4) -> bytes:
    return sub(33, bytes([version]) + key.fpr_bytes)


def issuer_id(key: Key) -> bytes:
    return sub(16, key.fpr_bytes[-8:])


@dataclass
class Spec:
    """What to sign and how; the defaults make a valid signature."""
    signer: Key
    hash_alg: int = 8
    sig_type: int = 0
    hashed: Optional[bytes] = None
    unhashed: Optional[bytes] = None
    prefix: Optional[bytes] = None
    encode: Optional[object] = None          # callable(k, t) -> encoded block
    value: Optional[object] = None           # callable(s, n) -> new s
    left16: Optional[bytes] = None
    extra: List[bytes] = field(default_factory=list)


def signature_body(data: bytes, spec: Spec, prefix_material: bytes = b"",
                   sig_type: Optional[int] = None) -> bytes:
    key = spec.signer
    hashed_sub = spec.hashed if spec.hashed is not None else \
        created() + issuer_fpr(key)
    unhashed_sub = spec.unhashed if spec.unhashed is not None else issuer_id(key)
    kind = spec.sig_type if sig_type is None else sig_type
    hashed = bytes([4, kind, 1, spec.hash_alg]) + \
        len(hashed_sub).to_bytes(2, "big") + hashed_sub
    trailer = b"\x04\xff" + len(hashed).to_bytes(4, "big")
    digest = hashlib.new(HASH_NAMES[spec.hash_alg],
                         prefix_material + data + hashed + trailer).digest()
    k = (key.n.bit_length() + 7) // 8
    t = (spec.prefix if spec.prefix is not None else PREFIXES[spec.hash_alg]) + digest
    encoded = spec.encode(k, t) if spec.encode else \
        b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    s = pow(int.from_bytes(encoded, "big"), key.d, key.n)
    if spec.value:
        s = spec.value(s, key.n)
    return hashed + len(unhashed_sub).to_bytes(2, "big") + unhashed_sub + \
        (spec.left16 if spec.left16 is not None else digest[:2]) + mpi(s)


def armor(data: bytes, kind: str = "SIGNATURE") -> str:
    text = base64.b64encode(data).decode()
    lines = [text[i: i + 64] for i in range(0, len(text), 64)]
    check = base64.b64encode(crc24(data).to_bytes(3, "big")).decode()
    return "\n".join([f"-----BEGIN PGP {kind}-----", "", *lines, f"={check}",
                      f"-----END PGP {kind}-----", ""])


def sign(data: bytes, spec: Spec) -> str:
    return armor(packet(2, signature_body(data, spec)) + b"".join(spec.extra))


def key_block(key: Key, subkey: Optional[Key] = None,
              uid: bytes = b"crafted test key <tests@invalid>") -> str:
    """A primary key with a user ID certified by itself, so gpg can import
    it, and optionally a subkey (left unbound)."""
    key_material = b"\x99" + len(key.body).to_bytes(2, "big") + key.body
    uid_material = b"\xb4" + len(uid).to_bytes(4, "big") + uid
    cert = signature_body(b"", Spec(key, hash_alg=10),
                          prefix_material=key_material + uid_material,
                          sig_type=0x13)
    blocks = packet(6, key.body) + packet(13, uid) + packet(2, cert)
    if subkey is not None:
        blocks += packet(14, subkey.body)
    return armor(blocks, "PUBLIC KEY BLOCK")
