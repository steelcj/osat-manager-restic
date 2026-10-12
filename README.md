# osat-manager-restic

`manage-restic` installs [restic](https://restic.net/), the encrypted, deduplicating backup program, into your own account. It keeps several versions side by side, switches between them, protects what it installs, and keeps every verified download so a version can be restored without a network. It is the pilot OSAT manager, succeeding osat-fluent-restic-tool.

## Requirements

Python 3.8 or later. The manager uses the standard library only.

## Install

```sh
PYTHONPATH=lib python3 -m osat_manager_restic --self-install
manage-restic --install
restic version
```

On Windows, in Command Prompt, the first line is `set PYTHONPATH=lib` followed by `python -m osat_manager_restic --self-install`.

The launchers go to `~/.local/bin`, or `%LOCALAPPDATA%\osat\bin` on Windows, which must be on your `PATH`. [Using manage-restic](en-ca/docs/guides/usage/using-manage-restic-v0.1.0.md) explains every command.

## Verification

Every download is verified before it is unpacked: the signature on restic's `SHA256SUMS` against restic's signing key, pinned by fingerprint in [`manager.yaml`](manager.yaml), then the download's SHA-256 against that signed list. The binary must then report the requested version. The reasons are in [decision 0001](en-ca/docs/decisions/0001--build-manage-restic-v0.1.0.md).

## Platform status

| Platform | Status |
| --- | --- |
| Linux, amd64 | Verified: the full end-to-end scenario passed on 2026-10-09, in an Incus container (Linux Mint 22.3, Python 3.10) restored to a clean snapshot, including the offline restore from the verified archive. [Record](tests/e2e/linux/2026-10-09--linux-scenario-run.md); passed again on 2026-10-11 after the Windows launcher change. [Record](tests/e2e/linux/2026-10-11--linux-scenario-run.md) |
| Linux, arm64 | Not yet verified |
| macOS | Not yet verified: no Apple hardware available |
| Windows, amd64 | Scenario passed, not yet marked verified: the full end-to-end scenario passed on 2026-10-11, over SSH in a Windows 11 virtual machine restored to a clean snapshot (Python 3.15.0 from manage-python), including the offline restore inside a network cut. The cut's IPv6 internet path could not be tested on this network, so its self-test is to be repeated on a network with IPv6 before Windows is marked verified. [Record](tests/e2e/windows/2026-10-11--windows-test-run.md) |

The version stays below 1.0.0 until every platform is verified (uc-automa 0011).

## Develop

```sh
python3 -m unittest discover -s tests/unit
```

The unit tests run offline, against fake releases signed with a test key in `tests/unit/data/`; `OSAT_INSTALL_TESTS=1` adds a wheel install test.

The end-to-end drivers and the network cut live in uc-test-platform (uc-automa 0031), a checkout beside this one, with uc-portage's and uc-automa's:

```sh
uc-test-platform linux --repository . --instance <container> --snapshot <clean-snapshot>
uc-test-platform windows --repository . --instance <vm> --snapshot <clean-snapshot> --ssh <host>
```

They run `tests/e2e_scenario.py`, which stays here, as an ordinary user, with real downloads, in an Incus container on Linux and over SSH in an Incus virtual machine on Windows, and write their records here, under `tests/e2e/<platform>/`. The Windows driver also runs the unit tests of this repository, uc-portage and uc-automa, the network cut's self-test, and an install of uc-portage and uc-automa from wheels with `pip install --no-index` inside a network cut, with PyYAML built as pure Python.

## License

osat-manager-restic follows the REUSE convention: [`REUSE.toml`](REUSE.toml) records which licence covers which paths, and [`LICENSES/`](LICENSES/) holds their texts. Code is licensed under the MIT License, also in [`LICENSE`](LICENSE). Documentation is licensed under the Creative Commons Attribution 4.0 International License. Releases are MIT and CC BY 4.0 from 0.1.0, the first public release (uc-automa 0025). restic's release signature, kept as test data, is restic's, under the BSD 2-Clause License.

This document, *osat-manager-restic*, by **Christopher Steel**, with AI assistance from **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).
