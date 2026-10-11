# Changelog

All notable changes are recorded here, in the form of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This repository follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-10

### Added

- `manage-restic`, meeting the OSAT manager contract: user-space install, versions side by side, switching, a generic `restic` alias beside one per minor line, renamable aliases, read-only installed versions, a verified archive for offline restore, self-install and uninstall.
- Two-step verification of every download: the OpenPGP signature on `SHA256SUMS` against restic's pinned key, verified with the standard library, then the SHA-256 of the download.
- `manager.yaml`, describing restic's releases, verification, platforms and locations.
- Unit tests against signed fake releases, and the end-to-end scenario with its Linux driver.
- Licensed MIT for code and CC BY 4.0 for documentation (uc-automa 0025).
