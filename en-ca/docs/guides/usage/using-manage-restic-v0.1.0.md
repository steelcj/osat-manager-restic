---
title: "Using manage-restic"
dc:title: "Using manage-restic"
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 5.5 (Anthropic), AI assistance"
dc:subject: "manage-restic, restic, OSAT manager, usage"
dc:description: "Every manage-restic command, with what it does, how aliases, verification, offline restore and protection work, and where the manager keeps its files."
dc:date: "2026-10-09"
dc:type: "Text"
dc:format: "text/markdown"
dc:identifier: "urn:uuid:3008c6f3-b5b2-44a3-9b2d-936d0de5d35a"
dc:language: "en-CA"
dc:rights: "CC-BY-SA-4.0"
sat:version: "0.1.0"
sat:status: "Accepted"
---

# Using manage-restic

Version: 0.1.0
Status: Accepted

## Summary

`manage-restic` installs restic into your own account, keeps several versions side by side, switches between them, and keeps every verified download so a version can be restored without a network. It needs no administrator rights and no software beyond Python 3.8 or later.

## Install the manager

From a checkout of osat-manager-restic:

```sh
PYTHONPATH=lib python3 -m osat_manager_restic --self-install
```

This copies the manager into its install root and writes a `manage-restic` launcher in `~/.local/bin`, or `%LOCALAPPDATA%\osat\bin` on Windows. Make sure that directory is on your `PATH`.

## Commands

| Command | What it does |
| --- | --- |
| `manage-restic --install` | Install the latest restic release and make it active |
| `manage-restic --install 0.18.1` | Install a given version and make it active |
| `manage-restic --switch 0.19.1` | Make an installed version active |
| `manage-restic --status` | Show the active, installed and archived versions, and the aliases |
| `manage-restic --remove 0.18.1` | Remove an installed version that is not active; its verified archive is kept |
| `manage-restic --alias restic-0.18=r18` | Rename an alias |
| `manage-restic --self-install` | Install or refresh the manager itself |
| `manage-restic --uninstall` | Remove everything the manager owns, after asking; `--yes` skips the question |
| `manage-restic --version` | Show the manager's version |

## Aliases

| Alias | Runs |
| --- | --- |
| `restic` | The active version |
| `restic-0.19` | The active version if it is a 0.19 release, otherwise the newest installed 0.19 release |
| `manage-restic` | The manager itself |

There is one versioned alias for each installed minor line. Any alias can be renamed, and keeps its new name across later installs and switches. The manager writes and removes only launchers it wrote itself; a file of the same name that it did not write is left alone, and the command stops.

## Verification

Before anything is unpacked, the manager checks the signature on the release's `SHA256SUMS` against restic's signing key, pinned by fingerprint in `manager.yaml`, then checks the download's SHA-256 against that signed list. After unpacking, it runs the binary and requires it to report the requested version. A download that fails any check is not installed and not archived.

## Offline restore

Every verified download is kept in the archive with the checksum file and signature that verified it. Installing a version that is in the archive needs no network: the manager re-checks the signature and checksum and installs from the archive. Keep the archive in your backups; at a bare-metal restore it is how you get back the exact restic version that wrote your repository.

## Protection

Installed versions are read-only. Writing to or deleting an installed binary fails; only the manager's `--remove` and `--uninstall` take them away.

## The pinned key

`manager.yaml` pins restic's signing key by fingerprint, `CF8F 18F2 8445 7597 3F79 D4E1 91A6 868B D3F7 A907`, Alexander Neumann's RSA key, with the key itself. A signature from any other key is refused, even if the key is otherwise valid.

If restic starts signing with another key, or announces that the key has changed, installing new versions fails until `manager.yaml` is changed. The manager never fetches or trusts a new key by itself. The change is a reviewed commit to `manager.yaml`:

1. Read the announcement in restic's own channels, and the new fingerprint in restic's installation documentation.
2. Fetch the new key from the address restic names, and confirm its fingerprint matches the documented one.
3. Confirm that the new key verifies the newest release's `SHA256SUMS.asc`.
4. Pin the key that actually signs. If restic signs with a subkey, pin that subkey's own fingerprint.
5. Replace `public_key` and `fingerprint` in `manager.yaml`. In the commit message, name where the fingerprint was confirmed.
6. Have the change reviewed, then release a new version of the manager.

Versions already in the verified archive were checked with the key in force when they were downloaded. An offline restore re-checks them against the key now pinned, so after a rotation, keep the old key's releases restorable by restoring them before the change, or by keeping a manager release that still pins the old key.

## What it leaves alone

restic's own configuration, cache, repositories and password files. Do not run `restic self-update` on a managed binary; install the new version with the manager instead.

## Where things go

| | Linux | macOS | Windows |
| --- | --- | --- | --- |
| Install root | `~/.local/share/osat/restic` | `~/Library/Application Support/osat/restic` | `%LOCALAPPDATA%\osat\restic` |
| Launchers | `~/.local/bin` | `~/.local/bin` | `%LOCALAPPDATA%\osat\bin` |

`OSAT_RESTIC_HOME` and `OSAT_BIN_DIR` override them, for testing.

## Changelog

| Version | Date | Status | Notes |
| --- | --- | --- | --- |
| 0.1.0 | 2026-10-09 | Accepted | Initial version |

## License

This document, *Using manage-restic*, by **Christopher Steel**, with AI assistance from **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
