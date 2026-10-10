"""Shared scaffolding: the checkout's lib/ on the import path, the signed
fake releases, and a sandboxed manager that never touches the real home
directory or the network."""

from __future__ import annotations

import copy
import io
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
if str(REPO / "lib") not in sys.path:
    sys.path.insert(0, str(REPO / "lib"))

from osat_manager_restic.errors import ManagerError  # noqa: E402
from osat_manager_restic.manager import Manager  # noqa: E402
from osat_manager_restic.manifest import load_manifest  # noqa: E402
from osat_manager_restic.net import NotPublished  # noqa: E402
from osat_manager_restic.platforms import Paths  # noqa: E402

FAKE = "fake://"


def zip_member(name: str, member: str) -> bytes:
    with zipfile.ZipFile(DATA / name) as z:
        return z.read(member)


def test_manifest() -> dict:
    """manager.yaml, pinned to the test signing key and pointed at the
    fake releases."""
    manifest = copy.deepcopy(load_manifest(REPO / "manager.yaml"))
    key = manifest["verification"]["signing_key"]
    key["public_key"] = (DATA / "test-signing-key.asc").read_text()
    key["fingerprint"] = (DATA / "test-signing-key.fingerprint").read_text().strip()
    manifest["sources"]["release_url"] = FAKE + "v{version}/{file}"
    manifest["sources"]["latest_release_api"] = FAKE + "latest"
    return manifest


class FakeNetwork:
    """Serves the signed fake releases; counts requests; can be switched
    off to prove offline behaviour, or made to tamper with an asset."""

    def __init__(self):
        self.requests = []
        self.online = True
        self.tamper = None

    def fetch(self, url: str, max_bytes: int = 0) -> bytes:
        self.requests.append(url)
        if not self.online:
            raise ManagerError(f"network is off: {url}")
        member = url[len(FAKE):]
        try:
            data = zip_member("fake-releases.zip", member)
        except KeyError:
            raise NotPublished(f"not published upstream: {url}") from None
        if self.tamper and member.endswith(self.tamper):
            data = data + b"tampered"
        return data

    def latest_version(self, api_url: str) -> str:
        self.fetch(FAKE + "v0.19.1/SHA256SUMS")
        return "0.19.1"


def fake_runner(argv):
    """Stands in for running the binary: the test doubles are scripts that
    echo their version, so the version is read from the file."""
    text = Path(argv[0]).read_bytes().decode("utf-8")
    match = re.search(r'echo "(.*)"', text)
    return match.group(1) + "\n"


class Sandbox(unittest.TestCase):
    system, arch = "linux", "amd64"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.paths = Paths(self.tmp / "root", self.tmp / "bin",
                           self.system == "windows")
        self.net = FakeNetwork()
        self.messages = []
        self.manager = self.make_manager()

    def tearDown(self):
        from osat_manager_restic.platforms import unprotect
        unprotect(self.tmp)
        self._tmp.cleanup()

    def make_manager(self, manifest=None, runner=fake_runner):
        return Manager(manifest or test_manifest(), self.paths, self.system,
                       self.arch, self.net, runner, self.messages.append)
