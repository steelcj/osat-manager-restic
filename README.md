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

The launchers go to `~/.local/bin`, or `%LOCALAPPDATA%\osat\bin` on Windows, which must be on your `PATH`. [Using manage-restic](en-ca/docs/guides/usage/using-manage-restic-v0.1.0.md) explains every command.

## Verification

Every download is verified before it is unpacked: the signature on restic's `SHA256SUMS` against restic's signing key, pinned by fingerprint in [`manager.yaml`](manager.yaml), then the download's SHA-256 against that signed list. The binary must then report the requested version. The reasons are in [decision 0001](en-ca/docs/decisions/0001--build-manage-restic-v0.1.0.md).

## Platform status

| Platform | Status |
| --- | --- |
| Linux, amd64 | Verified: the full end-to-end scenario passed on 2026-10-09, in an Incus container (Linux Mint 22.3, Python 3.10) restored to a clean snapshot, including the offline restore from the verified archive. [Record](tests/e2e/linux/2026-10-09--linux-scenario-run.md) |
| Linux, arm64 | Not yet verified |
| macOS | Not yet verified: no Apple hardware available |
| Windows | Not yet verified: the Windows 11 virtual machine could not be reached. Unit tests cover the Windows launchers and zip assets |

The version stays below 1.0.0 until every platform is verified (uc-automa 0011).

## Develop

```sh
python3 -m unittest discover -s tests/unit
python3 tests/e2e/linux/run_in_incus.py --instance <container> --snapshot <clean-snapshot>
```

The unit tests run offline, against fake releases signed with a test key in `tests/unit/data/`; `OSAT_INSTALL_TESTS=1` adds a wheel install test. The end-to-end driver runs `tests/e2e_scenario.py` as an ordinary user in an Incus container, with real downloads, and writes a record beside itself.

## License

osat-manager-restic follows the REUSE convention: [`REUSE.toml`](REUSE.toml) records which licence covers which paths, and [`LICENSES/`](LICENSES/) holds their texts. Code is licensed under the MIT License, also in [`LICENSE`](LICENSE). Documentation is licensed under the Creative Commons Attribution 4.0 International License. Releases are MIT and CC BY 4.0 from 0.1.0, the first public release (uc-automa 0025). restic's release signature, kept as test data, is restic's, under the BSD 2-Clause License.

This document, *osat-manager-restic*, by **Christopher Steel**, with AI assistance from **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).
