"""The manager contract, offline, against signed fake releases in a
sandbox: user-space install, versions side by side, switching, aliases,
renaming, protection, the verified archive, self-install and uninstall."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

from support import REPO, ManagerError, Sandbox, test_manifest

from osat_manager_restic.manifest import load_manifest

POSIX = os.name != "nt"
ROOT = POSIX and os.geteuid() == 0


class Install(Sandbox):

    def test_latest_is_installed_and_active(self):
        self.assertEqual(self.manager.install(), "0.19.1")
        self.assertEqual(self.manager.read_state()["active"], "0.19.1")
        self.assertTrue(self.paths.binary("0.19.1").is_file())
        self.assertIn("now active", self.messages[-1])

    def test_two_versions_side_by_side_and_switching(self):
        self.manager.install("0.18.1")
        self.manager.install("0.19.1")
        self.assertEqual(self.manager.installed(), ["0.18.1", "0.19.1"])
        self.manager.switch("0.18.1")
        state = self.manager.read_state()
        self.assertEqual(state["active"], "0.18.1")
        self.assertIn(str(self.paths.binary("0.18.1")),
                      self.paths.launcher("restic").read_text())
        self.assertIn(str(self.paths.binary("0.19.1")),
                      self.paths.launcher("restic-0.19").read_text())

    def test_provenance_records_the_verification(self):
        self.manager.install("0.19.1")
        text = (self.paths.versions / "0.19.1" / "provenance.json").read_text()
        self.assertIn('"signed_by": "', text)
        self.assertIn("restic_0.19.1_linux_amd64.bz2", text)

    def test_a_version_never_published_says_so(self):
        with self.assertRaises(ManagerError) as caught:
            self.manager.install("0.99.0")
        self.assertIn("never published", str(caught.exception))

    def test_a_tampered_download_is_refused_and_nothing_is_kept(self):
        self.net.tamper = ".bz2"
        with self.assertRaises(ManagerError) as caught:
            self.manager.install("0.19.1")
        self.assertIn("does not match the signed", str(caught.exception))
        self.assertEqual(self.manager.installed(), [])
        self.assertEqual(self.manager.archived(), [])

    def test_a_signature_from_another_key_is_refused(self):
        manifest = test_manifest()
        manifest["verification"]["signing_key"] = \
            load_manifest(REPO / "manager.yaml")["verification"]["signing_key"]
        manager = self.make_manager(manifest)
        with self.assertRaises(ManagerError):
            manager.install("0.19.1")
        self.assertEqual(manager.installed(), [])

    def test_a_binary_reporting_another_version_is_not_installed(self):
        manager = self.make_manager(runner=lambda argv: "restic 0.1.0\n")
        with self.assertRaises(ManagerError) as caught:
            manager.install("0.19.1")
        self.assertIn("not installed", str(caught.exception))
        self.assertEqual(manager.installed(), [])


class Archive(Sandbox):

    def test_restore_from_the_archive_with_the_network_off(self):
        self.manager.install("0.18.1")
        self.manager.install("0.19.1")
        self.manager.remove("0.18.1")
        self.assertEqual(self.manager.installed(), ["0.19.1"])
        self.assertIn("0.18.1", self.manager.archived())
        self.net.online = False
        before = len(self.net.requests)
        self.manager.install("0.18.1")
        self.assertEqual(len(self.net.requests), before,
                         "no network request was made")
        self.assertIn("0.18.1", self.manager.installed())
        self.assertTrue(any("re-checked" in m for m in self.messages))

    def restore_with_no_network(self, resolver_error):
        """Restore from the archive with the real network class, while
        name resolution and connections are patched to record each call
        and raise. Returns the recorded calls."""
        import socket
        from unittest import mock
        from osat_manager_restic.net import Network
        self.manager.install("0.18.1")
        self.manager.install("0.19.1")
        self.manager.remove("0.18.1")
        calls = []

        def getaddrinfo(*args, **kwargs):
            calls.append(("getaddrinfo", args))
            raise resolver_error

        def create_connection(*args, **kwargs):
            calls.append(("create_connection", args))
            raise OSError("no network in this test")

        real_network = self.make_manager()
        real_network.net = Network(timeout=2)
        # restic's real HTTPS URLs, so any attempt would reach the sockets.
        real_network.manifest["sources"] = \
            load_manifest(REPO / "manager.yaml")["sources"]
        with mock.patch.object(socket, "getaddrinfo", getaddrinfo), \
                mock.patch.object(socket, "create_connection", create_connection):
            real_network.install("0.18.1")
        self.assertIn("0.18.1", real_network.installed())
        return calls

    def test_an_offline_restore_makes_no_network_attempt(self):
        calls = self.restore_with_no_network(OSError("refused in this test"))
        self.assertEqual(calls, [], "the restore tried the network")

    def test_an_offline_restore_works_when_names_do_not_resolve(self):
        import socket
        calls = self.restore_with_no_network(
            socket.gaierror(socket.EAI_NONAME, "Name or service not known"))
        self.assertEqual(calls, [], "the restore tried the network")

    def test_the_patches_do_catch_a_network_attempt(self):
        """The control: with nothing archived, the same patches see the
        download attempt, so the two tests above can fail."""
        import socket
        from unittest import mock
        from osat_manager_restic.net import Network
        calls = []

        def getaddrinfo(*args, **kwargs):
            calls.append(("getaddrinfo", args))
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

        manager = self.make_manager()
        manager.net = Network(timeout=2)
        manager.manifest["sources"] = load_manifest(REPO / "manager.yaml")["sources"]
        with mock.patch.object(socket, "getaddrinfo", getaddrinfo), \
                mock.patch("osat_manager_restic.net.time.sleep"):
            with self.assertRaises(ManagerError):
                manager.install("0.18.1")
        self.assertTrue(calls, "a download attempt went unnoticed")

    def test_a_tampered_archive_is_refused(self):
        from osat_manager_restic.platforms import unprotect
        self.manager.install("0.18.1")
        self.manager.install("0.19.1")
        self.manager.remove("0.18.1")
        asset = self.paths.archive / "0.18.1" / "restic_0.18.1_linux_amd64.bz2"
        unprotect(asset.parent)
        asset.write_bytes(asset.read_bytes() + b"x")
        self.net.online = False
        with self.assertRaises(ManagerError):
            self.manager.install("0.18.1")

    def test_the_active_version_cannot_be_removed(self):
        self.manager.install("0.19.1")
        with self.assertRaises(ManagerError):
            self.manager.remove("0.19.1")


class Aliases(Sandbox):

    def test_rename_an_alias(self):
        self.manager.install("0.19.1")
        self.manager.rename_alias("restic-0.19=r19")
        self.assertFalse(self.paths.launcher("restic-0.19").exists())
        self.assertTrue(self.paths.launcher("r19").is_file())
        self.assertTrue(self.paths.launcher("restic").is_file())
        self.manager.install("0.18.1")
        self.assertTrue(self.paths.launcher("r19").is_file(),
                        "a renamed alias keeps its name across switches")

    def test_a_launcher_not_written_by_the_manager_is_left_alone(self):
        self.paths.bin_dir.mkdir(parents=True)
        self.paths.launcher("restic").write_text("#!/bin/sh\necho mine\n")
        with self.assertRaises(ManagerError):
            self.manager.install("0.19.1")
        self.assertIn("mine", self.paths.launcher("restic").read_text())

    @unittest.skipUnless(POSIX, "runs the launcher with /bin/sh")
    def test_both_alias_forms_resolve(self):
        self.manager.install("0.18.1")
        self.manager.install("0.19.1")
        self.manager.rename_alias("restic-0.18=r18")
        for name, version in (("restic", "0.19.1"), ("r18", "0.18.1")):
            out = subprocess.run([str(self.paths.launcher(name)), "version"],
                                 capture_output=True, text=True).stdout
            self.assertIn(f"restic {version}", out)


class Protection(Sandbox):

    @unittest.skipIf(ROOT, "root ignores file permissions")
    def test_an_installed_version_cannot_be_modified(self):
        self.manager.install("0.19.1")
        binary = self.paths.binary("0.19.1")
        with self.assertRaises(PermissionError):
            with binary.open("ab") as f:
                f.write(b"x")
        if POSIX:
            with self.assertRaises(PermissionError):
                (binary.parent / "extra").write_text("x")


class SelfInstallAndUninstall(Sandbox):

    def test_uninstall_leaves_nothing_behind(self):
        self.manager.install("0.18.1")
        self.manager.install("0.19.1")
        self.manager.self_install(REPO / "manager.yaml")
        (self.paths.bin_dir / "someone-elses-tool").write_text("x\n")
        self.manager.uninstall()
        self.assertFalse(self.paths.root.exists())
        self.assertEqual([p.name for p in self.paths.bin_dir.iterdir()],
                         ["someone-elses-tool"])

    def test_a_created_directory_holding_anything_else_is_kept(self):
        self.manager.install("0.19.1")
        (self.paths.bin_dir / "someone-elses-tool").write_text("x\n")
        self.manager.uninstall()
        self.assertTrue((self.paths.bin_dir / "someone-elses-tool").is_file())
        self.assertFalse(self.paths.root.exists())

    def test_a_directory_that_existed_before_is_kept_even_if_empty(self):
        self.paths.bin_dir.mkdir(parents=True)
        self.manager.install("0.19.1")
        self.manager.uninstall()
        self.assertTrue(self.paths.bin_dir.is_dir())

    def test_directories_the_manager_created_are_removed_when_empty(self):
        self.manager.install("0.19.1")
        self.manager.uninstall()
        self.assertFalse(self.paths.bin_dir.exists())
        self.assertEqual(list(self.tmp.iterdir()), [])

    @unittest.skipUnless(POSIX, "runs the launcher with /bin/sh")
    def test_the_self_installed_manager_runs_from_anywhere(self):
        self.manager.self_install(REPO / "manager.yaml")
        out = subprocess.run([str(self.paths.launcher("manage-restic")),
                              "--version"], cwd=str(self.tmp),
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("manage-restic", out.stdout)


class Windows(Sandbox):
    system = "windows"

    def test_zip_assets_and_cmd_launchers(self):
        self.manager.install("0.19.1")
        self.assertTrue(self.paths.binary("0.19.1").name.endswith(".exe"))
        launcher = self.paths.launcher("restic")
        self.assertEqual(launcher.suffix, ".cmd")
        text = launcher.read_bytes()
        self.assertIn(b"\r\n", text)
        self.assertIn(b"%*", text)


if __name__ == "__main__":
    unittest.main()
