# Changelog

All notable changes are recorded here, in the form of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This repository follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- On Windows, `manage-restic --uninstall` deleted its own launcher while `cmd.exe` was still reading it, so after uninstalling it printed "The system cannot find the path specified." and exited 1. Each Windows launcher now ends the batch file on the line that runs its command, and passes the command's exit code back.

### Changed

- The manager's launcher sets no variables: `--self-install` writes a `__main__.py` into the manager's directory, and the launcher runs that directory.
- The manager writes no bytecode cache, so a Python installed in the user's own account, as manage-python installs it, is left as it was.

### Added

- `tests/e2e/windows/run_over_ssh.py`, which runs the unit tests of uc-portage, uc-automa and this repository, the network cut's self-test and the end-to-end scenario in a Windows virtual machine reached over SSH, each from a clean snapshot, and installs uc-portage and uc-automa there with `pip install --no-index`, inside a network cut, from wheels built from their release tags and PyYAML's pure `py3-none-any` wheel.
- The network cut's self-test reaches its instance through a guest, so the same test runs in a Linux container with `incus exec` and in a Windows virtual machine over SSH.

## [0.1.0] - 2026-10-11

### Added

- `manage-restic`, meeting the OSAT manager contract: user-space install, versions side by side, switching, a generic `restic` alias beside one per minor line, renamable aliases, read-only installed versions, a verified archive for offline restore, self-install and uninstall.
- Two-step verification of every download: the OpenPGP signature on `SHA256SUMS` against restic's pinned key, verified with the standard library, then the SHA-256 of the download.
- `manager.yaml`, describing restic's releases, verification, platforms and locations.
- Unit tests against signed fake releases, and the end-to-end scenario with its Linux driver.
- Licensed MIT for code and CC BY 4.0 for documentation (uc-automa 0025).
