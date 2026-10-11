---
title: "Decision: Build manage-restic"
dc:title: "Decision: Build manage-restic"
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 5.5 (Anthropic), AI assistance"
dc:subject: "OSAT manager, restic, verification, OpenPGP, manager.yaml, platforms"
dc:description: "Build manage-restic as the pilot OSAT manager for restic: the platforms targeted, two-step verification against a pinned signing key in the standard library, and where it differs from the contract and the process."
dc:date: "2026-10-09"
dc:type: "Text"
dc:format: "text/markdown"
dc:identifier: "urn:uuid:1ede50fa-cf0c-48d5-b121-1506673c2b9f"
dc:language: "en-CA"
dc:rights: "CC-BY-4.0"
sat:version: "0.1.0"
sat:status: "Accepted"
---

# Decision: Build manage-restic

Version: 0.1.0
Status: Accepted

## Context

Every OSAT manager starts with a decision record naming the managed tool, its radar entry, the platforms targeted first, and anything the manager does differently from the contract <a id="cite-steel-2026a"></a>[(Steel, 2026a)](#ref-steel-2026a). restic was chosen as the pilot manager by uc-automa 0018, succeeding osat-fluent-restic-tool. Its radar entry, *uc-radar: restic, Backup Tool*, version 0.1.0, is a draft awaiting placement in uc-radar.

restic publishes, for each release, one compressed binary per platform, `restic_<version>_<os>_<arch>.bz2` for Linux and macOS and `.zip` for Windows, a `SHA256SUMS` file, and a detached OpenPGP signature of it, `SHA256SUMS.asc`, made with Alexander Neumann's RSA key `CF8F 18F2 8445 7597 3F79 D4E1 91A6 868B D3F7 A907` <a id="cite-restic-nd"></a>[(restic authors, n.d.)](#ref-restic-nd).

## Decision

Build `manage-restic`, meeting the OSAT manager contract, with these choices:

- **Platforms targeted first:** Linux on amd64 and arm64, macOS on amd64 and arm64, Windows on amd64. Only Linux on amd64 is verified for 0.1.0.
- **Verification:** every download is checked in two steps before it is unpacked. The signature on `SHA256SUMS` is verified against the key pinned in `manager.yaml`, by fingerprint; then the asset's SHA-256 is compared with the signed list. The extracted binary must then report the requested version before it is placed.
- **Signature verification in the standard library:** the process requires the standard library only, with no shell commands, and Windows rarely has `gpg`. The manager therefore verifies the RSA signature itself, implementing the parts of RFC 4880 it needs and refusing the rest. osat-fluent-restic-tool had deferred signature checking for exactly this reason.
- **Strict verification rules:** the hash is exactly SHA-256, SHA-384 or SHA-512; the signature's hashed area names the pinned fingerprint as issuer, and an issuer only in the unhashed area, or none, fails; every issuer named must be the pinned key; the 16-bit hash prefix must match; the PKCS#1 v1.5 encoding is compared byte for byte; and malformed or truncated input fails closed. Where these are stricter than `gpg`, the test vectors name the rule.
- **Pin the key that actually signs:** the pinned fingerprint names the key that makes the signatures, by its own fingerprint, whether a primary key or a subkey. restic signs with its primary key, `CF8F 18F2 8445 7597 3F79 D4E1 91A6 868B D3F7 A907`. A subkey's binding to its primary is not checked; pinning the subkey's own fingerprint is the trust decision.
- **Independent review:** because the verifier is security-critical, new code, it is reviewed independently, by a reviewer who did not see it written, before osat-manager-restic is tagged, and again after any rewrite. Every test vector's expected verdict is confirmed with `gpg --verify`.
- **Reading manager.yaml without PyYAML:** the manager must run on the Python manage-python installs, which has no PyYAML, so it reads the strict subset of YAML that `manager.yaml` uses and refuses anything else. This conflicts with the process's own pairing of a YAML manifest with standard-library-only code, and is recorded as a finding about the process.
- **Finding manager.yaml:** the manager follows uc-automa 0019, mapping `manager.yaml` into the package and falling back to a proven checkout, but with its own small lookup rather than uc-portage's resolver, since uc-portage is not standard-library-only. This is a second copy of that rule, to be retired if the shared manager package becomes real.
- **The verified archive** keeps the downloaded asset with the `SHA256SUMS` and signature that verified it, so an offline restore re-checks both.
- **Install and activate together:** `--install` makes the installed version active, because osat-fluent-restic-tool's install that did not activate was misleading.
- **Locations:** the install root is `osat/restic` in each platform's per-user data directory, as the process proposes, while whether `osat` is the right name remains open. Launchers go to `~/.local/bin` on Linux and macOS and `%LOCALAPPDATA%\osat\bin` on Windows, which the user adds to `PATH`.
- **Nothing left behind:** the manager records each directory it creates outside its install root and removes it on uninstall if it is empty.

## Consequences

- The pinned key changes only by a new version of `manager.yaml`, reviewed like any other change.
- The manager never touches restic's own configuration, cache, repositories or passwords, and does not use `restic self-update`.
- Reaching 1.0.0 needs macOS and Windows verified (uc-automa 0011).

## References

<a id="ref-restic-nd"></a>restic authors. (n.d.). *Installation*. restic documentation. Retrieved October 9, 2026, from https://restic.readthedocs.io/en/stable/020_installation.html [↩](#cite-restic-nd)

<a id="ref-steel-2026a"></a>Steel, C. (2026a). *Creating an OSAT manager repository* (Version 0.2.0) [Unpublished manuscript]. uc-automa. urn:uuid:b18e2ed3-b364-4880-b3c7-5676961f0174 [↩](#cite-steel-2026a)

## Changelog

| Version | Date | Status | Notes |
| --- | --- | --- | --- |
| 0.1.0 | 2026-10-09 | Accepted | Initial version |

## License

This document, *Decision: Build manage-restic*, by **Christopher Steel**, with AI assistance from **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).
